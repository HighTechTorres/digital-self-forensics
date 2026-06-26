#!/usr/bin/env python3
"""
correlate.py — find what's BETWEEN the sources, not just within them.

Operates ONLY on the local extract CSVs already produced by an extractor (no disk re-query,
OS-agnostic). Computes cross-source findings and writes correlations.json + correlations.md.

Usage:
    python3 correlate.py EXTRACT_DIR

Findings:
  - consume->create crossover : the year acquisition (downloads) fell while output (new
                                repos / tool adoption) rose — the clearest substrate-leap.
  - adoption leaps            : years you adopted clusters of new tooling.
  - era seams                : years where >=2 independent sources shift together.
  - intention gaps            : stated intentions (from Notes) vs later behavior — ONLY if the
                               personal layer (Apple-Notes-Full-Export.md) is present; every
                               row is conservative inference, default verdict 'unknown'.
Every finding separates FACT (from data) from INFERENCE (the join's reading).
"""
import os, sys, csv, json, re, collections, datetime

def read_csv(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8", errors="ignore") as f:
        return list(csv.DictReader(f))

def year_of(s):
    m=re.search(r'(19|20)\d\d', s or "")
    if not m: return None
    y=int(m.group(0))
    return y if 1995<=y<=2035 else None  # clamp out stray/epoch-zero years

def main():
    if len(sys.argv)<2: print(__doc__); sys.exit(1)
    d=sys.argv[1]
    findings=[]; era_seams=[]; intention_gaps=[]
    personal = os.path.exists(os.path.join(d,"Apple-Notes-Full-Export.md"))

    # ---- yearly signals ----
    consume=collections.Counter()  # downloads/yr
    for r in read_csv(os.path.join(d,"download-provenance.csv")):
        y=year_of(r.get("downloaded",""));
        if y: consume[y]+=1
    new_repos=collections.Counter()  # first-commit year per repo
    for r in read_csv(os.path.join(d,"git-timeline.csv")):
        y=year_of(r.get("first",""));
        if y: new_repos[y]+=1
    adopt=collections.Counter()  # tool first_seen per year
    for r in read_csv(os.path.join(d,"installs.csv")):
        y=year_of(r.get("first_seen",""));
        if y: adopt[y]+=1

    years=sorted(set(list(consume)+list(new_repos)+list(adopt)))
    create={y: new_repos.get(y,0)+adopt.get(y,0) for y in years}

    # ---- consume->create crossover ----
    if consume and any(create.values()):
        # steepest consume drop between consecutive years
        drops=[(years[i], consume.get(years[i-1],0)-consume.get(years[i],0)) for i in range(1,len(years))]
        drop_year, drop_mag = (max(drops, key=lambda t:t[1]) if drops else (None,0))
        peak_create_year = max(create, key=lambda y: create[y]) if create else None
        if drop_year and drop_mag>0:
            findings.append({
                "id":"consume-create-crossover","type":"crossover",
                "fact":{"metric":"downloads_per_year","values":[consume.get(y,0) for y in years],"years":years,
                        "new_outputs_per_year":[create.get(y,0) for y in years]},
                "inference":f"Acquisition fell sharpest into {drop_year} (−{drop_mag} downloads vs prior year) "
                            f"while creative output (new repos+tools) clustered around {peak_create_year}. "
                            f"Reads as a shift from consuming to producing.",
                "confidence":"high" if drop_mag>=20 else "medium",
                "sources":["provenance","git","installs"],
                "so_what":"Name this as your 'started building' inflection — it's a datable origin point."})

    # ---- adoption leaps ----
    if adopt:
        top=sorted(adopt.items(), key=lambda t:-t[1])[:3]
        for y,n in top:
            if n>=3:
                findings.append({"id":f"adoption-leap-{y}","type":"adoption-leap",
                    "fact":{"year":y,"tools_adopted":n},
                    "inference":f"{n} new tools first appeared in {y} — a capability expansion year.",
                    "confidence":"medium","sources":["installs"],
                    "so_what":"Tool-adoption spikes often mark when your work changed shape — check what shipped after."})

    # ---- era seams (>=2 sources shift in the same year) ----
    for y in years:
        signals=[]
        if consume.get(y,0) and consume.get(y,0) >= (max(consume.values())*0.6 if consume else 0): signals.append("download-spike")
        if new_repos.get(y,0): signals.append("new-repo")
        if adopt.get(y,0) and adopt.get(y,0) >= (max(adopt.values())*0.6 if adopt else 0): signals.append("tool-adoption-cluster")
        if len(signals)>=2:
            era_seams.append({"window":str(y),"signals":signals,"sources":["provenance","git","installs"]})

    # ---- intention gaps (personal layer only) ----
    if personal:
        txt=open(os.path.join(d,"Apple-Notes-Full-Export.md"),encoding="utf-8",errors="ignore").read()
        # conservative: pull lines that read like stated intentions; never judge fulfillment automatically
        pat=re.compile(r'(?im)^(.*\b(i will|i am going to|my goal|i want to become|launch|declare|become a|by \d{4})\b.*)$')
        seen=set()
        for m in pat.finditer(txt):
            line=m.group(1).strip()[:180]
            if len(line)<12 or line in seen: continue
            seen.add(line)
            intention_gaps.append({"stated_intention_quote":line,"verdict":"unknown",
                "note":"Inference requires the user to confirm against behavior; not auto-judged."})
            if len(intention_gaps)>=25: break

    out={"schema_version":"1.0","personal_layer_included":personal,
         "generated_from":[f for f in ["download-provenance.csv","git-timeline.csv","installs.csv","shell-tools.csv"] if os.path.exists(os.path.join(d,f))],
         "findings":findings,"era_seams":era_seams,"intention_gaps":intention_gaps}
    json.dump(out, open(os.path.join(d,"correlations.json"),"w"), indent=2)

    # markdown
    md=["# Correlations — what's *between* your sources","",
        f"*personal layer: {'included' if personal else 'excluded'} · generated from local extracts only*","","## Cross-source findings",""]
    if not findings: md.append("*(Not enough overlapping dated sources to correlate — run more layers.)*")
    for fnd in findings:
        md.append(f"### {fnd['id']}  ·  _{fnd['type']}_  ·  confidence: {fnd['confidence']}")
        md.append(f"- **Fact (data):** `{json.dumps(fnd['fact'])[:300]}`")
        md.append(f"- **Inference (the join):** {fnd['inference']}")
        md.append(f"- **Sources:** {', '.join(fnd['sources'])}")
        md.append(f"- **So what:** {fnd['so_what']}\n")
    md.append("## Era seams (multiple sources shifting together)")
    md += [f"- **{s['window']}** — {', '.join(s['signals'])}" for s in era_seams] or ["*(none detected)*"]
    if personal:
        md.append("\n## Stated intentions (from your notes — for YOU to judge, not auto-rated)")
        md += [f"- “{g['stated_intention_quote']}” → _{g['verdict']}_" for g in intention_gaps] or ["*(none found)*"]
    open(os.path.join(d,"correlations.md"),"w").write("\n".join(md))
    print(f"correlate: {len(findings)} findings, {len(era_seams)} era seams, {len(intention_gaps)} intentions "
          f"(personal={'on' if personal else 'off'}) -> correlations.json + correlations.md")

if __name__=="__main__":
    main()
