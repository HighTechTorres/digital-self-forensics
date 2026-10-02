"""
_common.py — small shared helpers for the digital-self-forensics scripts (stdlib only).

The one that matters most is under_sync_root(): every script that can write a sensitive layer
(Notes / Sticky Notes, photo GPS, the Handoff Pack's private/ section) must refuse to write it
under a cloud-sync folder. Keeping a single implementation here means a fix lands everywhere.

Scripts import it as `from _common import ...` — running `python3 scripts/<name>.py` puts the
scripts/ directory on sys.path, so no packaging is needed.
"""
import os, csv, json, re

SYNC_ROOTS = ["Dropbox", "Mobile Documents", "iCloud", "iCloudDrive", "iCloud Drive", "OneDrive",
              "Google Drive", "GoogleDrive", "My Drive", "pCloud", "pCloudDrive", "Box", "Box Sync",
              "Nextcloud", "ownCloud", "Creative Cloud Files", "MEGA", "MEGAsync",
              "CloudStorage"]  # macOS ~/Library/CloudStorage/<Provider-Account> — everything under it syncs

def under_sync_root(path):
    """Return the matching path segment if PATH is inside a cloud-sync folder, else None.

    Matches whole path segments, case-insensitively, across both / and \\ separators, so
    `~/dropbox/out` (case-insensitive APFS/NTFS) and `C:\\Users\\me\\onedrive\\out` are caught.
    Provider-prefixed enterprise folders (`OneDrive - Contoso`) match; look-alikes such as
    `OneDriveBackup` or `Boxes` do not.
    """
    parts = [p.lower() for p in os.path.abspath(path).replace("\\", "/").split("/") if p]
    roots = [s.lower() for s in SYNC_ROOTS]
    for seg in parts:
        for r in roots:
            if seg == r or seg.startswith(r + " -"):
                return seg
    return None

def read_csv(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8", errors="ignore") as f:
        return list(csv.DictReader(f))

def read_json(path):
    if not os.path.exists(path): return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def year_of(s):
    """First plausible 4-digit year in S (1995–2035), else None — clamps out epoch-zero junk."""
    m = re.search(r'(19|20)\d\d', s or "")
    if not m: return None
    y = int(m.group(0))
    return y if 1995 <= y <= 2035 else None
