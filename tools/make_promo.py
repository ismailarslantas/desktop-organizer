"""Regenerate the README images.

1. Builds a throw-away sample desktop in a temp folder (never touches your real desktop).
2. Runs the real dashboard against it and captures EN/TR screenshots with headless Chrome/Edge.
3. Renders docs/promo/src/promo.html slides to docs/images/*.png.

Usage:  python tools/make_promo.py [--slides-only]            (needs Chrome or Edge; set CHROME=/path to override)
"""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "promo" / "src"
OUT = ROOT / "docs" / "images"
sys.path.insert(0, str(ROOT / "scripts"))

SLIDES = {"hero": (1600, 900), "dashboard": (1600, 900), "flow": (1600, 900),
          "safety": (1600, 900), "bilingual": (1600, 900), "social": (1280, 640)}


def find_browser() -> str:
    cands = [os.environ.get("CHROME", ""),
             r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
             shutil.which("google-chrome") or "", shutil.which("chromium") or ""]
    for c in cands:
        if c and Path(c).exists():
            return c
    sys.exit("Chrome or Edge not found. Set CHROME=/path/to/browser.")


def shoot(browser, url, out: Path, w, h, lang="en-US", scale=2, budget=2500):
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--lang={lang}",
                    f"--force-device-scale-factor={scale}", f"--window-size={w},{h}",
                    f"--virtual-time-budget={budget}", f"--screenshot={out}", url],
                   check=True, capture_output=True, timeout=120)


def sample_desktop(d: Path):
    d.mkdir(parents=True)
    old = time.time() - 7200
    rnd = random.Random(4)
    spec = [("jpg", 14, b"\xff\xd8\xff\xe0"), ("png", 6, b"\x89PNG\r\n\x1a\n"), ("pdf", 12, b"%PDF-1.7"),
            ("docx", 6, b"PK\x03\x04"), ("xlsx", 7, b"PK\x03\x04"), ("pptx", 4, b"PK\x03\x04"),
            ("mp4", 5, b"\x00\x00\x00\x18ftypmp42"), ("mp3", 5, b"ID3"), ("zip", 5, b"PK\x05\x06"),
            ("exe", 3, b"MZ"), ("html", 2, b"<html>"), ("dat", 3, b"??")]
    files = []
    for ext, cnt, head in spec:
        for _ in range(cnt):
            files.append((ext, head + rnd.randbytes(rnd.randint(2000, 400000))))
    rnd.shuffle(files)
    for i, (ext, data) in enumerate(files, 1):
        (d / f"file_{i:03d}.{ext}").write_bytes(data)
    for i in range(5):
        (d / f"Screenshot 2026-11-0{i + 1}.png").write_bytes(b"\x89PNG\r\n\x1a\n" + rnd.randbytes(9000))
    for i in range(3):
        (d / f"DALL-E portrait {i}.png").write_bytes(b"\x89PNG\r\n\x1a\n" + rnd.randbytes(12000))
    first = next(d.glob("*.jpg")).read_bytes()
    for i in range(3):
        (d / f"copy_{i}.jpg").write_bytes(first)
    for p in d.iterdir():
        os.utime(p, (old, old))
    (d / "Browser.lnk").write_bytes(b"L")
    (d / "Projects").mkdir()


def main():
    browser = find_browser()
    OUT.mkdir(parents=True, exist_ok=True)
    shots = SRC / "shots"
    shots.mkdir(exist_ok=True)
    if "--slides-only" not in sys.argv:
        capture(browser, shots)
    page = (SRC / "promo.html").as_uri()
    for i, (name, (w, h)) in enumerate(SLIDES.items(), 1):
        target = OUT / (f"{i:02d}-{name}.png" if name != "social" else "social-preview.png")
        shoot(browser, f"{page}?s={name}", target, w, h, scale=1, budget=1500)
        print("wrote", target.relative_to(ROOT))


def capture(browser, shots: Path):
    tmp = Path(tempfile.mkdtemp(prefix="desktop-organizer-promo-"))
    os.environ["MASAUSTU_DUZENLEYICI_DURUM"] = str(tmp / "state")
    import duzen_cekirdek as core
    import duzen_pano

    try:
        sample_desktop(tmp / "Desktop")
        _pp, plan = core.build_plan(str(tmp / "Desktop"), stability_wait=0.2)
        op = plan["islem"]
        p = duzen_pano.Pano(op, pace=50)
        threading.Thread(target=p.serve, kwargs={"open_browser": False}, daemon=True).start()
        url = p.url()
        size = (1360, 1000)
        for lang, tag in (("en-US", "en"), ("tr", "tr")):
            shoot(browser, url, shots / f"preview-{tag}.png", *size, lang=lang)
        core.approve(op, core.APPROVAL_PHRASE)
        req = urllib.request.Request(f"{p.origin}/api/baslat", method="POST",
                                     headers={"X-Oturum-Anahtari": p.token, "Origin": p.origin})
        urllib.request.urlopen(req).read()
        time.sleep(22)
        for lang, tag in (("en-US", "en"), ("tr", "tr")):
            shoot(browser, url, shots / f"running-{tag}.png", *size, lang=lang)
        while p.state()["durum"] != "tamamlandi":
            time.sleep(0.5)
        time.sleep(1)
        for lang, tag in (("en-US", "en"), ("tr", "tr")):
            shoot(browser, url, shots / f"done-{tag}.png", *size, lang=lang)
        p.close()
        for f in shots.iterdir():
            shutil.copy(f, OUT / f"dashboard-{f.name}")
    finally:
        os.environ.pop("MASAUSTU_DUZENLEYICI_DURUM", None)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
