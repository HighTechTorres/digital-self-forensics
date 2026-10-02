"""The cloud-sync guard is the last line between a personal layer and someone's synced storage."""
import os
import pytest
from _common import under_sync_root

SYNCED = [
    "/Users/me/Dropbox/audit",
    "/Users/me/dropbox/audit",                                   # case-insensitive APFS
    "/Users/me/Library/Mobile Documents/com~apple~CloudDocs/out",
    "/Users/me/Library/CloudStorage/OneDrive-Personal/out",      # modern macOS layout
    "/Users/me/Library/CloudStorage/GoogleDrive-me@example.com/My Drive/out",
    r"C:\Users\me\OneDrive\out",
    r"C:\Users\me\onedrive\out",                                 # case-insensitive NTFS
    r"C:\Users\me\OneDrive - Contoso\out",                       # enterprise prefix
    r"G:\My Drive\out",
    "/home/me/Nextcloud/out",
    "/home/me/pCloudDrive/out",
    "/Users/me/Box/out",
]
LOCAL = [
    "/Users/me/Downloads/audit",
    "/Users/me/OneDriveBackup/out",                              # look-alike, not a sync root
    "/Users/me/Boxes/out",
    "/home/me/projects/dropbox-clone/out",
    r"C:\Users\me\Documents\out",
]

@pytest.mark.parametrize("path", SYNCED)
def test_synced_paths_are_refused(path):
    assert under_sync_root(path), path

@pytest.mark.parametrize("path", LOCAL)
def test_local_paths_are_allowed(path):
    assert under_sync_root(path) is None, path

@pytest.mark.parametrize("script", ["macos_extract.py", "windows_extract.py", "photo_exif.py",
                                    "build_handoff_pack.py"])
def test_every_writer_uses_the_shared_guard(script):
    from conftest import SCRIPTS
    src = open(os.path.join(SCRIPTS, script), encoding="utf-8").read()
    assert "from _common import under_sync_root" in src
    assert "def under_sync_root" not in src, "local copy would drift from the hardened guard"
