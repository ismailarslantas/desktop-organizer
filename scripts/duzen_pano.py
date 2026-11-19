"""Masaüstü Düzenleyici — yerel canlı pano sunucusu.

* Yalnızca 127.0.0.1 üzerinde, işletim sisteminin verdiği boş bir portta dinler.
* Her API isteği oturuma özel anahtar (X-Oturum-Anahtari), Host ve Origin denetiminden geçer.
* Tarayıcıdan yol, komut ya da parametre kabul edilmez; yalnızca onaylı plan çalıştırılabilir.
* Panoya dosya adı, yol veya küçük resim gönderilmez; dosyalar anonim kimliklerle temsil edilir.
"""

from __future__ import annotations

import hmac
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import duzen_cekirdek as core

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "pano"
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/app.css": ("app.css", "text/css; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8")}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


class Pano:
    def __init__(self, op_id: str, pace: float = core.PACE_SECONDS):
        self.op_id = op_id
        self.plan, self.digest = core.load_plan(op_id)
        self.pace = pace
        self.token = secrets.token_urlsafe(32)
        self.control = core.Control()
        self.status = "hazir"
        self.message = ""
        self.undo_report = None
        self.worker: threading.Thread | None = None
        self.mu = threading.Lock()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.origin = f"http://127.0.0.1:{self.port}"
        self.closing = False
        states = core.item_states(core.Journal(op_id).records())
        pending = [it for it in self.plan["ogeler"] if states.get(it["id"], {}).get("durum", "bekliyor") == "bekliyor"]
        self.resumable = bool(states) and bool(pending)
        if states and not pending:
            self.status = "tamamlandi"  # bu plan zaten tamamen işlenmiş

    # ------------------------------------------------------------------ durum
    def state(self) -> dict:
        recs = core.Journal(self.op_id).records()
        states = core.item_states(recs)
        approved = core.is_approved(self.op_id, self.digest)
        items = []
        for it in self.plan["ogeler"]:
            s = states.get(it["id"], {}).get("durum", "bekliyor")
            items.append({"id": it["id"], "k": it["kategori"], "d": s})
        used = sorted({it["kategori"] for it in self.plan["ogeler"]})
        lay = core.plan_layout(self.plan)
        cats = [{"k": k, "klasor": lay["klasor"][k], "etiket": lay["etiket"][k],
                 "renk": core.CATEGORIES[k][2],
                 "plan": sum(1 for it in self.plan["ogeler"] if it["kategori"] == k)} for k in used]
        with self.mu:
            status, message, undo_report = self.status, self.message, self.undo_report
            if status == "duraklatiliyor" and self.control.idle.is_set():
                status = self.status = "duraklatildi"
        busy = status in ("calisiyor", "duraklatiliyor", "duraklatildi", "durduruluyor", "geri_aliniyor")
        undo_op = None
        if not busy:
            try:
                undo_op = core.last_undoable_op()
            except OSError:
                undo_op = None
        return {
            "islem": self.op_id, "kok_adi": self.plan.get("kok_adi", core.ROOT_NAME), "onayli": approved, "durum": status, "mesaj": message,
            "sure": self.pace, "kategoriler": cats, "ogeler": items,
            "plan_dosya": len(self.plan["ogeler"]),
            "plan_boyut": sum(it["boyut"] for it in self.plan["ogeler"]),
            "sayaclar": core.summarize(self.op_id),
            "geri_alinabilir": bool(undo_op), "geri_alinacak_islem": undo_op,
            "geri_alma_raporu": undo_report,
            "devam_edilebilir": self.resumable and status == "hazir",
            "kalan": sum(1 for it in items if it["d"] == "bekliyor"),
        }

    # ------------------------------------------------------------------ eylemler
    def start(self):
        with self.mu:
            if self.status != "hazir":
                return 409, "zaten_baslatildi", "Bu panoda işlem zaten başlatıldı."
            if not core.is_approved(self.op_id, self.digest):
                return 409, "onay_yok", "Plan onaylanmadı; Başlat pasif."
            try:
                lock = core.GlobalLock("duzenleme", self.op_id).acquire()
            except core.DuzenHatasi as ex:
                return 409, "mesgul", str(ex)
            self.status, self.message = "calisiyor", ""

        def run():
            try:
                res = core.execute_plan(self.op_id, pace=self.pace, control=self.control, lock=lock)
                with self.mu:
                    self.status = res["sonuc"]
            except Exception as ex:  # panoda göster, sessizce yutma
                with self.mu:
                    self.status, self.message = "hata", str(ex)
            finally:
                lock.release()

        self.worker = threading.Thread(target=run, name="duzenleme", daemon=False)
        self.worker.start()
        return 200, "basladi", "Başladı."

    def pause_toggle(self):
        with self.mu:
            if self.status == "calisiyor":
                self.control.paused.set()
                self.status = "duraklatiliyor"
                return 200, "duraklatilacak", "Mevcut dosya bitince duraklatılacak."
            if self.status in ("duraklatiliyor", "duraklatildi"):
                self.control.paused.clear()
                self.status = "calisiyor"
                return 200, "devam", "Devam ediliyor."
        return 409, "calisan_yok", "Çalışan bir işlem yok."

    def stop(self):
        with self.mu:
            if self.status in ("calisiyor", "duraklatiliyor", "duraklatildi"):
                self.control.stopped.set()
                self.control.paused.clear()
                self.status = "durduruluyor"
                return 200, "durdurulacak", "Mevcut dosya bitince durdurulacak. Taşınanlar geri alınmaz."
        return 409, "calisan_yok", "Çalışan bir işlem yok."

    def undo_last(self):
        with self.mu:
            if self.status in ("calisiyor", "duraklatiliyor", "duraklatildi", "durduruluyor", "geri_aliniyor"):
                return 409, "once_bekle", "Önce çalışan işlemin bitmesini bekleyin."
            try:
                lock = core.GlobalLock("geri_alma", "son").acquire()
            except core.DuzenHatasi as ex:
                return 409, "mesgul", str(ex)
            prev = self.status
            self.status = "geri_aliniyor"

        def run():
            try:
                rep = core.undo(last=True, lock=lock)
                with self.mu:
                    self.undo_report = rep
                    self.status = "geri_alindi" if prev in ("tamamlandi", "durduruldu", "geri_alindi") else prev
            except Exception as ex:
                with self.mu:
                    self.status, self.message = "hata", str(ex)
            finally:
                lock.release()

        threading.Thread(target=run, name="geri_alma", daemon=False).start()
        return 200, "geri_alma_basladi", "Geri alma başladı."

    def close(self):
        with self.mu:
            if self.status in ("calisiyor", "duraklatiliyor", "duraklatildi"):
                self.control.stopped.set()
                self.control.paused.clear()
                self.status = "durduruluyor"
            self.closing = True

        def later():
            if self.worker:
                self.worker.join()
            self.server.shutdown()

        threading.Thread(target=later, daemon=True).start()
        return 200, "kapaniyor", "Pano kapanıyor."

    # ------------------------------------------------------------------ HTTP
    def _handler(self):
        pano = self

        class H(BaseHTTPRequestHandler):
            server_version = "MasaustuDuzenleyici"
            sys_version = ""

            def log_message(self, *a):
                pass

            def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy", CSP)
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Cross-Origin-Resource-Policy", "same-origin")
                self.end_headers()
                self.wfile.write(body)

            def _json(self, code, obj):
                self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

            def _host_ok(self):
                return self.headers.get("Host", "") == f"127.0.0.1:{pano.port}"

            def _api_ok(self, post: bool):
                if not self._host_ok():
                    return False
                key = self.headers.get("X-Oturum-Anahtari", "")
                if not hmac.compare_digest(key.encode(), pano.token.encode()):
                    return False
                origin = self.headers.get("Origin")
                if post and origin != pano.origin:
                    return False
                if origin is not None and origin != pano.origin:
                    return False
                site = self.headers.get("Sec-Fetch-Site")
                if site is not None and site not in ("same-origin", "none"):
                    return False
                return True

            def do_GET(self):
                path = self.path.split("?", 1)[0]
                if not self._host_ok():
                    return self._json(403, {"hata": "geçersiz Host"})
                if path in STATIC:
                    fname, ctype = STATIC[path]
                    return self._send(200, (ASSETS / fname).read_bytes(), ctype)
                if path == "/api/durum":
                    if not self._api_ok(post=False):
                        return self._json(403, {"hata": "yetkisiz"})
                    return self._json(200, pano.state())
                return self._json(404, {"hata": "bulunamadı"})

            def do_POST(self):
                path = self.path.split("?", 1)[0]
                if not self._api_ok(post=True):
                    return self._json(403, {"hata": "yetkisiz"})
                length = int(self.headers.get("Content-Length") or 0)
                if length:
                    if length > 1024:
                        return self._json(413, {"hata": "gövde kabul edilmez"})
                    self.rfile.read(length)  # içerik yok sayılır: tarayıcıdan parametre alınmaz
                actions = {"/api/baslat": pano.start, "/api/duraklat": pano.pause_toggle,
                           "/api/durdur": pano.stop, "/api/geri-al": pano.undo_last,
                           "/api/kapat": pano.close}
                fn = actions.get(path)
                if not fn:
                    return self._json(404, {"hata": "bulunamadı"})
                code, kod, msg = fn()
                return self._json(code, {"kod": kod, "mesaj": msg})

            def do_PUT(self):
                self._json(405, {"hata": "izin yok"})

            do_DELETE = do_PATCH = do_PUT

        return H

    def url(self) -> str:
        return f"{self.origin}/?k={self.token}"

    def serve(self, open_browser: bool = True):
        if open_browser:
            threading.Timer(0.3, lambda: webbrowser.open(self.url())).start()
        try:
            self.server.serve_forever(poll_interval=0.25)
        finally:
            self.server.server_close()
            if self.worker:
                self.worker.join()
