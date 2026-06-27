#!/usr/bin/env python3
"""
linux_extract.py — Linux deep-artifact extractor for self-forensics.

Native counterpart to macos_extract.py. Same contract, same OUTPUT FILE SCHEMA, so the
OS-agnostic downstream tools (correlate.py, build_handoff_pack.py, story_seeds.py, render_docs.py)
work on the results unchanged.

Local-only. Read-only on sources (databases are copied before querying). There is no Apple-Notes
equivalent on Linux, so there is no inner/personal layer here; --include-personal is accepted but
a no-op (printed as such).

Usage:
    python3 linux_extract.py OUTDIR [options]

Options (mirror macos_extract.py):
    --source PATH        Artifact root (default: $HOME). Use for an old drive / migrated tree.
    --include-personal   Accepted for parity; no inner layer exists on Linux (no-op).
    --layers a,b,c       Subset of: behavior,provenance,accounts,dev,installs,shell,recent,autostart
    --dry-run            Print what WOULD be extracted; write nothing.
    --run-id ID          Name the run (writes to OUTDIR/run-ID) for longitudinal diffing.

Exit codes: 0 ok · 2 bad args · 3 source not found.

Timestamp notes: Firefox places.sqlite = microseconds since 1970 (/1e6); Chrome History =
microseconds since 1601 ((t/1e6)-11644473600).
"""
import os, sys, argparse, sqlite3, shutil, tempfile, re, datetime, glob, collections, subprocess, json

ALL_LAYERS = ["behavior", "provenance", "accounts", "dev", "installs", "shell", "recent", "autostart"]
SYNC_ROOTS = ["Dropbox", "OneDrive", "Google Drive", "GoogleDrive", "pCloud", "Nextcloud", "ownCloud"]

def under_sync_root(path):
    ap = os.path.abspath(path)
    return next((s for s in SYNC_ROOTS if f"/{s}" in ap or ap.endswith(s)), None)

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

def host_of(url):
    m = re.sub(r'^\w+://', '', url or '').split('/')[0].replace('www.', '')
    return m if m else ""

def run(cmd):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout
    except Exception: return ""

def chrome_time(v):
    try: return datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=int(v))
    except Exception: return None

def ff_time(v):
    try: return datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=int(v))
    except Exception: return None

# ---------------- layers ----------------
def behavior(R, outdir, dry):
    """Session rhythm from `last` (login spans). Honest signal: machine-use hours, not per-app."""
    if os.path.abspath(R) != os.path.abspath(os.path.expanduser("~")):
        print("  behavior: skipped (last/journald only reflect the live machine)"); return
    out = ["app,start_epoch,start,minutes"]; by_hour = collections.Counter(); total = 0.0
    txt = run("last -F 2>/dev/null") or run("last 2>/dev/null")
    for line in txt.splitlines():
        if not line.strip() or line.startswith("wtmp") or "reboot" in line: continue
        m = re.search(r'\((\d+)\+?(\d{2}):(\d{2})\)', line)  # (DD+HH:MM) or (HH:MM)
        if not m: continue
        days = int(m.group(1)) if "+" in line[m.start():m.end()] else 0
        # fallback parse for (HH:MM) form
        dur = None
        mm = re.search(r'\((?:(\d+)\+)?(\d{2}):(\d{2})\)', line)
        if mm:
            d = int(mm.group(1) or 0); dur = d * 1440 + int(mm.group(2)) * 60 + int(mm.group(3))
        ts = re.search(r'(\w{3}\s+\w{3}\s+\d+\s+\d{2}:\d{2})', line)
        hh = re.search(r'\b(\d{2}):(\d{2})\b', line)
        if dur and hh:
            by_hour[int(hh.group(1))] += dur; total += dur
            out.append(f'session,,{ts.group(1) if ts else ""},{dur}')
    if len(out) > 1:
        print(f"  behavior: {len(out)-1} sessions, ~{round(total/60,1)}h tracked; peak hours "
              + ", ".join(f"{h:02d}:00" for h, _ in by_hour.most_common(4)))
        if not dry: w(outdir, "app-usage.csv", "\n".join(out))
    else:
        print("  behavior: no session history (last/wtmp empty)")

def _chrome_profiles(R):
    bases = [f"{R}/.config/google-chrome", f"{R}/.config/chromium",
             f"{R}/.config/BraveSoftware/Brave-Browser", f"{R}/.config/microsoft-edge"]
    for b in bases:
        for prof in glob.glob(b + "/*/"):
            yield prof.rstrip("/")

def provenance(R, outdir, dry):
    out = ["downloaded,app,file_url,page_url"]; by_year = collections.Counter(); n = 0
    # Chrome-family History.downloads (has tab_url = referrer)
    for prof in _chrome_profiles(R):
        src = copydb(os.path.join(prof, "History"))
        if not src: continue
        for tgt, ref, start in qy(src, "select target_path, tab_url, start_time from downloads"):
            d = chrome_time(start)
            out.append(f'"{d.isoformat() if d else ""}","chrome","{tgt or ""}","{ref or ""}"')
            if d: by_year[d.year] += 1
            n += 1
        os.unlink(src)
    # Firefox downloads via places annotations
    for places in glob.glob(f"{R}/.mozilla/firefox/*/places.sqlite"):
        src = copydb(places)
        if not src: continue
        rows = qy(src, "select p.url, a.dateAdded from moz_places p join moz_annos a on a.place_id=p.id "
                       "join moz_anno_attributes t on a.anno_attribute_id=t.id "
                       "where t.name like 'downloads%'")
        for url, da in rows:
            d = ff_time(da)
            out.append(f'"{d.isoformat() if d else ""}","firefox","{url or ""}",""')
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
    for lj in glob.glob(f"{R}/.mozilla/firefox/*/logins.json"):
        try:
            data = json.load(open(lj, encoding="utf-8", errors="ignore"))
            for e in data.get("logins", []):
                m = re.sub(r'https?://', '', e.get("hostname", "") or '').split('/')[0].replace('www.', '')
                if m: doms.add(m)
        except Exception: pass
    print(f"  accounts: {len(doms)} unique service domains (logins)")
    if not dry and doms: w(outdir, "saas-account-footprint.txt", "\n".join(sorted(doms)))

def dev(R, outdir, dry):
    repos = run(f"find '{R}' -maxdepth 6 -name .git -type d 2>/dev/null").split()
    lines = ["repo,commits,first,last,remote"]; seen = set()
    for g in repos:
        r = g[:-5]; name = os.path.basename(r.rstrip("/"))
        cnt = subprocess.run(["git", "-C", r, "rev-list", "--all", "--count"], capture_output=True, text=True).stdout.strip() or "0"
        log = subprocess.run(["git", "-C", r, "log", "--all", "--format=%H %ad", "--date=format:%Y-%m-%d"], capture_output=True, text=True).stdout.splitlines()
        dates = [ln.split()[1] for ln in log if ln.split() and ln.split()[0] not in seen and not seen.add(ln.split()[0])]
        rem = subprocess.run(["git", "-C", r, "config", "--get", "remote.origin.url"], capture_output=True, text=True).stdout.strip()
        lines.append(f'{name},{cnt},{min(dates) if dates else ""},{max(dates) if dates else ""},{rem}')
    kh = f"{R}/.ssh/known_hosts"; nhosts = sum(1 for _ in open(kh, errors="ignore")) if os.path.exists(kh) else 0
    print(f"  dev: {len(repos)} git repos | ssh known_hosts: {nhosts}")
    if not dry and len(lines) > 1: w(outdir, "git-timeline.csv", "\n".join(lines))

def installs(R, outdir, dry):
    """Tool-adoption chronology from package managers that record install dates."""
    events = ["tool,first_seen,source"]; seen = set()
    live = os.path.abspath(R) == os.path.abspath(os.path.expanduser("~"))
    # dpkg log (Debian/Ubuntu) — has dates
    for logf in sorted(glob.glob("/var/log/dpkg.log*")):
        opener = open
        try:
            if logf.endswith(".gz"):
                import gzip; opener = gzip.open
            for ln in opener(logf, "rt", errors="ignore"):
                m = re.match(r'(\d{4}-\d{2}-\d{2}) \S+ install (\S+?)(?::\S+)? ', ln)
                if m and m.group(2) not in seen:
                    seen.add(m.group(2)); events.append(f"{m.group(2)},{m.group(1)},dpkg")
        except Exception: pass
    # pacman log (Arch) — has dates
    if os.path.exists("/var/log/pacman.log"):
        for ln in open("/var/log/pacman.log", errors="ignore"):
            m = re.match(r'\[(\d{4}-\d{2}-\d{2})[^\]]*\].*installed (\S+)', ln)
            if m and m.group(2) not in seen:
                seen.add(m.group(2)); events.append(f"{m.group(2)},{m.group(1)},pacman")
    # rpm --last (Fedora/RHEL) — only on live system
    if live:
        for ln in run("rpm -qa --last 2>/dev/null").splitlines():
            parts = ln.split()
            if len(parts) >= 4:
                name = parts[0].rsplit("-", 2)[0]
                try:
                    d = datetime.datetime.strptime(" ".join(parts[-4:-1]), "%a %d %b").replace(year=datetime.date.today().year)
                except Exception: d = None
                if name not in seen:
                    seen.add(name); events.append(f"{name},{(d.date().isoformat() if d else '')},rpm")
        for ln in run("flatpak list --columns=application 2>/dev/null").splitlines():
            if ln.strip() and ln not in seen: seen.add(ln); events.append(f"{ln.strip()},,flatpak")
        for ln in run("snap list 2>/dev/null").splitlines()[1:]:
            t = ln.split()
            if t and t[0] not in seen: seen.add(t[0]); events.append(f"{t[0]},,snap")
    print(f"  installs: {len(events)-1} tool-adoption events")
    if not dry and len(events) > 1: w(outdir, "installs.csv", "\n".join(events))

def shell_history(R, outdir, dry):
    text = ""
    for h in (".zsh_history", ".bash_history"):
        p = os.path.join(R, h)
        if os.path.exists(p): text += open(p, errors="ignore").read() + "\n"
    for h in (".python_history", ".node_repl_history", ".psql_history"):
        p = os.path.join(R, h)
        if os.path.exists(p): text += open(p, errors="ignore").read() + "\n"
    if not text: print("  shell: no history found"); return
    cmds = collections.Counter()
    for line in text.splitlines():
        line = re.sub(r'^: \d+:\d+;', '', line).strip()
        tok = line.split()
        if tok: cmds[tok[0]] += 1
    out = ["command,count"] + [f"{c},{n}" for c, n in cmds.most_common(60)]
    print("  shell: top tools " + ", ".join(f"{c}({n})" for c, n in cmds.most_common(6)))
    if not dry: w(outdir, "shell-tools.csv", "\n".join(out))

def recent(R, outdir, dry):
    xbel = f"{R}/.local/share/recently-used.xbel"
    if not os.path.exists(xbel): print("  recent: recently-used.xbel not found"); return
    hrefs = re.findall(r'href="([^"]+)"', open(xbel, errors="ignore").read())
    files = [re.sub(r'^file://', '', h) for h in hrefs]
    print(f"  recent: {len(files)} recently-used items")
    if not dry and files: w(outdir, "frequently-used.txt", "\n".join(files[:500]))

def autostart(R, outdir, dry):
    items = []
    for p in glob.glob(f"{R}/.config/autostart/*.desktop"):
        items.append(os.path.basename(p)[:-8])
    if os.path.abspath(R) == os.path.abspath(os.path.expanduser("~")):
        for ln in run("systemctl --user list-unit-files --state=enabled 2>/dev/null").splitlines():
            t = ln.split()
            if t and t[0].endswith(".service"): items.append(t[0])
    print(f"  autostart: {len(items)} autostart entries / enabled user services")
    if not dry and items: w(outdir, "launch-agents.txt", "\n".join(sorted(set(items))))

LAYER_FN = {"behavior": behavior, "provenance": provenance, "accounts": accounts, "dev": dev,
            "installs": installs, "shell": shell_history, "recent": recent, "autostart": autostart}

def main():
    ap = argparse.ArgumentParser(add_help=True, description="Linux self-forensics extractor (local, read-only)")
    ap.add_argument("outdir")
    ap.add_argument("--source", default=os.path.expanduser("~"))
    ap.add_argument("--include-personal", action="store_true")
    ap.add_argument("--layers", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-id", default="")
    a = ap.parse_args()

    R = os.path.abspath(os.path.expanduser(a.source))
    if not os.path.isdir(R): print(f"ERROR: --source not found: {R}"); sys.exit(3)

    chosen = [l.strip() for l in a.layers.split(",") if l.strip()] if a.layers else list(ALL_LAYERS)
    chosen = [l for l in chosen if l in LAYER_FN]

    print("=" * 64)
    print("  DIGITAL SELF-FORENSICS — Linux extractor  (LOCAL · READ-ONLY)")
    print(f"  source root : {R}")
    print(f"  layers      : {', '.join(chosen) or '(none)'}")
    print(f"  inner layer : N/A on Linux (no notes equivalent)")
    print(f"  mode        : {'DRY-RUN (writes nothing)' if a.dry_run else 'WRITE'}")
    print("=" * 64)
    if a.include_personal:
        print("note: --include-personal has no effect on Linux (no inner layer).")

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
