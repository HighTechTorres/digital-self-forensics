"""Extractor contracts that must hold on any OS: dry-run writes nothing; bad source exits 3."""
import os, sys
import pytest
from conftest import run

@pytest.mark.parametrize("script", ["linux_extract.py", "macos_extract.py"])
def test_dry_run_writes_nothing(script, tmp_path):
    src = tmp_path / "ghost-home"; src.mkdir()
    out = tmp_path / "out"
    p = run(script, out, "--source", src, "--dry-run", check=False)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "DRY-RUN" in p.stdout
    assert not out.exists() or not any(out.iterdir())

@pytest.mark.parametrize("script", ["linux_extract.py", "macos_extract.py", "windows_extract.py"])
def test_missing_source_exits_3(script, tmp_path):
    p = run(script, tmp_path / "out", "--source", tmp_path / "does-not-exist", check=False)
    assert p.returncode == 3, p.stdout + p.stderr

@pytest.mark.parametrize("script", ["macos_extract.py", "windows_extract.py"])
def test_personal_layer_needs_explicit_flag(script, tmp_path):
    src = tmp_path / "ghost-home"; src.mkdir()
    p = run(script, tmp_path / "out", "--source", src, "--layers", "notes", "--dry-run", check=False)
    assert "ENABLED" not in p.stdout                       # --layers notes must not bypass consent

@pytest.mark.parametrize("script,flag", [("macos_extract.py", "--include-personal"),
                                         ("windows_extract.py", "--include-personal"),
                                         ("photo_exif.py", "--include-location")])
def test_sensitive_write_refused_under_sync_root(script, flag, tmp_path):
    src = tmp_path / "ghost-home"; src.mkdir()
    out = tmp_path / "dropbox" / "audit"                    # lowercase: the pre-v3.8 bypass
    p = run(script, out, "--source", src, flag, check=False)
    assert p.returncode == 2, p.stdout + p.stderr
    assert "REFUSING" in p.stdout
