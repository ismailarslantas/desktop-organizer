#!/usr/bin/env python3
"""Masaüstü Düzenleyici — komut satırı.

Komutlar:
  ortam                         Çalışma ortamını ve masaüstü tespitini denetler (hiçbir şey kurmaz).
  tespit [--masaustu YOL]       Gerçek masaüstü yolunu gösterir.
  plan   [--masaustu YOL]       Masaüstünü inceler, planı işlem kimliğiyle kaydeder ve yazdırır.
  onayla ISLEM --ifade "Planı onaylıyorum"
  pano   ISLEM [--sure 50] [--tarayici-acma]
                                Canlı panoyu açar. Taşıma yalnızca panodaki Başlat ile başlar.
  geri-al ISLEM | --son         Belirli işlemi ya da son işlemi geri alır.
  durum                         Kayıtlı işlemleri ve sayaçları listeler.
  uzlastir                      Yarım kalan kayıtları gerçek dosya durumuyla eşler.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import duzen_cekirdek as core  # noqa: E402

MIN_PY = (3, 9)


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def cmd_ortam(a) -> int:
    ok = sys.version_info >= MIN_PY
    print(f"İşletim sistemi : {platform.system()} {platform.release()} ({sys.platform})")
    print(f"Python          : {platform.python_version()} {'✓' if ok else '✗ (en az 3.9 gerekli)'}")
    print(f"Durum klasörü   : {core.state_dir()}")
    try:
        import webbrowser
        b = webbrowser.get()
        print(f"Tarayıcı        : {getattr(b, 'name', '') or 'sistem varsayılanı'} ✓")
    except Exception:
        print("Tarayıcı        : bulunamadı — pano adresini elle açabilirsiniz")
    if not core.IS_WIN and not core.IS_MAC:
        print(f"xdg-user-dir    : {'var' if shutil.which('xdg-user-dir') else 'yok (user-dirs.dirs okunur)'}")
    try:
        info = core.detect_desktop(a.masaustu)
        print(f"Masaüstü        : {info['yol']}")
        print(f"  kaynak        : {info['kaynak']}{' · OneDrive yönlendirmeli' if info['onedrive'] else ''}")
    except core.DuzenHatasi as ex:
        print(f"Masaüstü        : BELİRSİZ — {ex}")
        return 3
    print("Ek bağımlılık gerekmez (yalnızca Python standart kütüphanesi). Hiçbir şey kurulmadı.")
    return 0 if ok else 2


def cmd_tespit(a) -> int:
    info = core.detect_desktop(a.masaustu)
    if a.json:
        print(json.dumps(info, ensure_ascii=False))
    else:
        print(info["yol"])
        print(f"(kaynak: {info['kaynak']}{'; OneDrive yönlendirmeli' if info['onedrive'] else ''})")
    return 0


def cmd_plan(a) -> int:
    pp, plan = core.build_plan(a.masaustu, stability_wait=a.bekleme)
    print(pp.with_suffix(".md").read_text(encoding="utf-8"))
    print(f"İşlem kimliği: {plan['islem']}")
    print(f"Plan dosyası : {pp}")
    return 0


def cmd_onayla(a) -> int:
    rec = core.approve(a.islem, a.ifade)
    print(f"Plan {rec['islem']} onaylandı ({rec['onay_zamani']}). Panoda Başlat artık etkin.")
    return 0


def cmd_pano(a) -> int:
    import duzen_pano
    p = duzen_pano.Pano(a.islem, pace=a.sure)
    print(f"Pano: {p.url()}")
    print("Yalnızca 127.0.0.1 üzerinde dinliyor. Kapatmak için panodaki 'Panoyu Kapat' düğmesini kullanın.")
    if not core.is_approved(a.islem):
        print("Plan henüz onaylanmadı: Başlat pasif. Onay gelince pano kendiliğinden etkinleşir.")
    sys.stdout.flush()
    p.serve(open_browser=not a.tarayici_acma)
    print("Pano kapandı.")
    print(json.dumps(core.summarize(a.islem), ensure_ascii=False))
    return 0


def cmd_geri_al(a) -> int:
    if not a.son and not a.islem:
        print("İşlem kimliği verin ya da --son kullanın.", file=sys.stderr)
        return 2
    rep = core.undo(a.islem, last=a.son)
    if not rep.get("islem"):
        print(rep.get("mesaj", "Geri alınacak işlem yok."))
        return 0
    print(f"İşlem {rep['islem']}: {rep['geri_alinan']} dosya eski yerine döndü.")
    for c in rep["cakisma"]:
        print(f"  ÇAKIŞMA {c['id']} ({c['ad']}): {c['neden']}")
    for r in rep["reddedilen"]:
        print(f"  REDDEDİLDİ {r['id']}: {r['neden']}")
    for r in rep["hata"]:
        print(f"  HATA {r['id']}: {r['neden']}")
    return 0 if not (rep["cakisma"] or rep["reddedilen"] or rep["hata"]) else 1


def cmd_durum(a) -> int:
    core.reconcile_all()
    ops = core.list_ops()
    if not ops:
        print("Kayıtlı işlem yok.")
        return 0
    print("İşlem kimliği            Plan  Onay  Taşınan  Kalan  Kopyalar  Atlanan  Geri alınan  Boyut")
    for o in ops:
        print(f"{o['islem']:<24} {o['dosya']:>4}  {'evet' if o['onayli'] else 'hayır':<4}  {o['tasinan']:>7}"
              f"  {o['kalan']:>5}  {o['kopyalara']:>8}  {o['atlanan']:>7}  {o['geri_alinan']:>11}"
              f"  {core.format_size(o['boyut'])}")
    half = [o for o in ops if o["yarim"] and o["onayli"]]
    for o in half:
        print(f"\nYARIM KALAN İŞLEM: {o['islem']} — {o['kalan']} dosya bekliyor. Kaldığı yerden sürdürmek için:\n"
              f"  masaustu.py pano {o['islem']}   (aynı onaylı plan; yeni onay gerekmez, Başlat'a basılmalı)")
    return 0


def cmd_uzlastir(a) -> int:
    fixed = core.reconcile_all()
    print(f"{len(fixed)} yarım kayıt uzlaştırıldı.")
    for f in fixed:
        print(f"  {f['islem']} {f['id']}: {f['tur']} {f.get('neden', '')}")
    return 0


def main(argv=None) -> int:
    _utf8()
    ap = argparse.ArgumentParser(prog="masaustu", description="Masaüstü Düzenleyici — Desktop Organizer by Lionstone")
    sub = ap.add_subparsers(dest="komut", required=True)

    s = sub.add_parser("ortam", aliases=["env"])
    s.add_argument("--masaustu", "--desktop", dest="masaustu")
    s.set_defaults(fn=cmd_ortam)
    s = sub.add_parser("tespit", aliases=["detect"])
    s.add_argument("--masaustu", "--desktop", dest="masaustu")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_tespit)
    s = sub.add_parser("plan")
    s.add_argument("--masaustu", "--desktop", dest="masaustu", help="Yalnızca kullanıcı açıkça verdiyse ya da test klasörü için")
    s.add_argument("--bekleme", "--settle", dest="bekleme", type=float, default=2.0, help="kararlılık kontrolü arası saniye")
    s.set_defaults(fn=cmd_plan)
    s = sub.add_parser("onayla", aliases=["approve"])
    s.add_argument("islem")
    s.add_argument("--ifade", "--phrase", dest="ifade", required=True)
    s.set_defaults(fn=cmd_onayla)
    s = sub.add_parser("pano", aliases=["dashboard"])
    s.add_argument("islem")
    s.add_argument("--sure", "--seconds", dest="sure", type=float, default=core.PACE_SECONDS, help="görsel akış süresi (sn)")
    s.add_argument("--tarayici-acma", "--no-browser", dest="tarayici_acma", action="store_true")
    s.set_defaults(fn=cmd_pano)
    s = sub.add_parser("geri-al", aliases=["undo"])
    s.add_argument("islem", nargs="?")
    s.add_argument("--son", "--last", dest="son", action="store_true")
    s.set_defaults(fn=cmd_geri_al)
    s = sub.add_parser("durum", aliases=["status"])
    s.set_defaults(fn=cmd_durum)
    s = sub.add_parser("uzlastir", aliases=["reconcile"])
    s.set_defaults(fn=cmd_uzlastir)

    a = ap.parse_args(argv)
    if sys.version_info < MIN_PY:
        print("Python 3.9 veya üstü gerekli. Otomatik kurulum yapılmaz.", file=sys.stderr)
        return 2
    try:
        return a.fn(a)
    except core.BelirsizMasaustu as ex:
        print(f"MASAÜSTÜ BELİRSİZ: {ex}\nHiçbir işlem yapılmadı. Doğru yolu kullanıcıya sorun "
              "ve --masaustu ile verin.", file=sys.stderr)
        return 3
    except core.DuzenHatasi as ex:
        print(f"HATA: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(main())
