#!/usr/bin/env python3
"""
build_skill.py — rebuild digital-self-forensics.skill (the installable zip) from the repo.

Deterministic: sorted entries, fixed timestamps and permissions, so the same tree always produces
byte-identical output and CI can prove the committed bundle matches the source.

Usage:
    python3 scripts/build_skill.py           # (re)write digital-self-forensics.skill
    python3 scripts/build_skill.py --check   # exit 1 if the committed bundle is stale
    python3 scripts/build_skill.py --list    # print what would be packed

Only what the skill needs at runtime ships: SKILL.md, scripts/, references/, assets/, docs/, and the
top-level README/LICENSE/SECURITY/CHANGELOG. Tests, CI, evals, and examples stay in the repo only.
"""
import os, sys, io, zipfile, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "digital-self-forensics"
BUNDLE = os.path.join(ROOT, f"{NAME}.skill")
TOP_FILES = ["SKILL.md", "README.md", "LICENSE", "SECURITY.md", "CHANGELOG.md"]
TREES = ["scripts", "references", "assets", "docs"]
SKIP_DIRS = {"__pycache__", ".pytest_cache"}
SKIP_FILES = {"scripts/build_skill.py"}   # dev tooling, not needed at runtime
STAMP = (2026, 1, 1, 0, 0, 0)

def files():
    out = [f for f in TOP_FILES if os.path.isfile(os.path.join(ROOT, f))]
    for t in TREES:
        for dp, dns, fns in os.walk(os.path.join(ROOT, t)):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            out += [os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/")
                    for f in fns if not f.endswith((".pyc", ".pyo")) and f != ".DS_Store"]
    return sorted(p for p in out if p not in SKIP_FILES)

def build():
    rel = files()
    dirs = sorted({"/".join(p.split("/")[:i]) for p in rel for i in range(1, p.count("/") + 1)})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        def put(arc, data, mode):
            zi = zipfile.ZipInfo(arc, STAMP); zi.external_attr = mode << 16
            zi.compress_type = zipfile.ZIP_STORED if arc.endswith("/") else zipfile.ZIP_DEFLATED
            z.writestr(zi, data)
        put(f"{NAME}/", b"", 0o40755)
        for d in dirs: put(f"{NAME}/{d}/", b"", 0o40755)
        for p in rel:
            with open(os.path.join(ROOT, p), "rb") as f: data = f.read()
            if not p.startswith("assets/vendor/"):     # normalize text line endings (Windows checkouts)
                data = data.replace(b"\r\n", b"\n")
            mode = 0o100755 if p.endswith((".py", ".sh")) else 0o100644
            put(f"{NAME}/{p}", data, mode)
    return buf.getvalue(), rel

def manifest(blob):
    """Entry names, modes, and uncompressed bytes — compared instead of raw zip bytes, because
    deflate output can legitimately differ between zlib builds (macOS vs Windows vs Linux)."""
    if not blob: return None
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            return [(i.filename, i.external_attr >> 16, z.read(i)) for i in z.infolist()]
    except zipfile.BadZipFile:
        return None

def main():
    ap = argparse.ArgumentParser(description="Rebuild the .skill bundle deterministically.")
    ap.add_argument("--check", action="store_true", help="Fail if the committed bundle is out of date")
    ap.add_argument("--list", action="store_true", help="List bundled files and exit")
    a = ap.parse_args()
    data, rel = build()
    if a.list:
        print("\n".join(rel)); return
    if a.check:
        if manifest(open(BUNDLE, "rb").read() if os.path.exists(BUNDLE) else None) != manifest(data):
            print(f"STALE: {os.path.basename(BUNDLE)} does not match the source tree. "
                  "Run `python3 scripts/build_skill.py` and commit the result."); sys.exit(1)
        print(f"ok: {os.path.basename(BUNDLE)} is up to date ({len(rel)} files)"); return
    with open(BUNDLE, "wb") as f: f.write(data)
    print(f"wrote {os.path.basename(BUNDLE)} ({len(rel)} files, {len(data)/1024:.1f} KB)")

if __name__ == "__main__":
    main()
