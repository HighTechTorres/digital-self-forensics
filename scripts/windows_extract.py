#!/usr/bin/env python3
"""
windows_extract.py — Windows deep-artifact extractor for self-forensics.

Native counterpart to macos_extract.py. Same contract, same OUTPUT FILE SCHEMA, so the
OS-agnostic downstream tools (correlate.py, build_handoff_pack.py, story_seeds.py, render_docs.py)
work on the results unchanged. Pure Python + the stdlib `winreg` (no external deps).

Local-only. Read-only on sources (SQLite DBs are copied before querying). The inner/personal
layer (Sticky Notes bodies) is OFF by default and only enabled with --include-personal.

Run in PowerShell or cmd. Registry-based layers (behavior/installs/autostart Run keys) read the
LIVE machine only and are skipped under --source. Some advanced artifacts ($MFT, Prefetch) need an
elevated prompt and are out of scope here — see references/windows.md.

Usage:
    python windows_extract.py OUTDIR [options]

Options (mirror macos_extract.py):
    --source PATH        Artifact root (default: %USERPROFILE%). Use for an old drive / migrated tree.
    --include-personal   Enable the inner layer (Sticky Notes bodies). Default: OFF.
    --layers a,b,c       Subset of: behavior,provenance,accounts,dev,installs,shell,recent,autostart,notes
    --dry-run            Print what WOULD be extracted; write nothing.
    --run-id ID          Name the run (writes to OUTDIR/run-ID) for longitudinal diffing.

Exit codes: 0 ok · 2 bad args · 3 source not found.

Timestamp notes: UserAssist + Run keys use Windows FILETIME (100ns since 1601). Chrome History =
microseconds since 1601. Registry InstallDate is a YYYYMMDD string.
"""
import os, sys, argparse, sqlite3, shutil, tempfile, re, datetime, glob, collections, subprocess, struct, codecs

ALL_LAYERS = ["behavior", "provenance", "accounts", "dev", "installs", "shell", "recent", "autostart"]
PERSONAL_LAYERS = ["notes"]
SYNC_ROOTS = ["Dropbox", "OneDrive", "Google Drive", "GoogleDrive", "pCloud", "Box"]

def env(name, default=""):
    return os.environ.get(name, default)

def under_sync_root(path):
    ap = os.path.abspath(path)
    return next((s for s in SYNC_ROOTS if (os.sep + s) in ap or ap.endswith(s)), None)

def copydb(path):
    if not os.path.exists(path): return None
    tmp = tempfile.mktemp(suffix=".db"); shutil.copy2(path, tmp)
    for ext in ("-wal", "-shm"):
        if os.path.exists(path + ext):
            try: shutil.copy2(path + ext, tmp + ext)
            except Exception: pass
    return tmp

def qy(db, sql, params=()):
    con = sqlite3.connect(db)
    con.text_factory = lambda b: b.decode("utf-8", "ignore") if isinstance(b, bytes) else b
    try: return con.execute(sql, params).fetchall()
    except Exception: return []
    finally: con.close()

def w(outdir, name, text):
    p = os.path.join(outdir, name); open(p, "w", encoding="utf-8").write(text); return p

def filetime(v):
    try: return datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=int(v) / 10)
    except Exception: return None

def chrome_time(v):
    try: return datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=int(v))
    except Exception: return None

def is_live(R):
    return os.path.abspath(R) == os.path.abspath(env("USERPROFILE", os.path.expanduser("~")))

# ---------------- layers ----------------
def behavior(R, outdir, dry):
    """UserAssist = the knowledgeC analog: which apps you run, how often, and focus time."""
    if not is_live(R): print("  behavior: skipped (UserAssist is live-machine only)"); return
    try: import winreg
    except Exception: print("  behavior: winreg unavailable (not Windows)"); return
    out = ["app,start_epoch,start,minutes"]; by_app = collections.Counter(); rows = 0
    base = r"Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"
    try:
        ua = winreg.OpenKey(winreg.HKEY_CURRENT_USER, base)
    except Exception as e:
        print(f"  behavior: UserAssist not readable ({e})"); return
    i = 0
    while True:
        try: guid = winreg.EnumKey(ua, i); i += 1
        except OSError: break
        try: count = winreg.OpenKey(ua, guid + r"\Count")
        except Exception: continue
        j = 0
        while True:
            try: name, data, _ = winreg.EnumValue(count, j); j += 1
            except OSError: break
            decoded = codecs.decode(name, "rot_13")
            if not (decoded.lower().endswith(".exe") or "\\" in decoded): continue
            app = os.path.basename(decoded)
            run_count = focus_ms = 0; last = None
            try:
                if len(data) >= 16: run_count = struct.unpack_from("<I", data, 4)[0]
                if len(data) >= 16: focus_ms = struct.unpack_from("<I", data, 12)[0]
                if len(data) >= 68: last = filetime(struct.unpack_from("<Q", data, 60)[0])
            except Exception: pass
            mins = round(focus_ms / 60000.0, 1) if 0 < focus_ms < 10**9 else 0
            by_app[app] += mins or run_count
            ep = int(last.timestamp()) if last else ""
            out.append(f'{app},{ep},{last.isoformat() if last else ""},{mins}')
            rows += 1
    print("  behavior (top by focus/runs): " + ", ".join(f"{a} {round(m,1)}" for a, m in by_app.most_common(6)))
    if not dry and rows: w(outdir, "app-usage.csv", "\n".join(out))

def _chrome_user_data(R):
    la = env("LOCALAPPDATA") or os.path.join(R, "AppData", "Local")
    if not is_live(R): la = os.path.join(R, "AppData", "Local")
    return [os.path.join(la, "Google", "Chrome", "User Data"),
            os.path.join(la, "Microsoft", "Edge", "User Data"),
            os.path.join(la, "BraveSoftware", "Brave-Browser", "User Data")]

def _chrome_profiles(R):
    for ud in _chrome_user_data(R):
        for prof in glob.glob(os.path.join(ud, "*", "")):
            yield prof.rstrip("\\/")

def provenance(R, outdir, dry):
    """NTFS Zone.Identifier ADS records where each download came from."""
    out = ["downloaded,app,file_url,page_url"]; by_year = collections.Counter(); n = 0
    dl = os.path.join(R, "Downloads")
    if os.path.isdir(dl):
        for f in glob.glob(os.path.join(dl, "*")):
            if os.path.isdir(f): continue
            try:
                with open(f + ":Zone.Identifier", "r", errors="ignore") as zf:
                    z = zf.read()
            except Exception: continue
            host = re.search(r'HostUrl=(\S+)', z); ref = re.search(r'ReferrerUrl=(\S+)', z)
            page = (host or ref).group(1) if (host or ref) else ""
            try: d = datetime.datetime.fromtimestamp(os.path.getctime(f))
            except Exception: d = None
            out.append(f'"{d.isoformat() if d else ""}","browser","{os.path.basename(f)}","{page}"')
            if d: by_year[d.year] += 1
            n += 1
    # Chrome-family History.downloads also carries referrers
    for prof in _chrome_profiles(R):
        src = copydb(os.path.join(prof, "History"))
        if not src: continue
        for tgt, tab, start in qy(src, "select target_path, tab_url, start_time from downloads"):
            d = chrome_time(start)
            out.append(f'"{d.isoformat() if d else ""}","chrome","{tgt or ""}","{tab or ""}"')
            if d: by_year[d.year] += 1
            n += 1
        os.unlink(src)
    print(f"  provenance: {n} downloads | by year: " + " ".join(f"{y}:{by_year[y]}" for y in sorted(by_year)))
    if not dry and n: w(outdir, "download-provenance.csv", "\n".join(out))

def accounts(R, outdir, dry):
    doms = set()
    for prof in _chrome_profiles(R):
        src = copydb(os.path.join(prof, "Login Data"))
        if not src: continue
        for (realm,) in qy(src, "select signon_realm from logins"):
            m = re.sub(r'https?://', '', realm or '').split('/')[0].replace('www.', '')
            if m and not m.startswith(("android", "192.168", "10.", "127.")): doms.add(m)
        os.unlink(src)
    print(f"  accounts: {len(doms)} unique service domains (logins)")
    if not dry and doms: w(outdir, "saas-account-footprint.txt", "\n".join(sorted(doms)))

def dev(R, outdir, dry):
    repos = []
    for root, dirs, _ in os.walk(R):
        if root.count(os.sep) - R.count(os.sep) > 6:
            dirs[:] = []; continue
        if ".git" in dirs: repos.append(os.path.join(root, ".git"))
    lines = ["repo,commits,first,last,remote"]; seen = set()
    for g in repos:
        r = os.path.dirname(g); name = os.path.basename(r)
        try:
            cnt = subprocess.run(["git", "-C", r, "rev-list", "--all", "--count"], capture_output=True, text=True).stdout.strip() or "0"
            log = subprocess.run(["git", "-C", r, "log", "--all", "--format=%H %ad", "--date=format:%Y-%m-%d"], capture_output=True, text=True).stdout.splitlines()
            dates = [ln.split()[1] for ln in log if ln.split() and ln.split()[0] not in seen and not seen.add(ln.split()[0])]
            rem = subprocess.run(["git", "-C", r, "config", "--get", "remote.origin.url"], capture_output=True, text=True).stdout.strip()
            lines.append(f'{name},{cnt},{min(dates) if dates else ""},{max(dates) if dates else ""},{rem}')
        except Exception: pass
    kh = os.path.join(R, ".ssh", "known_hosts"); nhosts = sum(1 for _ in open(kh, errors="ignore")) if os.path.exists(kh) else 0
    print(f"  dev: {len(repos)} git repos | ssh known_hosts: {nhosts}")
    if not dry and len(lines) > 1: w(outdir, "git-timeline.csv", "\n".join(lines))

def installs(R, outdir, dry):
    """Installed-software adoption timeline from the registry Uninstall keys (InstallDate)."""
    if not is_live(R): print("  installs: skipped (registry is live-machine only)"); return
    try: import winreg
    except Exception: print("  installs: winreg unavailable"); return
    events = ["tool,first_seen,source"]; seen = set()
    roots = [(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")]
    for hive, path in roots:
        try: key = winreg.OpenKey(hive, path)
        except Exception: continue
        i = 0
        while True:
            try: sub = winreg.EnumKey(key, i); i += 1
            except OSError: break
            try:
                sk = winreg.OpenKey(key, sub)
                name = winreg.QueryValueEx(sk, "DisplayName")[0]
            except Exception: continue
            date = ""
            try:
                raw = str(winreg.QueryValueEx(sk, "InstallDate")[0])
                if re.match(r'^\d{8}$', raw): date = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
            except Exception: pass
            if name and name not in seen:
                seen.add(name); events.append(f"{name},{date},registry")
    print(f"  installs: {len(events)-1} installed-software entries")
    if not dry and len(events) > 1: w(outdir, "installs.csv", "\n".join(events))

def shell_history(R, outdir, dry):
    """PowerShell PSReadLine history = your terminal workflow."""
    ad = env("APPDATA") if is_live(R) else os.path.join(R, "AppData", "Roaming")
    hist = os.path.join(ad, "Microsoft", "Windows", "PowerShell", "PSReadLine", "ConsoleHost_history.txt")
    if not os.path.exists(hist): print("  shell: no PSReadLine history found"); return
    cmds = collections.Counter()
    for line in open(hist, errors="ignore"):
        tok = line.strip().split()
        if tok: cmds[tok[0]] += 1
    out = ["command,count"] + [f"{c},{n}" for c, n in cmds.most_common(60)]
    print("  shell: top tools " + ", ".join(f"{c}({n})" for c, n in cmds.most_common(6)))
    if not dry: w(outdir, "shell-tools.csv", "\n".join(out))

def recent(R, outdir, dry):
    ad = env("APPDATA") if is_live(R) else os.path.join(R, "AppData", "Roaming")
    rec = os.path.join(ad, "Microsoft", "Windows", "Recent")
    items = [os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(rec, "*.lnk"))]
    print(f"  recent: {len(items)} recently-used items")
    if not dry and items: w(outdir, "frequently-used.txt", "\n".join(items[:500]))

def autostart(R, outdir, dry):
    items = []
    ad = env("APPDATA") if is_live(R) else os.path.join(R, "AppData", "Roaming")
    startup = os.path.join(ad, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    items += [os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(startup, "*"))]
    if is_live(R):
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try: key = winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\Run")
                except Exception: continue
                j = 0
                while True:
                    try: nm, _, _ = winreg.EnumValue(key, j); j += 1; items.append(nm)
                    except OSError: break
        except Exception: pass
    print(f"  autostart: {len(items)} startup entries / Run keys")
    if not dry and items: w(outdir, "launch-agents.txt", "\n".join(sorted(set(items))))

# --- inner layer (opt-in only) — Windows Sticky Notes ---
def notes(R, outdir, dry):
    la = env("LOCALAPPDATA") if is_live(R) else os.path.join(R, "AppData", "Local")
    cands = glob.glob(os.path.join(la, "Packages", "Microsoft.MicrosoftStickyNotes_*", "LocalState", "plum.sqlite"))
    if not cands: print("  notes: no Sticky Notes store found"); return
    src = copydb(cands[0])
    if not src: print("  notes: store not accessible"); return
    rows = qy(src, "select Text, CreatedAt, UpdatedAt from Note where Text is not null") or \
           qy(src, "select Text from Note where Text is not null")
    os.unlink(src)
    out = []; n = 0
    for row in rows:
        body = (row[0] or "").strip()
        if sum(ch.isalpha() for ch in body) < 10: continue
        n += 1
        title = body.splitlines()[0][:80] if body else "(untitled)"
        cre = ""
        if len(row) >= 2 and row[1]:
            d = filetime(row[1]) if str(row[1]).isdigit() and len(str(row[1])) > 12 else None
            cre = d.date().isoformat() if d else ""
        out.append(f"### {title}\n*created {cre or '?'}*\n\n{body}\n\n---\n")
    print(f"  notes (INNER LAYER): {n} sticky notes")
    if not dry and out:
        w(outdir, "notes-export.md", f"# Sticky Notes — Full Export\n*{n} notes · personal layer*\n\n---\n\n" + "\n".join(out))

LAYER_FN = {"behavior": behavior, "provenance": provenance, "accounts": accounts, "dev": dev,
            "installs": installs, "shell": shell_history, "recent": recent, "autostart": autostart,
            "notes": notes}

def main():
    ap = argparse.ArgumentParser(add_help=True, description="Windows self-forensics extractor (local, read-only)")
    ap.add_argument("outdir")
    ap.add_argument("--source", default=env("USERPROFILE", os.path.expanduser("~")))
    ap.add_argument("--include-personal", action="store_true")
    ap.add_argument("--layers", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-id", default="")
    a = ap.parse_args()

    R = os.path.abspath(os.path.expanduser(a.source))
    if not os.path.isdir(R): print(f"ERROR: --source not found: {R}"); sys.exit(3)

    chosen = [l.strip() for l in a.layers.split(",") if l.strip()] if a.layers else list(ALL_LAYERS)
    if a.include_personal:
        chosen += [l for l in PERSONAL_LAYERS if l not in chosen]
    else:
        # consent gate: personal layers run ONLY with --include-personal, even if named in --layers
        blocked = [l for l in chosen if l in PERSONAL_LAYERS]
        if blocked:
            print(f"note: ignoring personal layer(s) {', '.join(blocked)} — they require --include-personal.")
        chosen = [l for l in chosen if l not in PERSONAL_LAYERS]
    chosen = [l for l in chosen if l in LAYER_FN]
    inner = "notes" in chosen and a.include_personal

    print("=" * 64)
    print("  DIGITAL SELF-FORENSICS — Windows extractor  (LOCAL · READ-ONLY)")
    print(f"  source root : {R}")
    print(f"  layers      : {', '.join(chosen) or '(none)'}")
    print(f"  inner layer : {'ENABLED — Sticky Notes WILL be written' if inner else 'OFF'}")
    print(f"  mode        : {'DRY-RUN (writes nothing)' if a.dry_run else 'WRITE'}")
    print("=" * 64)

    if inner and not a.dry_run:
        s = under_sync_root(a.outdir)
        if s:
            print(f"REFUSING: output dir is under a cloud-sync root ({s}). The personal layer must")
            print("not be written to synced storage. Choose a local, non-synced OUTDIR and retry.")
            sys.exit(2)

    outdir = a.outdir
    if a.run_id: outdir = os.path.join(a.outdir, f"run-{a.run_id}")
    if not a.dry_run: os.makedirs(outdir, exist_ok=True)

    for layer in chosen:
        print(f"== {layer.upper()} ==")
        try: LAYER_FN[layer](R, outdir, a.dry_run)
        except Exception as e: print(f"  {layer}: error — {e}")

    if a.dry_run: print("\nDRY-RUN complete — nothing was written.")
    else: print(f"\nExtracts written to: {outdir}")

if __name__ == "__main__":
    main()
