"""Masaüstü Düzenleyici — çekirdek.

Yalnızca Python standart kütüphanesini kullanır. Görevleri:
  * gerçek kullanıcı masaüstünü tespit etmek,
  * masaüstü kökündeki normal dosyaları sınıflandırıp plan çıkarmak,
  * onaylanmış planı güvenli biçimde (yalnızca taşıma, üzerine yazmadan) uygulamak,
  * her taşımayı kalıcı günlüğe yazmak, yarım kalanları uzlaştırmak ve geri almak.

Hiçbir dosya silinmez, üzerine yazılmaz ya da içeriği değiştirilmez.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"

ROOT_NAME = "Masaüstü Düzeni"
APPROVAL_PHRASE = "Planı onaylıyorum"
RECENT_SECONDS = 15 * 60
PACE_SECONDS = 50.0
STATE_ENV = "MASAUSTU_DUZENLEYICI_DURUM"

# anahtar: (klasör adı, etiket, renk)
CATEGORIES: dict[str, tuple[str, str, str]] = {
    "01": ("01_Görseller", "Görseller", "#3b82f6"),
    "02": ("02_YZ Görselleri", "YZ Görselleri", "#8b5cf6"),
    "03": ("03_Ekran Görüntüleri", "Ekran Görüntüleri", "#06b6d4"),
    "04": ("04_Videolar", "Videolar", "#ef4444"),
    "05": ("05_Ses", "Ses", "#ec4899"),
    "06": ("06_Belgeler", "Belgeler", "#f59e0b"),
    "07": ("07_Tablolar", "Tablolar", "#10b981"),
    "08": ("08_Sunumlar", "Sunumlar", "#f97316"),
    "09": ("09_Web Sayfaları", "Web Sayfaları", "#6366f1"),
    "10": ("10_Arşivler", "Arşivler", "#a16207"),
    "11": ("11_Kurulum", "Kurulum", "#64748b"),
    "12": ("12_Diğer", "Diğer", "#94a3b8"),
    "13": ("13_Kopyalar", "Kopyalar", "#14b8a6"),
}

IMAGE_EXT = {"jpg", "jpeg", "jfif", "png", "gif", "webp", "bmp", "tif", "tiff", "heic", "heif",
             "avif", "svg", "ico", "psd", "raw", "cr2", "cr3", "nef", "arw", "dng", "orf", "rw2"}
VIDEO_EXT = {"mp4", "mov", "avi", "mkv", "wmv", "flv", "webm", "m4v", "mpg", "mpeg", "3gp", "mts", "m2ts"}
AUDIO_EXT = {"mp3", "wav", "flac", "aac", "m4a", "ogg", "opus", "wma", "aif", "aiff", "mid", "midi", "amr"}
DOC_EXT = {"pdf", "doc", "docx", "odt", "rtf", "txt", "md", "pages", "epub", "tex", "xps", "oxps"}
SHEET_EXT = {"xls", "xlsx", "xlsm", "xlsb", "ods", "csv", "tsv", "numbers"}
SLIDE_EXT = {"ppt", "pptx", "pps", "ppsx", "odp", "key"}
WEB_EXT = {"html", "htm", "xhtml", "mhtml", "mht"}
ARCHIVE_EXT = {"zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "tbz2", "xz", "zst", "lz", "lzma"}
INSTALL_EXT = {"exe", "msi", "msix", "msixbundle", "appx", "appxbundle", "dmg", "pkg", "mpkg",
               "deb", "rpm", "appimage", "apk", "iso", "flatpakref", "snap"}
SHORTCUT_EXT = {"lnk", "url", "webloc", "desktop", "inetloc"}
TEMP_EXT = {"crdownload", "part", "partial", "download", "tmp", "temp", "opdownload",
            "!ut", "bc!", "aria2", "dtapart", "fdmdownload"}
SYSTEM_NAMES = {"desktop.ini", "thumbs.db", ".ds_store", ".localized", "ehthumbs.db",
                "$recycle.bin", "icon\r"}
RASTER_MAGIC = {"png", "jpg", "jpeg", "jfif", "gif", "webp", "bmp", "tif", "tiff", "heic", "heif", "avif"}

SCREENSHOT_NAME = re.compile(
    r"screenshot|screen ?shot|screen_shot|ekran g[öo]r[üu]nt[üu]s[üu]|ekran resmi|ekran al[ıi]nt[ıi]s[ıi]"
    r"|bildschirmfoto|capture d.[ée]cran|captura de pantalla|schermata|schermafbeelding"
    r"|\bsnip(ping)?\b|screencap|\bscr_\d", re.IGNORECASE)
SCREENSHOT_META = re.compile(
    rb"screenshot|greenshot|sharex|spectacle|flameshot|snipping tool|lightshot|gnome-screenshot",
    re.IGNORECASE)
AI_NAME = re.compile(
    r"dall[\s·\-_.]?e|midjourney|\bmj_|chatgpt image|gemini_generated_image|adobe ?firefly|^firefly[\s_-]"
    r"|stable[\s_-]?diffusion|comfyui|novelai|leonardo_phoenix|ideogram|\bsdxl\b|\bai[\s_-]generated",
    re.IGNORECASE)
AI_META = re.compile(
    rb"trainedalgorithmicmedia|midjourney|\bdall(?:[\s\-._]|\xc2\xb7)?e\b|novelai|stable diffusion|comfyui"
    rb"|invokeai|adobe firefly|google imagen|\bimagen [234]\b|\bopenai\b|gpt-4o|sd-metadata|negative prompt",
    re.IGNORECASE)
AI_PNG_KEYS = {b"parameters", b"prompt", b"workflow", b"sd-metadata", b"invokeai_metadata",
               b"dream", b"generation_data"}
HTML_COMPANION = ("_files", "_dosyalar", "-files", "_archivos", "-dateien", "_fichiers", "_file", "_bestanden")

# Windows dosya öznitelikleri
FA_HIDDEN, FA_SYSTEM = 0x2, 0x4
FA_REPARSE = 0x400
FA_OFFLINE = 0x1000
FA_RECALL_ON_OPEN = 0x40000
FA_RECALL_ON_DATA = 0x400000
CLOUD_ATTRS = FA_OFFLINE | FA_RECALL_ON_OPEN | FA_RECALL_ON_DATA
SF_DATALESS = 0x40000000  # macOS iCloud: içerik yerelde değil


class DuzenHatasi(Exception):
    """Kullanıcıya gösterilebilir hata."""


class BelirsizMasaustu(DuzenHatasi):
    """Gerçek masaüstü yolu güvenle belirlenemedi."""


class FarkliSurucu(OSError):
    pass


# --------------------------------------------------------------------------- yardımcılar

def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def name_key(name: str) -> str:
    return nfc(name).casefold()


def format_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    for u in units:
        if v < 1024 or u == units[-1]:
            if u == "B":
                return f"{int(v)} B"
            return f"{v:.1f} {u}".replace(".", ",")
        v /= 1024
    return f"{n} B"


def same_path(a, b) -> bool:
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def real_same(a, b) -> bool:
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def is_under(child, parent) -> bool:
    c = os.path.normcase(os.path.abspath(child))
    p = os.path.normcase(os.path.abspath(parent)).rstrip("\\/")
    return c == p or c.startswith(p + os.sep)


def attrs(st) -> int:
    return getattr(st, "st_file_attributes", 0) or 0


def is_link_like(st) -> bool:
    """Sembolik bağlantı, junction ya da bağlama noktası mı?

    OneDrive dosyaları da reparse noktasıdır ama ad vekili (name surrogate) değildir;
    onlar bağlantı sayılmaz. Bulutta-yalnızca durumu ayrıca denetlenir.
    """
    if stat.S_ISLNK(st.st_mode):
        return True
    if attrs(st) & FA_REPARSE:
        tag = getattr(st, "st_reparse_tag", 0) or 0
        return bool(tag & 0x20000000) or tag == 0
    return False


def is_cloud_only(st) -> bool:
    if attrs(st) & CLOUD_ATTRS:
        return True
    return bool((getattr(st, "st_flags", 0) or 0) & SF_DATALESS)


def is_hidden(name: str, st) -> bool:
    if name.startswith(".") or name.startswith("~$") or name.casefold() in SYSTEM_NAMES:
        return True
    if attrs(st) & (FA_HIDDEN | FA_SYSTEM):
        return True
    return bool((getattr(st, "st_flags", 0) or 0) & getattr(stat, "UF_HIDDEN", 0x8000))


def ext_of(name: str) -> str:
    n = name.casefold()
    for double in (".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst"):
        if n.endswith(double):
            return double[1:]
    return Path(n).suffix[1:]


def split_name(name: str) -> tuple[str, str]:
    n = name.casefold()
    for double in (".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst"):
        if n.endswith(double):
            return name[: -len(double)], name[-len(double):]
    p = Path(name)
    if p.suffix and p.stem:
        return p.stem, p.suffix
    return name, ""


def fingerprint(path, size: int) -> str:
    """Boyut + ilk/son 64 KB üzerinden hızlı doğrulama izi (dosyayı değiştirmez)."""
    h = hashlib.sha256()
    h.update(str(size).encode())
    with open(path, "rb") as f:
        h.update(f.read(65536))
        if size > 131072:
            f.seek(size - 65536)
            h.update(f.read(65536))
    return h.hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if IS_WIN:
        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = ctypes.c_void_p
        h = k32.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            k32.GetExitCodeProcess(ctypes.c_void_p(h), ctypes.byref(code))
            return code.value == 259
        finally:
            k32.CloseHandle(ctypes.c_void_p(h))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def is_locked(path) -> bool:
    """Başka bir süreç dosyaya yazıyor mu? (Windows'ta yazma paylaşımı vermeden açmayı dener.)"""
    if IS_WIN:
        k32 = ctypes.windll.kernel32
        k32.CreateFileW.restype = ctypes.c_void_p
        k32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                                   ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        h = k32.CreateFileW(str(path), 0x80000000, 0x1, None, 3, 0x80, None)  # GENERIC_READ, SHARE_READ
        if h in (None, ctypes.c_void_p(-1).value):
            return True
        k32.CloseHandle(ctypes.c_void_p(h))
        return False
    try:
        with open(path, "rb") as f:
            f.read(1)
        return False
    except OSError:
        return True


# --------------------------------------------------------------------------- durum klasörü

def state_dir() -> Path:
    env = os.environ.get(STATE_ENV)
    if env:
        p = Path(env)
    elif IS_WIN:
        p = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "MasaustuDuzenleyici"
    elif IS_MAC:
        p = Path.home() / "Library" / "Application Support" / "MasaustuDuzenleyici"
    else:
        p = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "masaustu-duzenleyici"
    (p / "planlar").mkdir(parents=True, exist_ok=True)
    (p / "islemler").mkdir(parents=True, exist_ok=True)
    return p


def plan_path(op_id: str) -> Path:
    if not re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{6}", op_id or ""):
        raise DuzenHatasi(f"Geçersiz işlem kimliği: {op_id!r}")
    return state_dir() / "planlar" / f"{op_id}.json"


def approval_path(op_id: str) -> Path:
    return plan_path(op_id).with_suffix(".onay.json")


# --------------------------------------------------------------------------- masaüstü tespiti

FOLDERID_DESKTOP = "B4BFCC3A-DB2C-424C-B029-7FE99A87C641"
FOLDERID_PUBLIC_DESKTOP = "C4AA340D-F20F-4863-AFEF-F87EF2E6BA25"


def _win_known_folder(guid: str):
    import uuid

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                    ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]

    u = uuid.UUID(guid)
    g = GUID(u.fields[0], u.fields[1], u.fields[2], (ctypes.c_ubyte * 8)(*u.bytes[8:]))
    out = ctypes.c_wchar_p()
    fn = ctypes.windll.shell32.SHGetKnownFolderPath
    fn.argtypes = [ctypes.POINTER(GUID), ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
    try:
        hr = fn(ctypes.byref(g), 0, None, ctypes.byref(out))
        if hr != 0:
            return None
        return out.value
    finally:
        if out:
            ctypes.windll.ole32.CoTaskMemFree(out)


def _win_registry_desktop():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
            val, _ = winreg.QueryValueEx(k, "Desktop")
        return os.path.expandvars(val)
    except OSError:
        return None


def _public_desktops() -> list[str]:
    out = []
    if IS_WIN:
        p = _win_known_folder(FOLDERID_PUBLIC_DESKTOP)
        if p:
            out.append(p)
        pub = os.environ.get("PUBLIC")
        if pub:
            out.append(os.path.join(pub, "Desktop"))
    elif IS_MAC:
        out.append("/Users/Shared")
    return out


def validate_desktop(path: str, source: str) -> dict:
    if not path:
        raise BelirsizMasaustu("Masaüstü yolu boş geldi.")
    p = os.path.abspath(path)
    try:
        st = os.lstat(p)
    except OSError:
        raise BelirsizMasaustu(f"Masaüstü klasörü bulunamadı: {p}")
    if not stat.S_ISDIR(st.st_mode):
        raise BelirsizMasaustu(f"Masaüstü yolu bir klasör değil: {p}")
    if is_link_like(st):
        raise BelirsizMasaustu(f"Masaüstü yolu bir bağlantı/junction: {p}. Gerçek hedef belirsiz.")
    for pub in _public_desktops():
        if same_path(p, pub):
            raise DuzenHatasi("Ortak/Public masaüstüne dokunulmaz.")
    if same_path(p, Path.home()):
        raise BelirsizMasaustu("Masaüstü yolu ev klasörünün kendisi görünüyor; belirsiz.")
    onedrive = False
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        od = os.environ.get(var)
        if od and is_under(p, od):
            onedrive = True
    return {"yol": p, "kaynak": source, "onedrive": onedrive}


def detect_desktop(override: str | None = None) -> dict:
    """Gerçek masaüstünü bulur; belirsizse BelirsizMasaustu fırlatır."""
    if override:
        return validate_desktop(override, "kullanıcının verdiği yol")
    if IS_WIN:
        kf = _win_known_folder(FOLDERID_DESKTOP)
        reg = _win_registry_desktop()
        if kf and reg and not same_path(kf, reg):
            raise BelirsizMasaustu(f"Windows Known Folder ({kf}) ile kayıt defteri ({reg}) farklı yol veriyor.")
        if not (kf or reg):
            raise BelirsizMasaustu("Windows masaüstü yolu okunamadı.")
        return validate_desktop(kf or reg, "Windows Known Folder (FOLDERID_Desktop)")
    if IS_MAC:
        return validate_desktop(str(Path.home() / "Desktop"), "macOS kullanıcı masaüstü (~/Desktop)")
    # Linux / diğer: XDG
    home = str(Path.home())
    path = None
    try:
        r = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            path, src = r.stdout.strip(), "xdg-user-dir DESKTOP"
    except (OSError, subprocess.SubprocessError):
        pass
    if not path:
        cfg = Path(os.environ.get("XDG_CONFIG_HOME") or Path(home) / ".config") / "user-dirs.dirs"
        if cfg.is_file():
            m = re.search(r'^XDG_DESKTOP_DIR="([^"]+)"', cfg.read_text(encoding="utf-8", errors="replace"), re.M)
            if m:
                path, src = m.group(1).replace("$HOME", home), "~/.config/user-dirs.dirs"
    if not path:
        raise BelirsizMasaustu("XDG masaüstü yolu bulunamadı (xdg-user-dir ve user-dirs.dirs yok).")
    if same_path(path, home):
        raise BelirsizMasaustu("XDG masaüstü yolu ev klasörünü gösteriyor; masaüstü tanımlı değil.")
    return validate_desktop(path, src)


# --------------------------------------------------------------------------- sınıflandırma

def _read_head(path, n=64) -> bytes:
    with open(path, "rb") as f:
        return f.read(n)


def sniff(head: bytes) -> str | None:
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head.startswith(b"BM"):
        return "bmp"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"heic", b"heix", b"mif1", b"msf1", b"heim", b"heis"):
            return "heic"
        if brand in (b"avif", b"avis"):
            return "avif"
        return "mp4"
    if head.startswith(b"%PDF"):
        return "pdf"
    return None


IMAGE_SNIFF = {"png", "jpg", "gif", "webp", "bmp", "tiff", "heic", "avif"}


def _png_meta(path, limit=8 << 20) -> tuple[set[bytes], bytes]:
    keys: set[bytes] = set()
    blob = bytearray()
    with open(path, "rb") as f:
        f.seek(8)
        read = 0
        for _ in range(2000):
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            length = int.from_bytes(hdr[:4], "big")
            ctype = hdr[4:8]
            if ctype in (b"tEXt", b"iTXt", b"zTXt", b"eXIf", b"caBX") and length <= (2 << 20) and read < limit:
                data = f.read(length)
                read += length
                if ctype in (b"tEXt", b"iTXt", b"zTXt"):
                    key = data.split(b"\x00", 1)[0].lower()
                    keys.add(key)
                    if ctype == b"zTXt":
                        import zlib
                        try:
                            data = key + b"\x00" + zlib.decompress(data[len(key) + 2:])
                        except zlib.error:
                            pass
                blob += data + b"\n"
                f.seek(4, 1)
            else:
                f.seek(length + 4, 1)
            if ctype == b"IEND":
                break
    return keys, bytes(blob)


def _jpeg_meta(path, limit=8 << 20) -> bytes:
    blob = bytearray()
    with open(path, "rb") as f:
        if f.read(2) != b"\xff\xd8":
            return b""
        while len(blob) < limit:
            b = f.read(1)
            while b == b"\xff":
                b = f.read(1)
            if not b:
                break
            marker = b[0]
            if marker in (0xD9, 0xDA):  # EOI / SOS: meta bölümü bitti
                break
            if 0xD0 <= marker <= 0xD7 or marker == 0x01:
                continue
            ln = f.read(2)
            if len(ln) < 2:
                break
            seg = int.from_bytes(ln, "big") - 2
            if 0xE0 <= marker <= 0xEF or marker == 0xFE:
                blob += f.read(max(seg, 0)) + b"\n"
            else:
                f.seek(max(seg, 0), 1)
    return bytes(blob)


def _webp_meta(path, limit=8 << 20) -> bytes:
    blob = bytearray()
    with open(path, "rb") as f:
        f.seek(12)
        while len(blob) < limit:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            cid, ln = hdr[:4], int.from_bytes(hdr[4:], "little")
            if cid in (b"EXIF", b"XMP "):
                blob += f.read(ln) + b"\n"
            else:
                f.seek(ln, 1)
            if ln % 2:
                f.seek(1, 1)
    return bytes(blob)


def image_metadata(path, kind: str) -> tuple[set[bytes], bytes]:
    try:
        if kind == "png":
            return _png_meta(path)
        if kind == "jpg":
            return set(), _jpeg_meta(path)
        if kind == "webp":
            return set(), _webp_meta(path)
    except OSError:
        pass
    return set(), b""


def classify(path: Path, name: str) -> tuple[str, str]:
    """(kategori anahtarı, gerekçe) döndürür. Dosyayı yalnızca okur."""
    ext = ext_of(name)
    head = _read_head(path)
    kind = sniff(head)

    if ext in IMAGE_EXT or (not ext and kind in IMAGE_SNIFF):
        if ext in RASTER_MAGIC and kind not in IMAGE_SNIFF:
            return "12", f".{ext} uzantılı ama dosya başlığı görsel değil"
        reason_base = f".{ext} görsel" if ext else f"uzantısız; başlık {kind} görseli"
        keys, meta = image_metadata(path, kind or "")
        if AI_NAME.search(name):
            return "02", "dosya adında açık YZ üretici işareti"
        if keys & AI_PNG_KEYS:
            k = b", ".join(sorted(keys & AI_PNG_KEYS)).decode("latin-1")
            return "02", f"PNG metadata'sında YZ üretici alanı ({k})"
        m = AI_META.search(meta) if meta else None
        if m:
            return "02", f"metadata'da YZ üretici işareti ({m.group(0).decode('latin-1', 'replace')})"
        if SCREENSHOT_NAME.search(name):
            return "03", "dosya adında ekran görüntüsü işareti"
        m = SCREENSHOT_META.search(meta) if meta else None
        if m:
            return "03", f"metadata'da ekran görüntüsü işareti ({m.group(0).decode('latin-1', 'replace')})"
        return "01", reason_base + "; YZ/ekran görüntüsü işareti yok"
    if ext in VIDEO_EXT:
        return "04", f".{ext} video"
    if ext in AUDIO_EXT:
        return "05", f".{ext} ses"
    if ext in DOC_EXT:
        if ext == "pdf" and kind != "pdf":
            return "12", ".pdf uzantılı ama başlık PDF değil"
        return "06", f".{ext} belge"
    if ext in SHEET_EXT:
        return "07", f".{ext} tablo"
    if ext in SLIDE_EXT:
        return "08", f".{ext} sunum"
    if ext in WEB_EXT:
        return "09", f".{ext} web sayfası"
    if ext in ARCHIVE_EXT or ext.startswith("tar."):
        return "10", f".{ext} arşiv"
    if ext in INSTALL_EXT:
        return "11", f".{ext} kurulum/disk görüntüsü"
    if not ext and kind == "pdf":
        return "06", "uzantısız; başlık PDF"
    return "12", (f".{ext} tanınmayan tür" if ext else "uzantısız, tanınmayan tür")


# --------------------------------------------------------------------------- tarama ve plan

def _scan(desktop: str, recent_seconds: float, now: float):
    entries = []
    folders, shortcuts, skipped = [], [], []
    with os.scandir(desktop) as it:
        names = sorted(it, key=lambda e: name_key(e.name))
    dir_keys = set()
    for e in names:
        try:
            st = os.lstat(e.path)
        except OSError:
            continue
        if stat.S_ISDIR(st.st_mode) and not is_link_like(st):
            dir_keys.add(name_key(e.name))
    all_keys = {name_key(e.name) for e in names}
    for e in names:
        name = e.name
        try:
            st = os.lstat(e.path)
        except OSError as ex:
            skipped.append({"ad": name, "neden": f"erişilemiyor ({ex.strerror})"})
            continue
        if is_link_like(st):
            skipped.append({"ad": name, "neden": "sembolik bağlantı/junction; hedefine gidilmez"})
            continue
        if stat.S_ISDIR(st.st_mode):
            if is_hidden(name, st):
                continue
            folders.append(name)
            continue
        if not stat.S_ISREG(st.st_mode):
            skipped.append({"ad": name, "neden": "normal dosya değil"})
            continue
        if is_hidden(name, st):
            skipped.append({"ad": name, "neden": "gizli/sistem dosyası"})
            continue
        if office_lock_present(name, all_keys):
            skipped.append({"ad": name, "neden": "şu an Office'te açık (~$ kilit dosyası var)"})
            continue
        if is_cloud_only(st):
            skipped.append({"ad": name, "neden": "yalnızca bulutta; indirme başlatılmaz"})
            continue
        ext = ext_of(name)
        if ext in SHORTCUT_EXT:
            shortcuts.append(name)
            continue
        if ext in TEMP_EXT or name.endswith("~"):
            skipped.append({"ad": name, "neden": "geçici/yarım indirme dosyası"})
            continue
        age = now - st.st_mtime
        if age < recent_seconds:
            mins = max(0, int(age // 60))
            skipped.append({"ad": name, "neden": f"son 15 dakikada değiştirilmiş (~{mins} dk önce)"})
            continue
        if ext in WEB_EXT:
            stem = name_key(split_name(name)[0])
            if any(stem + suf in dir_keys for suf in HTML_COMPANION):
                skipped.append({"ad": name, "neden": "bağlı kaynak klasörü var; klasörlere dokunulmadığı için atlandı"})
                continue
        if is_locked(e.path):
            skipped.append({"ad": name, "neden": "kilitli veya okunamıyor"})
            continue
        entries.append((name, e.path, st))
    return entries, folders, shortcuts, skipped


def office_lock_present(name: str, keys: set[str]) -> bool:
    """Word/Excel/PowerPoint açık belge için yanına '~$' ile başlayan kilit dosyası koyar.

    Uzun adlarda Office ilk bir ya da iki karakteri atar (ör. 'Rapor.docx' -> '~$apor.docx').
    """
    if name.startswith("~$"):
        return False
    return any(name_key("~$" + name[i:]) in keys for i in (0, 1, 2) if len(name) - i > 4)


def _existing_names(d: Path) -> set[str]:
    try:
        with os.scandir(d) as it:
            return {name_key(e.name) for e in it}
    except OSError:
        return set()


def unique_name(name: str, taken: set[str]) -> str:
    if name_key(name) not in taken:
        return name
    stem, suf = split_name(name)
    i = 2
    while True:
        cand = f"{stem} ({i}){suf}"
        if name_key(cand) not in taken:
            return cand
        i += 1


def check_root(desktop: str) -> Path:
    root = Path(desktop) / ROOT_NAME
    try:
        st = os.lstat(root)
    except FileNotFoundError:
        return root
    if is_link_like(st):
        raise DuzenHatasi(f"'{ROOT_NAME}' bir bağlantı/junction; güvenli hedef değil.")
    if not stat.S_ISDIR(st.st_mode):
        raise DuzenHatasi(f"Masaüstünde '{ROOT_NAME}' adında klasör olmayan bir öğe var.")
    if not resolves_inside(root, Path(desktop)):
        raise DuzenHatasi(f"'{ROOT_NAME}' masaüstü dışını gösteriyor.")
    return root


def resolves_inside(path: Path, parent: Path) -> bool:
    """path gerçekten parent'ın doğrudan çocuğu mu (bağlantı üzerinden başka yere gitmiyor mu)?"""
    expect = os.path.join(os.path.realpath(parent), path.name)
    return os.path.normcase(os.path.realpath(path)) == os.path.normcase(expect)


def build_plan(desktop_override: str | None = None, stability_wait: float = 2.0,
               recent_seconds: float = RECENT_SECONDS) -> tuple[Path, dict]:
    reconcile_all()
    info = detect_desktop(desktop_override)
    desktop = info["yol"]
    sd = state_dir()
    if is_under(sd, desktop):
        raise DuzenHatasi("Durum klasörü masaüstünün içinde olamaz.")
    root = check_root(desktop)
    now = time.time()
    entries, folders, shortcuts, skipped = _scan(desktop, recent_seconds, now)

    # kararlılık: iki ölçüm arasında boyut/zaman değişenleri ayıkla
    if stability_wait > 0 and entries:
        time.sleep(stability_wait)
    stable = []
    for name, path, st in entries:
        try:
            st2 = os.lstat(path)
        except OSError:
            skipped.append({"ad": name, "neden": "inceleme sırasında kayboldu"})
            continue
        if (st2.st_size, st2.st_mtime_ns) != (st.st_size, st.st_mtime_ns):
            skipped.append({"ad": name, "neden": "iki kontrol arasında boyutu/zamanı değişti"})
            continue
        stable.append((name, path, st2))

    items = []
    for name, path, st in stable:
        try:
            cat, why = classify(Path(path), name)
            fp = fingerprint(path, st.st_size)
        except OSError as ex:
            skipped.append({"ad": name, "neden": f"okunamadı ({ex.strerror or ex})"})
            continue
        items.append({"ad": name, "kaynak": path, "kategori": cat, "gerekce": why,
                      "boyut": st.st_size, "mtime_ns": st.st_mtime_ns,
                      "kimlik": [st.st_dev, st.st_ino], "iz": fp})

    # kopyalar: boyut grubu -> SHA-256
    by_size: dict[int, list[dict]] = {}
    for it in items:
        if it["boyut"] > 0:
            by_size.setdefault(it["boyut"], []).append(it)
    dup_groups = []
    for size, group in by_size.items():
        if len(group) < 2:
            continue
        by_hash: dict[str, list[dict]] = {}
        for it in group:
            try:
                it["sha256"] = sha256_file(it["kaynak"])
            except OSError:
                continue
            by_hash.setdefault(it["sha256"], []).append(it)
        for digest, same in by_hash.items():
            if len(same) < 2:
                continue
            same.sort(key=lambda x: (x["mtime_ns"], len(x["ad"]), name_key(x["ad"])))
            keeper, copies = same[0], same[1:]
            for c in copies:
                c["kopya_asil"] = keeper["ad"]
                c["normal_kategori"] = c["kategori"]
                c["kategori"] = "13"
                c["gerekce"] = f"'{keeper['ad']}' ile aynı içerik (SHA-256 {digest[:12]}…)"
            dup_groups.append({"sha256": digest, "boyut": size, "asil": keeper["ad"],
                               "kopyalar": [c["ad"] for c in copies]})

    # kimlik ve hedef adları
    items.sort(key=lambda x: name_key(x["ad"]))
    taken: dict[str, set[str]] = {}
    collisions = []
    for i, it in enumerate(items, 1):
        it["id"] = f"D-{i:04d}"
        folder = CATEGORIES[it["kategori"]][0]
        if folder not in taken:
            taken[folder] = _existing_names(root / folder)
        new = unique_name(it["ad"], taken[folder])
        taken[folder].add(name_key(new))
        if new != it["ad"]:
            collisions.append({"id": it["id"], "ad": it["ad"], "yeni_ad": new, "klasor": folder})
        it["hedef_ad"] = new
        it["hedef"] = str(root / folder / new)

    op_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
    plan = {
        "surum": 1, "islem": op_id, "olusturma": now_iso(),
        "masaustu": desktop, "masaustu_kaynagi": info["kaynak"], "onedrive": info["onedrive"],
        "kok": str(root), "isletim_sistemi": sys.platform,
        "kurallar": {"son_degisiklik_dk": recent_seconds / 60, "kopya_asil_kurali":
                     "en eski değiştirilme zamanı; eşitse en kısa ad; eşitse alfabetik"},
        "ogeler": items, "kopya_gruplari": dup_groups, "cakismalar": collisions,
        "atlananlar": skipped, "klasorler": folders, "kisayollar": shortcuts,
    }
    pp = plan_path(op_id)
    data = json.dumps(plan, ensure_ascii=False, indent=1).encode("utf-8")
    pp.write_bytes(data)
    pp.with_suffix(".md").write_text(plan_markdown(plan), encoding="utf-8")
    return pp, plan


def _md(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def plan_markdown(plan: dict) -> str:
    items = plan["ogeler"]
    out = [f"# Masaüstü düzenleme planı — işlem `{plan['islem']}`", "",
           f"- **Gerçek masaüstü:** `{plan['masaustu']}`  ",
           f"  (kaynak: {plan['masaustu_kaynagi']}{'; OneDrive yönlendirmeli' if plan['onedrive'] else ''})",
           f"- **Hedef ana klasör:** `{plan['kok']}`",
           f"- **Taşınacak dosya:** {len(items)} · **Toplam:** {format_size(sum(i['boyut'] for i in items))}",
           "", "## Özet", "", "| Kategori | Dosya | Toplam boyut | Hedef klasör |", "|---|---:|---:|---|"]
    for key, (folder, label, _c) in CATEGORIES.items():
        sel = [i for i in items if i["kategori"] == key]
        if sel:
            out.append(f"| {label} | {len(sel)} | {format_size(sum(i['boyut'] for i in sel))} | `{ROOT_NAME}/{folder}` |")
    out += ["", "## Ayrıntılı plan", "", "| Kimlik | Kaynak adı | Hedef yol | Gerekçe |", "|---|---|---|---|"]
    for i in items:
        rel = f"{ROOT_NAME}/{CATEGORIES[i['kategori']][0]}/{i['hedef_ad']}"
        out.append(f"| {i['id']} | {_md(i['ad'])} | `{_md(rel)}` | {_md(i['gerekce'])} |")
    out += ["", "## Kopya grupları", ""]
    if plan["kopya_gruplari"]:
        out.append(f"Kural: {plan['kurallar']['kopya_asil_kurali']} olan dosya normal kategorisine gider; "
                   "diğerleri `13_Kopyalar`'a taşınır. Hiçbiri silinmez, disk alanı değişmez.")
        out.append("")
        for g in plan["kopya_gruplari"]:
            out.append(f"- `{g['sha256'][:12]}…` ({format_size(g['boyut'])}): asıl **{_md(g['asil'])}** → "
                       + ", ".join(_md(c) for c in g["kopyalar"]))
    else:
        out.append("Aynı içerikli dosya bulunmadı.")
    out += ["", "## İsim çakışmaları", ""]
    if plan["cakismalar"]:
        for c in plan["cakismalar"]:
            out.append(f"- {_md(c['ad'])} → `{c['klasor']}/{_md(c['yeni_ad'])}` (hedefte aynı ad var)")
    else:
        out.append("Çakışma yok.")
    out += ["", "## Atlanan öğeler", ""]
    if plan["atlananlar"]:
        out += ["| Öğe | Neden |", "|---|---|"]
        out += [f"| {_md(s['ad'])} | {_md(s['neden'])} |" for s in plan["atlananlar"]]
    else:
        out.append("Atlanan öğe yok.")
    out += ["", "## Dokunulmayanlar", "",
            f"- Klasörler ({len(plan['klasorler'])}): " + (", ".join(_md(f) for f in plan["klasorler"]) or "—"),
            f"- Kısayollar ({len(plan['kisayollar'])}): " + (", ".join(_md(f) for f in plan["kisayollar"]) or "—"),
            "", f"Bu planı uygulamak için tam olarak **\"{APPROVAL_PHRASE}\"** yazın. "
            "Onay yalnızca bu işlem kimliği ve bu listedeki dosyalar için geçerlidir."]
    return "\n".join(out) + "\n"


def load_plan(op_id: str) -> tuple[dict, str]:
    pp = plan_path(op_id)
    if not pp.is_file():
        raise DuzenHatasi(f"Plan bulunamadı: {op_id}")
    data = pp.read_bytes()
    return json.loads(data.decode("utf-8")), hashlib.sha256(data).hexdigest()


def approve(op_id: str, phrase: str) -> dict:
    if (phrase or "").strip() != APPROVAL_PHRASE:
        raise DuzenHatasi(f'Onay ifadesi tam olarak "{APPROVAL_PHRASE}" olmalı.')
    _plan, digest = load_plan(op_id)
    rec = {"islem": op_id, "plan_sha256": digest, "onay_zamani": now_iso(), "ifade": APPROVAL_PHRASE}
    approval_path(op_id).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


def is_approved(op_id: str, digest: str | None = None) -> bool:
    ap = approval_path(op_id)
    if not ap.is_file():
        return False
    try:
        rec = json.loads(ap.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if digest is None:
        _p, digest = load_plan(op_id)
    return rec.get("plan_sha256") == digest and rec.get("ifade") == APPROVAL_PHRASE


# --------------------------------------------------------------------------- kilit ve günlük

class GlobalLock:
    """Aynı anda tek düzenleme/geri alma. Durum klasöründe O_EXCL kilit dosyası."""

    def __init__(self, purpose: str, op_id: str = ""):
        self.path = state_dir() / "kilit.json"
        self.purpose, self.op_id, self.held = purpose, op_id, False

    def acquire(self):
        for _ in range(3):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    info = json.loads(self.path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    info = {}
                pid = int(info.get("pid", 0) or 0)
                if pid and pid_alive(pid):
                    raise DuzenHatasi(
                        f"Başka bir işlem sürüyor ({info.get('amac', '?')} {info.get('islem', '')}, pid {pid}). "
                        "Aynı anda iki düzenleme ya da geri alma yapılamaz.")
                if not info and time.time() - self.path.stat().st_mtime < 5:
                    time.sleep(0.2)
                    continue
                self.path.unlink()  # sahibi kapanmış kilit (bizim durum dosyamız)
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"pid": os.getpid(), "amac": self.purpose, "islem": self.op_id, "zaman": now_iso()}, f)
            self.held = True
            return self
        raise DuzenHatasi("Kilit alınamadı.")

    def release(self):
        if self.held:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self.held = False

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *a):
        self.release()


class Journal:
    def __init__(self, op_id: str):
        self.dir = state_dir() / "islemler" / op_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "gunluk.jsonl"

    def append(self, rec: dict):
        rec = {"zaman": now_iso(), **rec}
        line = json.dumps(rec, ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    def records(self) -> list[dict]:
        if not self.path.is_file():
            return []
        out = []
        with open(self.path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue  # çökme sırasında yarım kalmış satır
        return out


MOVE_FINAL = {"tasima_tamam", "tasima_hata", "tasima_atlandi"}
UNDO_FINAL = {"geri_tamam", "geri_cakisma", "geri_reddedildi", "geri_hata"}


def item_states(records: list[dict]) -> dict[str, dict]:
    """Her öğe için günlükten türetilen son durum."""
    st: dict[str, dict] = {}
    for r in records:
        t, i = r.get("tur"), r.get("id")
        if not i:
            continue
        cur = st.setdefault(i, {"durum": "bekliyor"})
        if t == "tasima_niyeti":
            cur.update(durum="tasiniyor", kayit=r)
        elif t == "tasima_tamam":
            cur.update(durum="tasindi", hedef=r.get("hedef"), kayit={**cur.get("kayit", {}), **r})
        elif t in ("tasima_hata", "tasima_atlandi"):
            cur.update(durum="atlandi", neden=r.get("neden"))
        elif t == "geri_niyet":
            cur.update(durum="geri_aliniyor")
        elif t == "geri_tamam":
            cur.update(durum="geri_alindi")
        elif t in ("geri_cakisma", "geri_reddedildi", "geri_hata"):
            cur.update(durum="tasindi", geri_neden=r.get("neden"))
    return st


# --------------------------------------------------------------------------- güvenli taşıma

def safe_move(src: str, dst: str):
    """Yalnızca aynı birimde yeniden adlandırma; hedef varsa asla üzerine yazmaz."""
    try:
        if IS_WIN:
            os.rename(src, dst)  # MoveFileExW(0): üzerine yazmaz, sürücüler arası kopyalamaz
            return
        libc = ctypes.CDLL(None, use_errno=True)
        bsrc, bdst = os.fsencode(src), os.fsencode(dst)
        if IS_MAC and hasattr(libc, "renamex_np"):
            fn = libc.renamex_np
            fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
            if fn(bsrc, bdst, 0x4) != 0:  # RENAME_EXCL
                e = ctypes.get_errno()
                raise OSError(e, os.strerror(e), dst)
            return
        fn = getattr(libc, "renameat2", None)
        if fn is not None:
            fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
            if fn(-100, bsrc, -100, bdst, 1) == 0:  # AT_FDCWD, RENAME_NOREPLACE
                return
            e = ctypes.get_errno()
            if e not in (errno.EINVAL, errno.ENOSYS, getattr(errno, "ENOTSUP", 95)):
                raise OSError(e, os.strerror(e), dst)
        if os.path.lexists(dst):
            raise FileExistsError(errno.EEXIST, "hedef zaten var", dst)
        os.rename(src, dst)
    except OSError as ex:
        if ex.errno == errno.EXDEV or getattr(ex, "winerror", None) == 17:
            raise FarkliSurucu(errno.EXDEV, "farklı sürücü/birim; güvenli taşıma mümkün değil", dst)
        raise


def matches(path: str, rec: dict) -> tuple[bool, str]:
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return False, "dosya beklenen yerde yok"
    except OSError as ex:
        return False, f"erişilemiyor ({ex.strerror})"
    if is_link_like(st) or not stat.S_ISREG(st.st_mode):
        return False, "artık normal dosya değil"
    if is_cloud_only(st):
        return False, "yalnızca bulutta"
    if st.st_size != rec["boyut"] or st.st_mtime_ns != rec["mtime_ns"]:
        return False, "boyutu veya değiştirilme zamanı değişmiş"
    ino = rec.get("kimlik", [0, 0])[1]
    if ino and st.st_ino and ino != st.st_ino:
        return False, "farklı dosya (kimlik uyuşmuyor)"
    try:
        if fingerprint(path, st.st_size) != rec["iz"]:
            return False, "içerik izi uyuşmuyor"
    except OSError as ex:
        return False, f"okunamadı ({ex.strerror})"
    return True, ""


def _ensure_dir(path: Path, parent: Path) -> Path:
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        os.mkdir(path)
        st = os.lstat(path)
    if is_link_like(st) or not stat.S_ISDIR(st.st_mode):
        raise DuzenHatasi(f"Hedef '{path.name}' güvenli bir klasör değil.")
    if not resolves_inside(path, parent):
        raise DuzenHatasi(f"Hedef '{path.name}' izin verilen konumun dışında.")
    return path


class Control:
    """Pano ile çalıştırıcı arasındaki duraklat/durdur bayrakları."""

    def __init__(self):
        import threading
        self.paused = threading.Event()
        self.stopped = threading.Event()
        self.idle = threading.Event()  # duraklatma gerçekten devreye girdiğinde set edilir


def execute_plan(op_id: str, pace: float = PACE_SECONDS, control: Control | None = None,
                 lock: GlobalLock | None = None) -> dict:
    """Onaylı planı uygular. Dönüş: özet. Kilit verilmezse kendisi alır."""
    control = control or Control()
    plan, digest = load_plan(op_id)
    if not is_approved(op_id, digest):
        raise DuzenHatasi("Plan onaylanmamış veya onaydan sonra değişmiş; taşıma yapılmadı.")
    own = lock is None
    lock = lock or GlobalLock("duzenleme", op_id).acquire()
    try:
        reconcile_all()
        journal = Journal(op_id)
        done = item_states(journal.records())
        desktop = plan["masaustu"]
        validate_desktop(desktop, plan["masaustu_kaynagi"])
        root = check_root(desktop)  # klasör ilk taşımada oluşturulur
        items = plan["ogeler"]
        n = max(len(items), 1)
        t0 = time.monotonic()
        paused_total = 0.0
        result = "tamamlandi"
        for idx, it in enumerate(items):
            if it["id"] in done and done[it["id"]]["durum"] != "bekliyor":
                continue
            target = t0 + idx * pace / n
            while True:
                if control.stopped.is_set():
                    result = "durduruldu"
                    break
                if control.paused.is_set():
                    control.idle.set()
                    p0 = time.monotonic()
                    while control.paused.is_set() and not control.stopped.is_set():
                        time.sleep(0.05)
                    paused_total += time.monotonic() - p0
                    control.idle.clear()
                    continue
                now = time.monotonic()
                if now >= target + paused_total:
                    break
                time.sleep(min(0.05, target + paused_total - now))
            if result == "durduruldu":
                break
            _move_one(it, desktop, root, journal)
        return {"islem": op_id, "sonuc": result, **summarize(op_id)}
    finally:
        if own:
            lock.release()


def _move_one(it: dict, desktop: str, root: Path, journal: Journal):
    src = it["kaynak"]
    base = {"id": it["id"], "kaynak": src, "kategori": it["kategori"]}
    if not real_same(os.path.dirname(src), desktop):
        journal.append({"tur": "tasima_atlandi", **base, "neden": "kaynak masaüstü kökünde değil"})
        return
    try:
        st = os.lstat(src)
    except FileNotFoundError:
        journal.append({"tur": "tasima_atlandi", **base, "neden": "kaynak artık yok"})
        return
    if is_hidden(os.path.basename(src), st):
        journal.append({"tur": "tasima_atlandi", **base, "neden": "gizli/sistem dosyası oldu"})
        return
    ok, why = matches(src, it)
    if not ok:
        journal.append({"tur": "tasima_atlandi", **base, "neden": f"plandan sonra değişti: {why}; yeniden incelenmeli"})
        return
    if office_lock_present(os.path.basename(src), _existing_names(Path(desktop))):
        journal.append({"tur": "tasima_atlandi", **base, "neden": "şu an Office'te açık (~$ kilit dosyası var)"})
        return
    try:
        _ensure_dir(root, Path(desktop))
        catdir = _ensure_dir(root / CATEGORIES[it["kategori"]][0], root)
    except (DuzenHatasi, OSError) as ex:
        journal.append({"tur": "tasima_hata", **base, "neden": str(ex)})
        return
    name = unique_name(it["hedef_ad"], _existing_names(catdir))
    dst = str(catdir / name)
    if not real_same(os.path.dirname(dst), catdir):
        journal.append({"tur": "tasima_hata", **base, "neden": "hedef izin verilen klasörün dışında"})
        return
    rec = {"tur": "tasima_niyeti", **base, "hedef": dst, "boyut": it["boyut"], "mtime_ns": it["mtime_ns"],
           "kimlik": it["kimlik"], "iz": it["iz"], "kopya": it["kategori"] == "13"}
    journal.append(rec)
    try:
        safe_move(src, dst)
    except FarkliSurucu as ex:
        journal.append({"tur": "tasima_hata", **base, "neden": ex.strerror})
        return
    except OSError as ex:
        reason = "kilitli/erişilemiyor" if isinstance(ex, PermissionError) else (ex.strerror or str(ex))
        journal.append({"tur": "tasima_hata", **base, "neden": reason})
        return
    ok, why = matches(dst, it)
    if ok and not os.path.lexists(src):
        journal.append({"tur": "tasima_tamam", **base, "hedef": dst, "boyut": it["boyut"],
                        "kopya": it["kategori"] == "13"})
    else:
        journal.append({"tur": "tasima_hata", **base, "hedef": dst,
                        "neden": f"taşıma sonrası doğrulanamadı: {why or 'kaynak hâlâ duruyor'}"})


# --------------------------------------------------------------------------- uzlaştırma

def _all_ops() -> list[str]:
    d = state_dir() / "islemler"
    return sorted(p.name for p in d.iterdir() if p.is_dir() and (p / "gunluk.jsonl").is_file())


def reconcile_all() -> list[dict]:
    """Çökme/kapanma sonrası niyeti olup sonucu olmayan kayıtları gerçek dosya durumuyla eşler."""
    fixed = []
    for op in _all_ops():
        j = Journal(op)
        open_moves: dict[str, dict] = {}
        open_undos: dict[str, dict] = {}
        moves_by_id: dict[str, dict] = {}
        for r in j.records():
            t, i = r.get("tur"), r.get("id")
            if t == "tasima_niyeti":
                open_moves[i] = r
                moves_by_id[i] = r
            elif t in MOVE_FINAL:
                open_moves.pop(i, None)
            elif t == "geri_niyet":
                open_undos[i] = r
            elif t in UNDO_FINAL:
                open_undos.pop(i, None)
        for i, r in open_moves.items():
            src, dst = r["kaynak"], r["hedef"]
            at_dst, _ = matches(dst, r)
            at_src, _ = matches(src, r)
            if at_dst and not os.path.lexists(src):
                rec = {"tur": "tasima_tamam", "id": i, "kaynak": src, "hedef": dst, "boyut": r["boyut"],
                       "kategori": r.get("kategori"), "kopya": r.get("kopya", False), "uzlastirma": True}
            elif at_src and not os.path.lexists(dst):
                rec = {"tur": "tasima_hata", "id": i, "kaynak": src, "neden": "yarıda kaldı; dosya yerinde",
                       "uzlastirma": True}
            else:
                rec = {"tur": "tasima_hata", "id": i, "kaynak": src, "hedef": dst,
                       "neden": "yarıda kaldı; dosya konumu belirsiz, elle kontrol edin", "uzlastirma": True}
            j.append(rec)
            fixed.append({"islem": op, **rec})
        for i, r in open_undos.items():
            cur, orig = r["kaynak"], r["hedef"]
            mv = moves_by_id.get(i, r)
            at_orig, _ = matches(orig, mv)
            at_cur, _ = matches(cur, mv)
            if at_orig and not os.path.lexists(cur):
                rec = {"tur": "geri_tamam", "id": i, "kaynak": cur, "hedef": orig, "uzlastirma": True}
            elif at_cur:
                rec = {"tur": "geri_hata", "id": i, "neden": "geri alma yarıda kaldı; dosya taşınmış konumda",
                       "uzlastirma": True}
            else:
                rec = {"tur": "geri_hata", "id": i, "neden": "geri alma yarıda kaldı; konum belirsiz",
                       "uzlastirma": True}
            j.append(rec)
            fixed.append({"islem": op, **rec})
    return fixed


# --------------------------------------------------------------------------- geri alma

def undoable(op_id: str) -> list[dict]:
    recs = Journal(op_id).records()
    intents = {r["id"]: r for r in recs if r.get("tur") == "tasima_niyeti"}
    out = []
    for i, s in item_states(recs).items():
        if s["durum"] == "tasindi" and i in intents:
            r = dict(intents[i])
            r["hedef"] = s.get("hedef") or r["hedef"]
            out.append(r)
    return sorted(out, key=lambda r: r["id"], reverse=True)


def last_undoable_op() -> str | None:
    for op in reversed(_all_ops()):
        if undoable(op):
            return op
    return None


def undo(op_id: str | None = None, last: bool = False, lock: GlobalLock | None = None) -> dict:
    own = lock is None
    lock = lock or GlobalLock("geri_alma", op_id or "son").acquire()
    try:
        reconcile_all()
        if last or not op_id:
            op_id = last_undoable_op()
            if not op_id:
                return {"islem": None, "geri_alinan": 0, "cakisma": [], "reddedilen": [], "hata": [],
                        "mesaj": "Geri alınacak işlem yok."}
        else:
            plan_path(op_id)  # biçim denetimi
        j = Journal(op_id)
        report = {"islem": op_id, "geri_alinan": 0, "cakisma": [], "reddedilen": [], "hata": []}
        for r in undoable(op_id):
            cur, orig = r["hedef"], r["kaynak"]
            base = {"id": r["id"], "kaynak": cur, "hedef": orig}
            ok, why = matches(cur, r)
            if not ok:
                j.append({"tur": "geri_reddedildi", **base, "neden": why})
                report["reddedilen"].append({"id": r["id"], "neden": why})
                continue
            if os.path.lexists(orig):
                why = "eski konum dolu; dosya mevcut konumunda bırakıldı"
                j.append({"tur": "geri_cakisma", **base, "neden": why})
                report["cakisma"].append({"id": r["id"], "ad": os.path.basename(orig), "neden": why})
                continue
            if not os.path.isdir(os.path.dirname(orig)):
                why = "eski klasör yok"
                j.append({"tur": "geri_reddedildi", **base, "neden": why})
                report["reddedilen"].append({"id": r["id"], "neden": why})
                continue
            j.append({"tur": "geri_niyet", **base})
            try:
                safe_move(cur, orig)
            except OSError as ex:
                why = ex.strerror or str(ex)
                j.append({"tur": "geri_hata", **base, "neden": why})
                report["hata"].append({"id": r["id"], "neden": why})
                continue
            ok, why = matches(orig, r)
            if ok and not os.path.lexists(cur):
                j.append({"tur": "geri_tamam", **base})
                report["geri_alinan"] += 1
            else:
                j.append({"tur": "geri_hata", **base, "neden": f"doğrulanamadı: {why}"})
                report["hata"].append({"id": r["id"], "neden": why})
        return report
    finally:
        if own:
            lock.release()


# --------------------------------------------------------------------------- özet

def summarize(op_id: str) -> dict:
    states = item_states(Journal(op_id).records())
    moved = [s for s in states.values() if s["durum"] == "tasindi"]
    kayit = [s.get("kayit", {}) for s in moved]
    return {
        "tasinan": len(moved),
        "kopyalara": sum(1 for k in kayit if k.get("kopya")),
        "boyut": sum(int(k.get("boyut", 0)) for k in kayit),
        "klasor": len({k.get("kategori") for k in kayit if k.get("kategori")}),
        "atlanan": sum(1 for s in states.values() if s["durum"] == "atlandi"),
        "geri_alinan": sum(1 for s in states.values() if s["durum"] == "geri_alindi"),
    }


def list_ops() -> list[dict]:
    out = []
    for pp in sorted((state_dir() / "planlar").glob("*.json")):
        if pp.name.endswith(".onay.json"):
            continue
        op = pp.stem
        try:
            plan, digest = load_plan(op)
        except (DuzenHatasi, ValueError):
            continue
        states = item_states(Journal(op).records())
        kalan = sum(1 for it in plan["ogeler"] if states.get(it["id"], {}).get("durum", "bekliyor") == "bekliyor")
        out.append({"islem": op, "dosya": len(plan["ogeler"]), "onayli": is_approved(op, digest),
                    "kalan": kalan, "yarim": bool(states) and kalan > 0, **summarize(op)})
    return out
