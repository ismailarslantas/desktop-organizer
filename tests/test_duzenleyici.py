"""Geçici örnek masaüstü üzerinde senaryo testleri. Gerçek masaüstüne dokunmaz.

Çalıştırma:  python -m unittest discover -s tests -v
"""

from __future__ import annotations

import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import duzen_cekirdek as core  # noqa: E402

OLD = time.time() - 3 * 3600
PNG = b"\x89PNG\r\n\x1a\n"
JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


def png_with_text(key: bytes, value: bytes) -> bytes:
    def chunk(t, d):
        return len(d).to_bytes(4, "big") + t + d + zlib.crc32(t + d).to_bytes(4, "big")
    ihdr = (1).to_bytes(4, "big") * 2 + b"\x08\x02\x00\x00\x00"
    return PNG + chunk(b"IHDR", ihdr) + chunk(b"tEXt", key + b"\x00" + value) + chunk(b"IEND", b"")


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="md-test-"))
        self.desk = self.tmp / "Desktop"
        self.desk.mkdir()
        self.state = self.tmp / "state"
        os.environ[core.STATE_ENV] = str(self.state)

    def tearDown(self):
        os.environ.pop(core.STATE_ENV, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def put(self, name, data=b"x", age=OLD, where=None):
        p = (where or self.desk) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data if isinstance(data, bytes) else data.encode())
        os.utime(p, (age, age))
        return p

    def plan(self):
        pp, plan = core.build_plan(str(self.desk), stability_wait=0.05)
        return plan

    def by_name(self, plan):
        return {i["ad"]: i for i in plan["ogeler"]}

    def skipped(self, plan):
        return {s["ad"]: s["neden"] for s in plan["atlananlar"]}

    def run_plan(self, plan):
        core.approve(plan["islem"], core.APPROVAL_PHRASE)
        return core.execute_plan(plan["islem"], pace=0)

    layout = "en"  # varsayılan düzen

    def root(self):
        return self.desk / core.LAYOUTS[self.layout]["kok"]

    def f(self, key):
        return core.LAYOUTS[self.layout]["klasor"][key]


class TestClassification(Sandbox):
    def test_normal_files_and_categories(self):
        self.put("tatil.jpg", JPG)
        self.put("rapor.pdf", b"%PDF-1.4 ...")
        self.put("butce.xlsx", b"PK\x03\x04")
        self.put("sunum.pptx", b"PK\x03\x04a")
        self.put("klip.mp4", b"\x00\x00\x00\x18ftypmp42")
        self.put("sarki.mp3", b"ID3")
        self.put("sayfa.html", b"<html></html>")
        self.put("yedek.zip", b"PK\x05\x06")
        self.put("kurulum.msi", b"\xd0\xcf")
        self.put("not.xyz", b"?")
        self.put("afis.psd", b"8BPS")
        self.put("logo.ai", b"%PDF-1.6 illustrator")
        self.put("rozet.EPS", b"%!PS-Adobe-3.0 EPSF-3.0")
        self.put("kartvizit.cdr", b"RIFF\x00\x00\x00\x00CDR")
        self.put("Ekran Görüntüsü 2026-01-02.png", PNG + b"data")
        self.put("Screenshot 2026-01-02 at 10.00.png", PNG + b"data2")
        self.put("DALL·E 2026 kedi.png", PNG + b"data3")
        self.put("sd_cikti.png", png_with_text(b"parameters", b"a cat, Steps: 20, Sampler: Euler"))
        self.put("c2pa.png", png_with_text(b"XML:com.adobe.xmp",
                                           b"<x>http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia</x>"))
        self.put("mac_ekran.png", png_with_text(b"XML:com.adobe.xmp", b"<exif:UserComment>Screenshot</exif:UserComment>"))
        self.put("sahte.png", b"bu bir metin")
        self.put("gorunus_belirsiz.png", PNG + b"pixels")
        cats = {n: i["kategori"] for n, i in self.by_name(self.plan()).items()}
        self.assertEqual(cats["tatil.jpg"], "01")
        self.assertEqual(cats["rapor.pdf"], "06")
        self.assertEqual(cats["butce.xlsx"], "07")
        self.assertEqual(cats["sunum.pptx"], "08")
        self.assertEqual(cats["klip.mp4"], "04")
        self.assertEqual(cats["sarki.mp3"], "05")
        self.assertEqual(cats["sayfa.html"], "09")
        self.assertEqual(cats["yedek.zip"], "10")
        self.assertEqual(cats["kurulum.msi"], "11")
        self.assertEqual(cats["not.xyz"], "12")
        self.assertEqual(cats["logo.ai"], "14")
        self.assertEqual(cats["rozet.EPS"], "15")
        self.assertEqual(cats["kartvizit.cdr"], "16")
        self.assertEqual(cats["afis.psd"], "17")
        self.assertEqual(cats["Ekran Görüntüsü 2026-01-02.png"], "03")
        self.assertEqual(cats["Screenshot 2026-01-02 at 10.00.png"], "03")
        self.assertEqual(cats["mac_ekran.png"], "03")
        self.assertEqual(cats["DALL·E 2026 kedi.png"], "02")
        self.assertEqual(cats["sd_cikti.png"], "02")
        self.assertEqual(cats["c2pa.png"], "02")
        self.assertEqual(cats["sahte.png"], "12")
        self.assertEqual(cats["gorunus_belirsiz.png"], "01")

    def test_untouchables(self):
        self.put("Uygulama.lnk", b"L")
        self.put("Site.url", b"[InternetShortcut]")
        self.put("indir.pdf.crdownload", b"%PDF")
        self.put("video.mp4.part", b"..")
        self.put("gecici.tmp", b"..")
        self.put("yeni.txt", b"taze", age=time.time() - 60)
        self.put("desktop.ini", b"[.ShellClassInfo]")
        self.put(".gizli", b"h")
        self.put("sayfa.html", b"<html>")
        (self.desk / "sayfa_files").mkdir()
        (self.desk / "Projeler").mkdir()
        self.put("ic.txt", b"klasor ici", where=self.desk / "Projeler")
        plan = self.plan()
        names = set(self.by_name(plan))
        self.assertEqual(names, set(), names)
        sk = self.skipped(plan)
        self.assertIn("geçici", sk["indir.pdf.crdownload"])
        self.assertIn("geçici", sk["video.mp4.part"])
        self.assertIn("geçici", sk["gecici.tmp"])
        self.assertIn("15 dakika", sk["yeni.txt"])
        self.assertIn("kaynak klasörü", sk["sayfa.html"])
        self.assertIn("gizli", sk["desktop.ini"])
        self.assertEqual(sorted(plan["kisayollar"]), ["Site.url", "Uygulama.lnk"])
        self.assertIn("Projeler", plan["klasorler"])
        self.run_plan(plan)
        self.assertTrue((self.desk / "Projeler" / "ic.txt").exists())
        self.assertTrue((self.desk / "Uygulama.lnk").exists())
        self.assertFalse(self.root().exists(), "taşınacak dosya yokken düzen klasörü oluşturulmamalı")

    def test_ordinary_metadata_is_not_ai(self):
        xmp = b"<x:xmpmeta><exif:ImageNumber>6</exif:ImageNumber><tiff:ImageDescription/></x:xmpmeta>"
        self.put("urun.png", png_with_text(b"XML:com.adobe.xmp", xmp))
        self.put("katalog_dallas.png", png_with_text(b"Comment", b"Dallas edition, paperweight"))
        self.put("openai.png", png_with_text(b"XML:com.adobe.xmp", b"<claim_generator>OpenAI-API</claim_generator>"))
        cats = {n: i["kategori"] for n, i in self.by_name(self.plan()).items()}
        self.assertEqual(cats["urun.png"], "01", "ImageNumber gibi alanlar YZ işareti sayılmamalı")
        self.assertEqual(cats["katalog_dallas.png"], "01")
        self.assertEqual(cats["openai.png"], "02")

    def test_outlook_data_files_never_touched(self):
        pst = self.put("backup.pst", b"!BDN" + b"\x00" * 64)
        ost = self.put("Outlook.OST", b"!BDN" + b"\x01" * 64)
        self.put("not.txt", b"tasinir")
        before = (pst.read_bytes(), os.stat(pst).st_mtime_ns)
        plan = self.plan()
        self.assertEqual(set(self.by_name(plan)), {"not.txt"})
        self.assertEqual(sorted(k["ad"] for k in plan["korunanlar"]), ["Outlook.OST", "backup.pst"])
        self.assertIn("backup.pst", (core.plan_path(plan["islem"]).with_suffix(".md")).read_text(encoding="utf-8"))
        self.run_plan(plan)
        core.undo(plan["islem"])
        self.assertEqual((pst.read_bytes(), os.stat(pst).st_mtime_ns), before, ".pst taşınmamalı ve değişmemeli")
        self.assertTrue(ost.exists())

    def test_open_office_document_skipped(self):
        self.put("SAP KATALOG NO.xlsx", b"PK\x03\x04")
        self.put("~$SAP Katalog No.xlsx", b"lock")
        self.put("Uzun Rapor Adi.docx", b"PK\x03\x04")
        self.put("~$un Rapor Adi.docx", b"lock")
        self.put("kapali.xlsx", b"PK\x03\x04x")
        plan = self.plan()
        sk = self.skipped(plan)
        self.assertIn("Office", sk["SAP KATALOG NO.xlsx"])
        self.assertIn("Office", sk["Uzun Rapor Adi.docx"])
        self.assertEqual(set(self.by_name(plan)), {"kapali.xlsx"})
        # plandan sonra açılırsa taşıma anında da atlanır
        core.approve(plan["islem"], core.APPROVAL_PHRASE)
        self.put("~$kapali.xlsx", b"lock")
        res = core.execute_plan(plan["islem"], pace=0)
        self.assertEqual(res["tasinan"], 0)
        self.assertTrue((self.desk / "kapali.xlsx").exists())

    def test_symlink_skipped(self):
        target = self.put("hedef.txt", b"t", where=self.tmp)
        try:
            os.symlink(target, self.desk / "baglanti.txt")
        except (OSError, NotImplementedError):
            self.skipTest("Bu ortamda sembolik bağlantı oluşturulamıyor (yetki gerekir).")
        sk = self.skipped(self.plan())
        self.assertIn("bağlantı", sk["baglanti.txt"])

    @unittest.skipUnless(core.IS_WIN, "Windows öznitelikleri")
    def test_windows_hidden_and_cloud_attributes(self):
        import ctypes
        h = self.put("gizli.txt", b"h")
        ctypes.windll.kernel32.SetFileAttributesW(str(h), 0x2)
        sk = self.skipped(self.plan())
        self.assertIn("gizli", sk["gizli.txt"])


class TestMoveAndDuplicates(Sandbox):
    def test_duplicates_and_name_collision(self):
        self.put("a.txt", b"ayni icerik", age=OLD - 100)  # en eski -> asıl
        self.put("b.txt", b"ayni icerik", age=OLD)
        self.put("c.txt", b"farkli icrk", age=OLD)  # aynı boyut, farklı içerik
        self.put("rapor.pdf", b"%PDF yeni")
        self.put("rapor.pdf", b"%PDF eski", where=self.root() / self.f("06"))
        plan = self.plan()
        items = self.by_name(plan)
        self.assertEqual(items["a.txt"]["kategori"], "06")
        self.assertEqual(items["b.txt"]["kategori"], "13")
        self.assertEqual(items["c.txt"]["kategori"], "06")
        self.assertEqual(len(plan["kopya_gruplari"]), 1)
        self.assertEqual(plan["kopya_gruplari"][0]["asil"], "a.txt")
        self.assertEqual(items["rapor.pdf"]["hedef_ad"], "rapor (2).pdf")
        res = self.run_plan(plan)
        self.assertEqual(res["sonuc"], "tamamlandi")
        self.assertEqual(res["tasinan"], 4)
        self.assertEqual(res["kopyalara"], 1)
        r = self.root()
        self.assertEqual((r / self.f("06") / "rapor.pdf").read_bytes(), b"%PDF eski")
        self.assertEqual((r / self.f("06") / "rapor (2).pdf").read_bytes(), b"%PDF yeni")
        self.assertTrue((r / self.f("13") / "b.txt").exists())
        self.assertTrue((r / self.f("06") / "a.txt").exists())
        self.assertFalse((r / self.f("01")).exists(), "gereksiz kategori klasörü oluşturulmamalı")

    def test_same_name_different_content_is_not_duplicate(self):
        self.put("x.txt", b"bir")
        self.put("x.txt", b"iki", where=self.root() / self.f("06"))
        plan = self.plan()
        self.assertEqual(plan["kopya_gruplari"], [])
        self.assertEqual(self.by_name(plan)["x.txt"]["kategori"], "06")

    def test_requires_exact_approval(self):
        self.put("a.txt", b"a")
        plan = self.plan()
        with self.assertRaises(core.DuzenHatasi):
            core.execute_plan(plan["islem"], pace=0)
        with self.assertRaises(core.DuzenHatasi):
            core.approve(plan["islem"], "tamam")
        self.assertTrue((self.desk / "a.txt").exists())

    def test_tampered_plan_rejected(self):
        self.put("a.txt", b"a")
        plan = self.plan()
        core.approve(plan["islem"], core.APPROVAL_PHRASE)
        pp = core.plan_path(plan["islem"])
        data = json.loads(pp.read_text(encoding="utf-8"))
        data["ogeler"][0]["hedef"] = str(self.tmp / "baska")
        pp.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(core.DuzenHatasi):
            core.execute_plan(plan["islem"], pace=0)
        self.assertTrue((self.desk / "a.txt").exists())

    def test_changed_after_approval_and_new_file(self):
        self.put("a.txt", b"orijinal")
        self.put("b.txt", b"sabit")
        plan = self.plan()
        core.approve(plan["islem"], core.APPROVAL_PHRASE)
        p = self.desk / "a.txt"
        p.write_bytes(b"degisti!!")
        os.utime(p, (OLD, OLD))
        self.put("sonradan.txt", b"yeni gelen")
        res = core.execute_plan(plan["islem"], pace=0)
        self.assertEqual(res["tasinan"], 1)
        self.assertEqual(res["atlanan"], 1)
        self.assertTrue((self.desk / "a.txt").exists())
        self.assertTrue((self.desk / "sonradan.txt").exists(), "onaydan sonra gelen dosya taşınmamalı")

    def test_concurrent_operations_blocked(self):
        self.put("a.txt", b"a")
        plan = self.plan()
        core.approve(plan["islem"], core.APPROVAL_PHRASE)
        with core.GlobalLock("test"):
            with self.assertRaises(core.DuzenHatasi):
                core.execute_plan(plan["islem"], pace=0)
            with self.assertRaises(core.DuzenHatasi):
                core.undo(last=True)
        self.assertTrue((self.desk / "a.txt").exists())

    def test_pause_and_stop_between_files(self):
        for i in range(6):
            self.put(f"f{i}.txt", f"icerik {i}".encode())
        plan = self.plan()
        core.approve(plan["islem"], core.APPROVAL_PHRASE)
        ctl = core.Control()
        out = {}
        t = threading.Thread(target=lambda: out.update(core.execute_plan(plan["islem"], pace=3, control=ctl)))
        t.start()
        time.sleep(0.8)
        ctl.paused.set()
        time.sleep(0.2)
        n_paused = core.summarize(plan["islem"])["tasinan"]
        time.sleep(0.8)
        self.assertEqual(core.summarize(plan["islem"])["tasinan"], n_paused, "duraklatılmışken taşıma olmamalı")
        ctl.stopped.set()
        t.join(5)
        self.assertEqual(out["sonuc"], "durduruldu")
        self.assertLess(out["tasinan"], 6)
        self.assertGreaterEqual(out["tasinan"], 1)
        # durdurma önceden taşınanları geri almaz
        self.assertEqual(len(list((self.root() / self.f("06")).iterdir())), out["tasinan"])


class TestLayouts(Sandbox):
    def test_default_is_english(self):
        self.put("rapor.pdf", b"%PDF-1.4")
        plan = self.plan()
        self.assertEqual(plan["duzen"], "en")
        self.run_plan(plan)
        self.assertTrue((self.desk / "Organized Desktop" / "06_Documents" / "rapor.pdf").exists())
        self.assertFalse((self.desk / core.ROOT_NAME).exists())

    def test_turkish_layout_is_remembered(self):
        self.put("rapor.pdf", b"%PDF-1.4")
        pp, plan = core.build_plan(str(self.desk), stability_wait=0.05, layout="tr")
        self.assertEqual(plan["kok_adi"], "Masaüstü Düzeni")
        self.run_plan(plan)
        self.assertTrue((self.desk / "Masaüstü Düzeni" / "06_Belgeler" / "rapor.pdf").exists())
        self.put("not.txt", b"ikinci")
        self.assertEqual(self.plan()["duzen"], "tr", "kayıtlı düzen sonraki planda da kullanılmalı")

    def test_existing_turkish_root_is_kept(self):
        (self.desk / "Masaüstü Düzeni" / "06_Belgeler").mkdir(parents=True)
        self.put("rapor.pdf", b"%PDF-1.4")
        plan = self.plan()
        self.assertEqual(plan["duzen"], "tr", "masaüstündeki mevcut Türkçe kök korunmalı")
        self.assertIn("Masaüstü Düzeni/06_Belgeler/rapor.pdf",
                      core.plan_path(plan["islem"]).with_suffix(".md").read_text(encoding="utf-8"))

    def test_switching_layout_notes_other_root(self):
        (self.desk / "Masaüstü Düzeni").mkdir()
        self.put("rapor.pdf", b"%PDF-1.4")
        pp, plan = core.build_plan(str(self.desk), stability_wait=0.05, layout="en")
        self.assertEqual(plan["diger_kokler"], ["Masaüstü Düzeni"])
        self.assertIn("Masaüstü Düzeni", pp.with_suffix(".md").read_text(encoding="utf-8"))

    def test_old_plans_without_layout_still_run(self):
        self.put("rapor.pdf", b"%PDF-1.4")
        pp, plan = core.build_plan(str(self.desk), stability_wait=0.05, layout="tr")
        data = core.json.loads(pp.read_text(encoding="utf-8"))
        for k in ("duzen", "duzen_nedeni", "kok_adi", "klasor_adlari", "diger_kokler"):
            data.pop(k)
        pp.write_text(core.json.dumps(data, ensure_ascii=False), encoding="utf-8")
        core.approve(plan["islem"], core.APPROVAL_PHRASE)
        self.assertEqual(core.execute_plan(plan["islem"], pace=0)["tasinan"], 1)
        self.assertTrue((self.desk / "Masaüstü Düzeni" / "06_Belgeler" / "rapor.pdf").exists())

    def test_unknown_layout_rejected(self):
        with self.assertRaises(core.DuzenHatasi):
            core.build_plan(str(self.desk), stability_wait=0.05, layout="de")


class TestUndoAndRecovery(Sandbox):
    def test_undo_restores(self):
        self.put("a.txt", b"a")
        self.put("b.jpg", JPG)
        plan = self.plan()
        self.run_plan(plan)
        self.assertFalse((self.desk / "a.txt").exists())
        rep = core.undo(plan["islem"])
        self.assertEqual(rep["geri_alinan"], 2)
        self.assertEqual((self.desk / "a.txt").read_bytes(), b"a")
        self.assertTrue((self.root() / self.f("06")).is_dir(), "geri alma klasör silmemeli")

    def test_undo_conflict_and_modified(self):
        self.put("a.txt", b"a")
        self.put("b.txt", b"bb")
        plan = self.plan()
        self.run_plan(plan)
        self.put("a.txt", b"yeni a")  # eski konum doldu
        moved_b = self.root() / self.f("06") / "b.txt"
        moved_b.write_bytes(b"degisti")  # taşındıktan sonra değişti
        rep = core.undo(last=True)
        self.assertEqual(rep["geri_alinan"], 0)
        self.assertEqual(len(rep["cakisma"]), 1)
        self.assertEqual(len(rep["reddedilen"]), 1)
        self.assertEqual((self.desk / "a.txt").read_bytes(), b"yeni a", "üzerine yazılmamalı")
        self.assertTrue((self.root() / self.f("06") / "a.txt").exists(), "çakışan dosya yerinde kalmalı")
        self.assertTrue(moved_b.exists())
        # çakışma giderilince tekrar denenebilir
        os.rename(self.desk / "a.txt", self.tmp / "kenara.txt")
        rep2 = core.undo(plan["islem"])
        self.assertEqual(rep2["geri_alinan"], 1)
        self.assertEqual((self.desk / "a.txt").read_bytes(), b"a")

    def test_undo_last_picks_latest(self):
        self.put("a.txt", b"a")
        p1 = self.plan()
        self.run_plan(p1)
        time.sleep(1.1)  # işlem kimlikleri saniye çözünürlüklü
        self.put("b.txt", b"b")
        p2 = self.plan()
        self.run_plan(p2)
        rep = core.undo(last=True)
        self.assertEqual(rep["islem"], p2["islem"])
        self.assertTrue((self.desk / "b.txt").exists())
        self.assertFalse((self.desk / "a.txt").exists())

    def test_crash_reconciliation(self):
        self.put("a.txt", b"a")
        self.put("b.txt", b"bb")
        plan = self.plan()
        core.approve(plan["islem"], core.APPROVAL_PHRASE)
        j = core.Journal(plan["islem"])
        items = self.by_name(plan)
        cat = self.root() / self.f("06")
        cat.mkdir(parents=True)
        for name, moved in (("a.txt", True), ("b.txt", False)):
            it = items[name]
            j.append({"tur": "tasima_niyeti", "id": it["id"], "kaynak": it["kaynak"], "hedef": it["hedef"],
                      "kategori": "06", "boyut": it["boyut"], "mtime_ns": it["mtime_ns"],
                      "kimlik": it["kimlik"], "iz": it["iz"], "kopya": False})
            if moved:
                os.rename(it["kaynak"], it["hedef"])  # taşındı ama "tamam" yazılamadan çöktü
        fixed = core.reconcile_all()
        kinds = sorted(f["tur"] for f in fixed)
        self.assertEqual(kinds, ["tasima_hata", "tasima_tamam"])
        self.assertEqual(core.summarize(plan["islem"])["tasinan"], 1)
        rep = core.undo(plan["islem"])
        self.assertEqual(rep["geri_alinan"], 1)
        self.assertTrue((self.desk / "a.txt").exists())

    def test_root_must_not_be_link(self):
        self.put("a.txt", b"a")
        other = self.tmp / "baska"
        other.mkdir()
        try:
            if core.IS_WIN:
                import subprocess
                r = subprocess.run(["cmd", "/c", "mklink", "/J", str(self.root()), str(other)],
                                   capture_output=True)
                if r.returncode != 0:
                    raise OSError
            else:
                os.symlink(other, self.root(), target_is_directory=True)
        except OSError:
            self.skipTest("bağlantı oluşturulamadı")
        with self.assertRaises(core.DuzenHatasi):
            self.plan()


class TestDashboardSecurity(Sandbox):
    def setUp(self):
        super().setUp()
        import duzen_pano
        self.put("a.txt", b"a")
        self.put("b.jpg", JPG)
        self.planned = self.plan()
        self.p = duzen_pano.Pano(self.planned["islem"], pace=0)
        self.t = threading.Thread(target=self.p.serve, kwargs={"open_browser": False}, daemon=True)
        self.t.start()

    def tearDown(self):
        try:
            self.req("POST", "/api/kapat")
        except OSError:
            pass
        self.t.join(5)
        super().tearDown()

    def req(self, method, path, key=True, origin=True, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.p.port, timeout=5)
        h = {"Host": host or f"127.0.0.1:{self.p.port}"}
        if key:
            h["X-Oturum-Anahtari"] = self.p.token if key is True else key
        if origin:
            h["Origin"] = self.p.origin if origin is True else origin
        c.request(method, path, headers=h)
        r = c.getresponse()
        body = r.read()
        c.close()
        return r.status, (json.loads(body) if body.startswith(b"{") else body)

    def test_binds_loopback_only(self):
        self.assertEqual(self.p.server.server_address[0], "127.0.0.1")

    def test_auth_origin_host(self):
        self.assertEqual(self.req("GET", "/api/durum", key=False)[0], 403)
        self.assertEqual(self.req("GET", "/api/durum", key="yanlis")[0], 403)
        self.assertEqual(self.req("GET", "/api/durum", origin="http://evil.example")[0], 403)
        self.assertEqual(self.req("GET", "/api/durum", host="evil.example")[0], 403)
        self.assertEqual(self.req("POST", "/api/baslat", origin=False)[0], 403)
        code, st = self.req("GET", "/api/durum")
        self.assertEqual(code, 200)
        blob = json.dumps(st, ensure_ascii=False)
        for secret in ("a.txt", "b.jpg", str(self.desk), self.tmp.name):
            self.assertNotIn(secret, blob, "panoya ad/yol sızmamalı")

    def test_start_disabled_until_approved_then_runs(self):
        code, _ = self.req("POST", "/api/baslat")
        self.assertEqual(code, 409)
        self.assertTrue((self.desk / "a.txt").exists())
        core.approve(self.planned["islem"], core.APPROVAL_PHRASE)
        self.assertTrue(self.req("GET", "/api/durum")[1]["onayli"])
        self.assertEqual(self.req("POST", "/api/baslat")[0], 200)
        for _ in range(100):
            st = self.req("GET", "/api/durum")[1]
            if st["durum"] == "tamamlandi":
                break
            time.sleep(0.05)
        self.assertEqual(st["durum"], "tamamlandi")
        self.assertEqual(st["sayaclar"]["tasinan"], 2)
        self.assertEqual(self.req("POST", "/api/baslat")[0], 409, "aynı plan ikinci kez başlatılamaz")
        self.assertEqual(self.req("POST", "/api/geri-al")[0], 200)
        for _ in range(100):
            st = self.req("GET", "/api/durum")[1]
            if st["durum"] == "geri_alindi":
                break
            time.sleep(0.05)
        self.assertEqual(st["geri_alma_raporu"]["geri_alinan"], 2)
        self.assertTrue((self.desk / "a.txt").exists())

    def test_resume_interrupted_run(self):
        import duzen_pano
        core.approve(self.planned["islem"], core.APPROVAL_PHRASE)
        first = self.planned["ogeler"][0]
        core._move_one(first, str(self.desk), self.root(), core.Journal(self.planned["islem"]))  # yarıda kesilmiş gibi
        p2 = duzen_pano.Pano(self.planned["islem"], pace=0)
        st = p2.state()
        self.assertTrue(st["devam_edilebilir"])
        self.assertEqual(st["kalan"], 1)
        self.assertTrue(all(c["k"] in core.CATEGORIES for c in st["kategoriler"]))
        p2.server.server_close()
        ops = {o["islem"]: o for o in core.list_ops()}
        self.assertTrue(ops[self.planned["islem"]]["yarim"])
        res = core.execute_plan(self.planned["islem"], pace=0)
        self.assertEqual(res["tasinan"], 2, "taşınmış dosya tekrar ellenmeden kalan tamamlanmalı")
        p3 = duzen_pano.Pano(self.planned["islem"], pace=0)
        self.assertEqual(p3.state()["durum"], "tamamlandi")
        p3.server.server_close()

    def test_assets_have_no_external_references(self):
        import re as _re
        for f in (HERE.parent / "assets" / "pano").iterdir():
            text = f.read_text(encoding="utf-8")
            self.assertIsNone(_re.search(r"https?://|//cdn|@import|fonts\.g", text), f.name)

    def test_rejects_arbitrary_paths(self):
        self.assertEqual(self.req("POST", "/api/calistir?yol=C:/")[0], 404)
        self.assertEqual(self.req("GET", "/../scripts/duzen_cekirdek.py")[0], 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
