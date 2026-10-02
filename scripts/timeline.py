#!/usr/bin/env python3
"""
timeline.py — Phase 6 super-timeline: merge every dated event in the extracts into one chronology.

Operates ONLY on the local extract files an extractor already wrote (no disk re-query, OS-agnostic,
stdlib only). Writes:
    timeline.csv  — one row per event: date,year,month,source,event,detail
    timeline.md   — yearly counts by source, busiest months, first/last activity per source, and
                    inflection points (the biggest year-over-year swings), each labelled FACT.

Usage:
    python3 timeline.py EXTRACT_DIR [--out DIR] [--include-personal]

Sources (each optional; a missing file is skipped and reported):
    download-provenance.csv  downloads        (detail = source host)
    git-timeline.csv         repo first/last commit
    installs.csv             tool first seen
    photo-exif.csv           photos taken     (dates + camera only — GPS is never copied)
    app-usage.csv            app sessions     (usually a short recent window)
    notes                    note created dates — ONLY with --include-personal; dates only, no
                             titles or bodies (the timeline is a counting artifact, not a quote).
"""
import os, sys, re, csv, argparse, collections

from _common import read_csv, year_of

NOTES_FILES = ["Apple-Notes-Full-Export.md", "notes-export.md"]  # macOS Notes / Windows Sticky Notes
# Sources whose files cover only a short retention window (knowledgeC ~2–4 weeks, `last`, UserAssist):
# they're listed per year but kept OUT of busiest-months and inflections, where a recent window would
# masquerade as a behavior change.
WINDOW_SOURCES = {"app-usage"}
DATE_RE = re.compile(r'((?:19|20)\d\d)-(\d\d)(?:-(\d\d))?')

def norm_date(s):
    """'2021-03-09T10:00:00' / '2021-03-09' / '2021-03' -> ('2021-03-09', 2021, '2021-03'), else None."""
    m = DATE_RE.search(s or "")
    if not m or not year_of(m.group(1)): return None
    y, mo, d = m.group(1), m.group(2), m.group(3) or "01"
    if not ("01" <= mo <= "12"): return None
    return f"{y}-{mo}-{d}", int(y), f"{y}-{mo}"

HOST_RE = re.compile(r'^[a-z][a-z0-9+.-]*://(?:[^@/]*@)?([^/:?#]+)', re.I)

def host_of(url):
    """Hostname of URL (no 'www.'), or '' — plain string parsing; nothing is ever fetched."""
    m = HOST_RE.match((url or "").strip())
    h = m.group(1).lower() if m else ""
    return h[4:] if h.startswith("www.") else h

def collect(d, include_personal):
    ev, seen, missing = [], [], []
    def add(date_s, source, event, detail=""):
        nd = norm_date(date_s)
        if nd: ev.append((nd[0], nd[1], nd[2], source, event, detail))

    def src(name, label, fn):
        path = os.path.join(d, name)
        if not os.path.exists(path): missing.append(name); return
        before = len(ev); fn(path); seen.append((label, len(ev) - before))

    src("download-provenance.csv", "downloads",
        lambda p: [add(r.get("downloaded"), "downloads", "download", host_of(r.get("page_url") or r.get("file_url")))
                   for r in read_csv(p)])

    def git(p):
        for r in read_csv(p):
            name = os.path.basename((r.get("repo") or "").rstrip("/\\")) or "(repo)"
            add(r.get("first"), "git", "repo started", name)
            if r.get("last") and r.get("last") != r.get("first"):
                add(r.get("last"), "git", "last commit", name)
    src("git-timeline.csv", "git", git)

    src("installs.csv", "installs",
        lambda p: [add(r.get("first_seen"), "installs", "tool adopted", r.get("tool", "")) for r in read_csv(p)])
    src("photo-exif.csv", "photos",
        lambda p: [add(r.get("taken"), "photos", "photo", r.get("camera", "")) for r in read_csv(p)])
    src("app-usage.csv", "app-usage",
        lambda p: [add(r.get("start"), "app-usage", "app session", (r.get("app") or "").split(".")[-1])
                   for r in read_csv(p)])

    notes = next((n for n in NOTES_FILES if os.path.exists(os.path.join(d, n))), None)
    if notes and include_personal:
        def notes_fn(p):
            text = open(p, encoding="utf-8", errors="ignore").read()
            for m in re.finditer(r'^\*created\s+(\S+)', text, re.MULTILINE):
                add(m.group(1), "notes", "note written", "")   # date only — never a title or body
        src(notes, "notes", notes_fn)
    elif notes:
        print("  notes: present but skipped (inner layer needs --include-personal)")

    ev.sort()
    return ev, seen, missing

def inflections(by_year_src, years, min_volume=5):
    """Biggest year-over-year rise and fall per source (ignoring tiny volumes)."""
    out = []
    for s, counts in by_year_src.items():
        if s in WINDOW_SOURCES: continue
        best_up = best_dn = None
        for a, b in zip(years, years[1:]):
            x, y = counts.get(a, 0), counts.get(b, 0)
            if max(x, y) < min_volume: continue
            delta = y - x
            if delta > 0 and (best_up is None or delta > best_up[2]): best_up = (a, b, delta, x, y)
            if delta < 0 and (best_dn is None or delta < best_dn[2]): best_dn = (a, b, delta, x, y)
        for kind, t in (("rise", best_up), ("drop", best_dn)):
            if t: out.append({"source": s, "kind": kind, "from": t[0], "to": t[1], "before": t[3], "after": t[4]})
    out.sort(key=lambda r: -abs(r["after"] - r["before"]))
    return out

def render_md(ev, seen, missing):
    by_year_src = collections.defaultdict(collections.Counter)
    by_month = collections.Counter()
    first, last = {}, {}
    for date, y, mo, s, _, _ in ev:
        by_year_src[s][y] += 1
        if s not in WINDOW_SOURCES: by_month[mo] += 1
        first.setdefault(s, date); last[s] = date
    years = list(range(min(e[1] for e in ev), max(e[1] for e in ev) + 1)) if ev else []
    sources = [s for s, _ in seen if by_year_src.get(s)]

    md = ["# Super-timeline", "",
          f"*{len(ev)} dated events from {len(sources)} source(s), built locally from the extracts. "
          "Counts are FACT; reading meaning into them is inference — label it when you write the report.*", ""]
    if not ev:
        return "\n".join(md + ["*(no dated events found)*", ""]), []

    md += ["## Events per year", "", "| Year | " + " | ".join(sources) + " | Total |",
           "|---|" + "---|" * (len(sources) + 1)]
    for y in years:
        row = [by_year_src[s].get(y, 0) for s in sources]
        md.append(f"| {y} | " + " | ".join(str(n) for n in row) + f" | {sum(row)} |")

    md += ["", "## Busiest months", "", "*Excludes short-window sources (" + ", ".join(sorted(WINDOW_SOURCES))
           + ") — their recent window is retention, not a trend.*", ""]
    md += [f"- {mo} — {n} events" for mo, n in by_month.most_common(8)]

    md += ["", "## First and last activity per source", "", "| Source | First | Last |", "|---|---|---|"]
    md += [f"| {s} | {first[s]} | {last[s]} |" for s in sources]

    inf = inflections(by_year_src, years)
    md += ["", "## Inflection points (biggest year-over-year swings)", ""]
    md += [f"- **{r['source']}** {r['kind']}: {r['from']} → {r['to']} ({r['before']} → {r['after']})" for r in inf[:10]] \
          or ["*(no swings above the noise floor)*"]
    if missing:
        md += ["", f"*Not present (skipped): {', '.join(missing)}*"]
    return "\n".join(md) + "\n", inf

def main():
    ap = argparse.ArgumentParser(description="Merge every dated extract into one super-timeline (local).")
    ap.add_argument("extract_dir")
    ap.add_argument("--out", default="", help="Output dir (default: EXTRACT_DIR)")
    ap.add_argument("--include-personal", action="store_true",
                    help="Also count note-created dates (dates only; never titles or bodies)")
    a = ap.parse_args()
    d = a.extract_dir
    if not os.path.isdir(d): print(f"not a directory: {d}"); sys.exit(3)
    out = a.out or d
    os.makedirs(out, exist_ok=True)

    ev, seen, missing = collect(d, a.include_personal)
    with open(os.path.join(out, "timeline.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["date", "year", "month", "source", "event", "detail"]); w.writerows(ev)
    md, inf = render_md(ev, seen, missing)
    with open(os.path.join(out, "timeline.md"), "w", encoding="utf-8") as f: f.write(md)

    parts = ", ".join(f"{s}:{n}" for s, n in seen) or "none"
    print(f"timeline: {len(ev)} events ({parts}), {len(inf)} inflections "
          f"(personal={'on' if a.include_personal else 'off'}) -> timeline.csv + timeline.md")

if __name__ == "__main__":
    main()
