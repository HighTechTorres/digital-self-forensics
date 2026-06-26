#!/usr/bin/env python3
"""
diff_runs.py — turn the one-shot audit into a practice: compare two runs and report the delta.

Usage:
    python3 diff_runs.py OLD_RUN_DIR NEW_RUN_DIR

Reports (to NEW_RUN_DIR/diff.md): new & dropped SaaS domains, new repos / commit growth,
new download sources, shifted top shell tools. Also accumulates app-usage across runs into a
growing behavior-history.csv beside the runs — because knowledgeC only retains ~2-4 weeks, so
the longitudinal rhythm only exists if you stitch monthly runs together.
"""
import os, sys, csv, collections

def lines(p):
    return [l.strip() for l in open(p,encoding="utf-8",errors="ignore")] if os.path.exists(p) else []
def rows(p):
    return list(csv.DictReader(open(p,encoding="utf-8",errors="ignore"))) if os.path.exists(p) else []

def main():
    if len(sys.argv)<3: print(__doc__); sys.exit(1)
    old,new=sys.argv[1],sys.argv[2]
    md=["# Run diff", f"*old: {os.path.basename(old)} → new: {os.path.basename(new)}*",""]

    o=set(lines(os.path.join(old,"saas-account-footprint.txt")))
    n=set(lines(os.path.join(new,"saas-account-footprint.txt")))
    md += ["## Accounts", f"- **+{len(n-o)} new services:** {', '.join(sorted(n-o)[:25]) or '—'}",
           f"- **-{len(o-n)} dropped:** {', '.join(sorted(o-n)[:25]) or '—'}",""]

    orepo={r['repo']:int(r.get('commits',0) or 0) for r in rows(os.path.join(old,'git-timeline.csv'))}
    nrepo={r['repo']:int(r.get('commits',0) or 0) for r in rows(os.path.join(new,'git-timeline.csv'))}
    new_repos=[r for r in nrepo if r not in orepo]
    grew=[(r,nrepo[r]-orepo[r]) for r in nrepo if r in orepo and nrepo[r]>orepo[r]]
    md += ["## Code", f"- **new repos:** {', '.join(new_repos) or '—'}",
           f"- **commit growth:** {', '.join(f'{r}(+{g})' for r,g in grew) or '—'}",""]

    def dl_sources(p):
        c=collections.Counter()
        for r in rows(p):
            u=r.get('file_url','');
            if '://' in u: c[u.split('://')[1].split('/')[0]]+=1
        return c
    od=dl_sources(os.path.join(old,'download-provenance.csv')); nd=dl_sources(os.path.join(new,'download-provenance.csv'))
    md += ["## Downloads", f"- **new sources:** {', '.join(sorted(set(nd)-set(od))[:20]) or '—'}",""]

    os.makedirs(os.path.dirname(os.path.abspath(new)) or '.', exist_ok=True)
    open(os.path.join(new,"diff.md"),"w").write("\n".join(md))

    # accumulate behavior history (dedupe on app+start_epoch)
    hist=os.path.join(os.path.dirname(os.path.abspath(new)) or '.',"behavior-history.csv")
    seen=set(); allrows=[]
    for src in (hist, os.path.join(old,"app-usage.csv"), os.path.join(new,"app-usage.csv")):
        for r in rows(src):
            k=(r.get('app'),r.get('start_epoch'))
            if k in seen or not r.get('app'): continue
            seen.add(k); allrows.append(r)
    if allrows:
        with open(hist,"w",newline="") as f:
            wcsv=csv.DictWriter(f, fieldnames=["app","start_epoch","start","minutes"]); wcsv.writeheader()
            for r in allrows: wcsv.writerow({k:r.get(k,'') for k in ["app","start_epoch","start","minutes"]})
    print(f"diff_runs: wrote {new}/diff.md ; behavior-history now {len(allrows)} unique sessions")

if __name__=="__main__":
    main()
