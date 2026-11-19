---
name: desktop-organizer
description: Desktop Organizer by Lionstone (Masaüstü Düzenleyici). Tidies the root of the user's real Windows or macOS desktop into one "Masaüstü Düzeni" folder with 17 numbered categories, only after the user approves a written plan, with a local live dashboard and journaled undo. Use when the user asks to clean up, organize or tidy their desktop ("masaüstümü düzenle", "masaüstünü toparla", "organize my desktop"), or to undo a previous desktop clean-up.
---

# Desktop Organizer by Lionstone

Reply in the user's language (the tool's own output is Turkish). Keep the flow moving; the
only approval you must wait for is the explicit plan approval in step 4.

`SKILL_DIR` below is the folder that contains this file. Run the tool with Python 3.9+:

```
python "<SKILL_DIR>/scripts/masaustu.py" <command>
```

(On Windows `py -3` also works; on macOS/Linux use `python3`.) The core uses only the Python
standard library. **Never install anything automatically.** If Python is missing or too old,
tell the user what to install and stop.

## Hard rules

- Creating or installing this skill is **not** permission to move files.
- Never move, rename, delete or overwrite anything on the real desktop yourself (no `mv`,
  `Move-Item`, Finder/Explorer automation). Only the tool moves files, and only after the user
  presses **Başlat** in the dashboard for an approved plan.
- Never pass `--masaustu/--desktop` for the real desktop unless the user gave you that path.
  If detection reports the desktop is ambiguous (exit code 3), show the reason and ask the user.
- Never approve on the user's behalf. Approval is valid only when the user writes
  **`Planı onaylıyorum`** (or clearly says they approve *this* plan) after seeing it, and only for
  the operation id you showed. Files added later are never included.
- Do not send file names, paths or contents to any external service.
- Outlook data files (`.pst`, `.ost`, `.nst`) are never planned, moved or touched; the tool lists
  them under *Korunan uygulama veri dosyaları*. Never work around this.

## Workflow

1. **Check the environment** — `masaustu.py ortam`. Report OS, Python and the detected desktop
   path (OneDrive-redirected desktops on Windows are handled; the Public desktop is never used).
2. **Plan** — `masaustu.py plan`. It scans only the desktop root (no sub-folders), skips hidden /
   system files, symlinks, shortcuts (`.lnk .url .webloc .desktop`), temp/partial downloads,
   files changed in the last 15 minutes, unstable, locked or cloud-only files, and HTML pages
   that have a companion `_files` folder. It saves the plan with a unique operation id.
3. **Show the plan** — print the tool's Markdown output to the user: real desktop path, the
   summary table (category, file count, total size, target folder), the detailed plan (source
   name, target path, reason), duplicate groups (and which file stays in its normal category),
   name collisions, and skipped items with reasons. Do not shorten the skipped list.
4. **Wait for approval.** You may open the dashboard as a preview before approval
   (`masaustu.py pano <ID>` — the **Başlat** button stays disabled). When the user writes
   `Planı onaylıyorum`, run:
   `masaustu.py onayla <ID> --ifade "Planı onaylıyorum"`.
   The dashboard enables **Başlat** by itself. Tell the user to press it.
5. **Dashboard** — `masaustu.py pano <ID>` runs a local server on `127.0.0.1` (random free port,
   per-session key, Host/Origin checks) and opens the browser. Run it as a background/long-running
   command; it ends when the user presses **Panoyu Kapat**. Controls: Başlat, Duraklat/Devam Et,
   Durdur (takes effect after the current file; already moved files stay moved), Son İşlemi Geri
   Al, Panoyu Kapat. If no browser opens, give the user the printed URL.
6. **Report** — after the dashboard closes, run `masaustu.py durum` and summarise: moved,
   copies moved to `13_Kopyalar` (this saves no disk space), skipped and why.

The dashboard has a **TR / EN** switch (top right); it starts in the browser's language.

## Resuming an interrupted run

A run can be cut short: the app crashes, the computer sleeps, the dashboard is closed, or your
session ends because of a usage limit. When you (or a new session) come back:

1. Run `masaustu.py durum`. An approved run with files left is printed as
   `YARIM KALAN İŞLEM: <ID> — N dosya bekliyor`.
2. Tell the user, then open `masaustu.py pano <ID>`. The button reads **Kaldığı Yerden Devam Et**
   (EN: *Resume where it stopped*). No new approval is needed — it is the same approved plan — but
   the user still presses the button. Already-moved files are skipped; each remaining file is
   re-checked first, and files that changed are set aside.
3. Do **not** create a new plan for the same desktop while an approved run is unfinished, unless
   the user asks for a fresh plan.

## Undo

- Last operation: `masaustu.py geri-al --son`
- A specific one: `masaustu.py geri-al <ID>`

Undo verifies each file (size, modification time, file id, content fingerprint). If the original
spot is occupied, or the file changed or moved since, it is left where it is and reported. Undo
never deletes files or folders. Only one organise/undo can run at a time.

## Recovery

Every move is journaled (intent → result) in the user's app-data folder, not on the desktop.
`masaustu.py uzlastir` (also run automatically) reconciles half-finished records after a crash.

## Target layout

```
Masaüstü Düzeni/
  01_Görseller  02_YZ Görselleri  03_Ekran Görüntüleri  04_Videolar  05_Ses
  06_Belgeler   07_Tablolar       08_Sunumlar           09_Web Sayfaları
  10_Arşivler   11_Kurulum        12_Diğer              13_Kopyalar
  14_AI Dosyaları  15_EPS Dosyaları  16_CDR Dosyaları  17_PSD Dosyaları
  (Illustrator, EPS, CorelDRAW, Photoshop)
```

Only the folders that are needed are created. AI images are only separated when generator
metadata (e.g. Stable Diffusion `parameters`, C2PA/IPTC `trainedAlgorithmicMedia`) or an explicit
file-name marker exists; never by how an image looks. Unclear images go to `01_Görseller`.
