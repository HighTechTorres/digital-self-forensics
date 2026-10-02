import os, sys, shutil, subprocess
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "extract")
CANARY = "CANARY-PRIVATE"   # appears only in the fixture's synthetic notes export

sys.path.insert(0, SCRIPTS)

def run(script, *args, check=True):
    """Run a skill script the way the skill does (python3 scripts/<name>.py ...)."""
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise AssertionError(f"{script} exited {p.returncode}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    return p

@pytest.fixture
def extract(tmp_path):
    """A fresh, writable copy of the synthetic extract set (includes a fake notes export)."""
    d = tmp_path / "extract"
    shutil.copytree(FIXTURE, d)
    return d

def all_text(path):
    """Concatenated text of every file under PATH except the notes export itself."""
    chunks = []
    for dp, _, fns in os.walk(path):
        for f in fns:
            if f in ("notes-export.md", "Apple-Notes-Full-Export.md"): continue
            with open(os.path.join(dp, f), encoding="utf-8", errors="ignore") as fh:
                chunks.append(fh.read())
    return "\n".join(chunks)
