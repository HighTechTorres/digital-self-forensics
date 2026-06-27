#!/usr/bin/env python3
"""
macos_extract.py (v2) — macOS deep-artifact extractor for self-forensics.

Local-only. Read-only on sources (databases are copied before querying). The personal/inner
layer (Apple Notes bodies) is OFF by default and only enabled with --include-personal.

Usage:
    python3 macos_extract.py OUTDIR [options]

Options:
    --source PATH        Artifact root to read from (default: $HOME). Use for an OLD drive,
                         a Time Machine / migrated tree (e.g. /Volumes/Old/Users/me). Read-only.
    --include-personal   Enable the inner layer (decompress Apple Notes bodies). Default: OFF.
    --layers a,b,c       Only run these layers. Names: behavior,provenance,accounts,dev,
                         installs,shell,spotlight,agents,notes  (default: all non-personal).
    --dry-run            Print the inventory + what WOULD be extracted. Writes nothing.
    --run-id ID          Name the run (default: timestamp) — used for longitudinal diffing.
    --no-notes           Deprecated; now a no-op (notes already off unless --include-personal).

Exit codes: 0 ok · 2 bad args · 3 source not found.
Apple/Core Data timestamps are seconds since 2001-01-01 (add 978307200 for Unix epoch).
Apple Notes bodies are gzip-compressed protobufs in ZICNOTEDATA.ZDATA.
"""
import os, sys, argparse, sqlite3, shutil, tempfile, gzip, zlib, re, datetime, glob, collections, subprocess

EPOCH = 978307200
ALL_LAYERS = ["behavior","provenance","accounts","dev","installs","shell","spotlight","agents"]
PERSONAL_LAYERS = ["notes"]
SYNC_ROOTS = ["Dropbox","Library/Mobile Documents","iCloud","OneDrive","Google Drive","GoogleDrive","pCloud","Box Sync"]

def under_sync_root(path):
    ap = os.path.abspath(path)
    return next((s for s in SYNC_ROOTS if f"/{s}" in ap or ap.endswith(s)), None)

def copydb(path):
    if not os.path.exists(path): return None
    tmp = tempfile.mktemp(suffix=".db"); shutil.copy2(path, tmp)
    for ext in ("-wal","-shm"):
        if os.path.exists(path+ext):
            try: shutil.copy2(path+ext, tmp+ext)
            except Exception: pass
    return tmp

def q(db, sql, params=()):
    con=sqlite3.connect(db); con.text_factory=lambda b: b.decode("utf-8","ignore") if isinstance(b,bytes) else b
    try: return con.execute(sql, params).fetchall()
    finally: con.close()

def macdate(v):
    try: return datetime.datetime(2001,1,1)+datetime.timedelta(seconds=float(v))
    except Exception: return None

def w(outdir, name, text):
    p=os.path.join(outdir,name); open(p,"w",encoding="utf-8").write(text); return p

# ---------------- layers ----------------
def behavior(R, outdir, dry):
    src=copydb(f"{R}/Library/Application Support/Knowledge/knowledgeC.db")
    if not src: print("  behavior: knowledgeC not accessible (grant Full Disk Access)"); return
    rows=q(src,"select ZVALUESTRING,ZSTARTDATE,ZENDDATE from ZOBJECT where ZSTREAMNAME='/app/usage' and ZVALUESTRING is not null")
    os.unlink(src)
    if not rows: print("  behavior: no app-usage rows"); return
    by_app=collections.Counter(); by_hour=collections.Counter(); out=["app,start_epoch,start,minutes"]
    for app,s,e in rows:
        d=macdate(s); mins=round((float(e)-float(s))/60.0,1) if e and s else 0
        by_app[app]+=mins
        if d: by_hour[d.hour]+=mins; out.append(f'{app},{int(float(s)+EPOCH)},{d.isoformat()},{mins}')
    print("  behavior (top apps by hours): "+", ".join(f"{a.split('.')[-1]} {round(m/60,1)}h" for a,m in by_app.most_common(6)))
    if not dry: w(outdir,"app-usage.csv","\n".join(out))

def provenance(R, outdir, dry):
    src=copydb(f"{R}/Library/Preferences/com.apple.LaunchServices.QuarantineEventsV2")
    if not src: print("  provenance: quarantine db not found"); return
    rows=q(src,"select LSQuarantineTimeStamp,LSQuarantineAgentName,LSQuarantineDataURLString,LSQuarantineOriginURLString from LSQuarantineEvent")
    os.unlink(src)
    out=["downloaded,app,file_url,page_url"]; by_year=collections.Counter()
    for ts,app,furl,purl in rows:
        d=macdate(ts); out.append(f'"{d.isoformat() if d else ""}","{app or ""}","{furl or ""}","{purl or ""}"')
        if d: by_year[d.year]+=1
    print("  provenance: %d downloads | by year: %s" % (len(rows), " ".join(f"{y}:{by_year[y]}" for y in sorted(by_year))))
    if not dry: w(outdir,"download-provenance.csv","\n".join(out))

def accounts(R, outdir, dry):
    doms=set()
    for base in (f"{R}/Library/Application Support/BraveSoftware/Brave-Browser",
                 f"{R}/Library/Application Support/Google/Chrome"):
        for ld in glob.glob(base+"/*/Login Data"):
            src=copydb(ld)
            if not src: continue
            try:
                for (realm,) in q(src,"select signon_realm from logins"):
                    m=re.sub(r'https?://','',realm or '').split('/')[0].replace('www.','')
                    if m and not m.startswith(('android','192.168','10.','127.')): doms.add(m)
            except Exception: pass
            os.unlink(src)
    print(f"  accounts: {len(doms)} unique service domains (logins)")
    if not dry: w(outdir,"saas-account-footprint.txt","\n".join(sorted(doms)))

def dev(R, outdir, dry):
    repos=subprocess.run(f"find '{R}' -maxdepth 5 -name .git -type d 2>/dev/null",shell=True,capture_output=True,text=True).stdout.split()
    lines=["repo,commits,first,last,remote"]; seen=set()
    for g in repos:
        r=g[:-5]; name=os.path.basename(r)
        cnt=subprocess.run(["git","-C",r,"rev-list","--all","--count"],capture_output=True,text=True).stdout.strip() or "0"
        log=subprocess.run(["git","-C",r,"log","--all","--format=%H %ad","--date=format:%Y-%m-%d"],capture_output=True,text=True).stdout.splitlines()
        dates=[ln.split()[1] for ln in log if ln.split() and ln.split()[0] not in seen and not seen.add(ln.split()[0])]
        rem=subprocess.run(["git","-C",r,"config","--get","remote.origin.url"],capture_output=True,text=True).stdout.strip()
        lines.append(f'{name},{cnt},{min(dates) if dates else ""},{max(dates) if dates else ""},{rem}')
    kh=f"{R}/.ssh/known_hosts"; nhosts=sum(1 for _ in open(kh,errors="ignore")) if os.path.exists(kh) else 0
    print(f"  dev: {len(repos)} git repos | ssh known_hosts: {nhosts}")
    if not dry: w(outdir,"git-timeline.csv","\n".join(lines))

def installs(R, outdir, dry):
    """Tool-adoption chronology — a substrate-leap detector.
    Uses CREATION time (birthtime), not mtime — mtime is reset by every app auto-update,
    which would falsely pile recent years with 'adoptions'. Brew uses the install receipt."""
    events=["tool,first_seen,source"]; seen=set()
    for a in glob.glob(f"{R}/Applications/*.app")+glob.glob("/Applications/*.app"):
        name=os.path.basename(a)[:-4]
        if name in seen: continue
        seen.add(name)
        try:
            st=os.stat(a); ts=getattr(st,"st_birthtime",st.st_mtime)
            events.append(f'{name},{datetime.date.fromtimestamp(ts).isoformat()},app-created')
        except Exception: pass
    cellar=subprocess.run("brew --cellar 2>/dev/null",shell=True,capture_output=True,text=True).stdout.strip()
    if cellar and os.path.isdir(cellar):
        for pkg in os.listdir(cellar):
            pkgdir=os.path.join(cellar,pkg)
            try:
                recs=glob.glob(os.path.join(pkgdir,"*","INSTALL_RECEIPT.json"))
                ts=os.path.getmtime(recs[0]) if recs else getattr(os.stat(pkgdir),"st_birthtime",os.path.getmtime(pkgdir))
                events.append(f'{pkg},{datetime.date.fromtimestamp(ts).isoformat()},brew')
            except Exception: pass
    print(f"  installs: {len(events)-1} tool-adoption events (by creation date)")
    if not dry: w(outdir,"installs.csv","\n".join(events))

def shell_history(R, outdir, dry):
    """Command frequency (no timestamps in most histories) — skill curve in the terminal."""
    text=""
    for h in (".zsh_history",".bash_history"):
        p=os.path.join(R,h)
        if os.path.exists(p): text+=open(p,errors="ignore").read()+"\n"
    if not text: print("  shell: no history found"); return
    cmds=collections.Counter()
    for line in text.splitlines():
        line=re.sub(r'^: \d+:\d+;','',line).strip()
        tok=line.split()
        if tok: cmds[tok[0]]+=1
    out=["command,count"]+[f"{c},{n}" for c,n in cmds.most_common(60)]
    print("  shell: top tools "+", ".join(f"{c}({n})" for c,n in cmds.most_common(6)))
    if not dry: w(outdir,"shell-tools.csv","\n".join(out))

def spotlight(R, outdir, dry):
    """Most-used docs via Spotlight (only meaningful for the live ~; skipped for --source)."""
    if os.path.abspath(R)!=os.path.abspath(os.path.expanduser("~")):
        print("  spotlight: skipped (only works on the live home volume)"); return
    res=subprocess.run(["mdfind","-onlyin",R,"kMDItemUseCount > 5"],capture_output=True,text=True).stdout.splitlines()
    print(f"  spotlight: {len(res)} frequently-used items")
    if not dry and res: w(outdir,"frequently-used.txt","\n".join(res[:500]))

def agents(R, outdir, dry):
    """What runs automatically = your already-outsourced cognition."""
    items=[]
    for d in (f"{R}/Library/LaunchAgents",):
        items+= [os.path.basename(p)[:-6] for p in glob.glob(d+"/*.plist")]
    print(f"  agents: {len(items)} user LaunchAgents")
    if not dry and items: w(outdir,"launch-agents.txt","\n".join(sorted(items)))

# --- inner layer (opt-in only) ---
def _decompress(b):
    if not b: return ""
    for f in (gzip.decompress, zlib.decompress, lambda x: zlib.decompress(x,-15)):
        try: return f(b).decode("utf-8","ignore")
        except Exception: continue
    return ""
def _clean(s):
    s=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]',' ',s)
    runs=re.findall(r'[\w \t\.\,\;\:\!\?\'\"\-\(\)\/\&\%\$\#\@\+\=\nÀ-ɏ¿¡“”’–—•]{2,}', s)
    return re.sub(r'\n{3,}','\n\n', re.sub(r'[ \t]{2,}',' ', ' '.join(runs))).strip()
def notes(R, outdir, dry):
    src=copydb(f"{R}/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite")
    if not src: print("  notes: not accessible (Full Disk Access)"); return
    con=sqlite3.connect(src); con.text_factory=bytes
    try:
        rows=con.execute("""select c.ZTITLE1,c.ZCREATIONDATE1,c.ZMODIFICATIONDATE1,d.ZDATA
            from ZICCLOUDSYNCINGOBJECT c join ZICNOTEDATA d on c.ZNOTEDATA=d.Z_PK
            where c.ZNOTEDATA is not null order by c.ZMODIFICATIONDATE1 desc""").fetchall()
    except Exception as e:
        con.close(); os.unlink(src); print("  notes: query failed",e); return
    con.close(); os.unlink(src)
    out=[]; n=0
    for title,cre,mod,data in rows:
        ti=(title or b"").decode("utf-8","ignore").strip(); body=_clean(_decompress(data))
        if ti and body.startswith(ti): body=body[len(ti):].strip()
        if sum(ch.isalpha() for ch in body)<25: continue
        n+=1; cm=macdate(cre); md=macdate(mod)
        out.append(f"### {ti or '(untitled)'}\n*created {cm.date() if cm else '?'} · modified {md.date() if md else '?'}*\n\n{body}\n\n---\n")
    print(f"  notes (INNER LAYER): {n} notes")
    if not dry: w(outdir,"Apple-Notes-Full-Export.md",f"# Apple Notes — Full Export\n*{n} notes · decompressed locally · personal layer*\n\n---\n\n"+"\n".join(out))

LAYER_FN = {"behavior":behavior,"provenance":provenance,"accounts":accounts,"dev":dev,
            "installs":installs,"shell":shell_history,"spotlight":spotlight,"agents":agents,"notes":notes}

def main():
    ap=argparse.ArgumentParser(add_help=True, description="macOS self-forensics extractor v2 (local, read-only)")
    ap.add_argument("outdir")
    ap.add_argument("--source", default=os.path.expanduser("~"))
    ap.add_argument("--include-personal", action="store_true")
    ap.add_argument("--layers", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--no-notes", action="store_true", help=argparse.SUPPRESS)
    a=ap.parse_args()

    R=os.path.abspath(os.path.expanduser(a.source))
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

    # consent banner — always printed first, before touching anything
    inner = "notes" in chosen and a.include_personal
    print("="*64)
    print("  DIGITAL SELF-FORENSICS — macOS extractor v2  (LOCAL · READ-ONLY)")
    print(f"  source root : {R}")
    print(f"  layers      : {', '.join(chosen) or '(none)'}")
    print(f"  inner layer : {'ENABLED — note bodies WILL be written' if inner else 'OFF (no personal note bodies)'}")
    print(f"  mode        : {'DRY-RUN (writes nothing)' if a.dry_run else 'WRITE'}")
    print("="*64)

    # sync-root guard for the inner layer
    if inner and not a.dry_run:
        s=under_sync_root(a.outdir)
        if s:
            print(f"REFUSING: output dir is under a cloud-sync root ({s}). The personal layer must")
            print("not be written to synced storage. Choose a local, non-synced OUTDIR and retry.")
            sys.exit(2)

    outdir=a.outdir
    if a.run_id: outdir=os.path.join(a.outdir, f"run-{a.run_id}")
    if not a.dry_run: os.makedirs(outdir, exist_ok=True)

    for layer in chosen:
        print(f"== {layer.upper()} ==")
        try: LAYER_FN[layer](R, outdir, a.dry_run)
        except Exception as e: print(f"  {layer}: error — {e}")

    if a.dry_run: print("\nDRY-RUN complete — nothing was written.")
    else: print(f"\nExtracts written to: {outdir}")

if __name__=="__main__":
    main()
