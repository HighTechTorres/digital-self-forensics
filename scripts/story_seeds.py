#!/usr/bin/env python3
"""
story_seeds.py — mine the local extracts for *moments worth remembering*, not just metrics.

The reports answer "how do I operate?"; Story Seeds answers "what are the moments I'd want to
keep?" Your disk remembers small narratives you've forgotten — the day a project began, the month
a new obsession took hold, the year everything shifted. This surfaces them as journal-ready seeds:
a title, the window, the on-disk evidence, and a prompt to pull the memory out.

It supplies EVIDENCE and PROMPTS only — it never invents prose. The first-person draft is written
by the skill (the model) from the structured seed, grounded in the evidence, in the user's voice.
Hard rule inherited from the skill: quote, don't dramatize; label inference; nothing diagnosed.

Local-only, OS-agnostic: reads ONLY the extract files already produced (the same CSV/TXT/JSON
correlate.py reads). Never re-queries the disk, never transmits.

Usage:
    python3 story_seeds.py EXTRACT_DIR [--include-personal] [--max N]

Personal note moments are OFF by default; --include-personal turns on the (verbatim-quote) note
detector, only if the inner-layer export is present.

Outputs: story-seeds.json + story-seeds.md in EXTRACT_DIR.
"""
import os, sys, csv, json, re, argparse, collections

def read_csv(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8", errors="ignore") as f:
        return list(csv.DictReader(f))

def read_json(path):
    if not os.path.exists(path): return {}
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return json.load(f)
    except Exception:
        return {}

def host_of(url):
    m = re.sub(r'^\w+://', '', url or '').split('/')[0].replace('www.', '')
    return m.lower() if m else ""

def ym(s):
    m = re.search(r'((?:19|20)\d\d)-(\d\d)', s or "")
    return f"{m.group(1)}-{m.group(2)}" if m else None

def year_of(s):
    m = re.search(r'(19|20)\d\d', s or "")
    if not m: return None
    y = int(m.group(0))
    return y if 1995 <= y <= 2035 else None

def seed(stype, title, when, evidence, prompt, confidence="medium"):
    return {"type": stype, "title": title, "when": when, "evidence": evidence,
            "prompt": prompt, "confidence": confidence, "draft": None}

# ---------------- detectors ----------------
def project_origins(d):
    out = []
    for r in read_csv(os.path.join(d, "git-timeline.csv")):
        first = r.get("first", ""); repo = r.get("repo", "")
        if not first or not repo: continue
        commits = int(r.get("commits") or 0)
        host = host_of(r.get("remote", ""))
        out.append(seed("project-origin", f"The day “{repo}” began", first,
                        {"repo": repo, "first_commit": first, "last_commit": r.get("last", ""),
                         "commits": commits, "host": host},
                        f"What were you hoping “{repo}” would become when you started it — "
                        f"and did it turn out that way?",
                        "high" if commits >= 20 else "medium"))
    out.sort(key=lambda s: -s["evidence"]["commits"])
    return out

def adoption_moments(d):
    by_year = collections.defaultdict(list)
    for r in read_csv(os.path.join(d, "installs.csv")):
        y = year_of(r.get("first_seen", ""))
        if y and r.get("tool"): by_year[y].append(r["tool"])
    out = []
    for y, tools in by_year.items():
        if len(tools) >= 3:
            sample = ", ".join(tools[:6])
            out.append(seed("adoption-moment", f"The year your toolkit jumped ({y})", str(y),
                            {"year": y, "tool_count": len(tools), "tools": tools[:12]},
                            f"In {y} you picked up {sample}. What were you trying to build or "
                            f"learn that pulled these in?",
                            "high" if len(tools) >= 6 else "medium"))
    out.sort(key=lambda s: -s["evidence"]["tool_count"])
    return out

def research_bursts(d):
    counts = collections.Counter()
    for r in read_csv(os.path.join(d, "download-provenance.csv")):
        h = host_of(r.get("page_url", "")); m = ym(r.get("downloaded", ""))
        if h and m: counts[(m, h)] += 1
    out = []
    for (month, host), n in counts.most_common(40):
        if n >= 8:
            out.append(seed("research-burst", f"A deep dive into {host} ({month})", month,
                            {"month": month, "source": host, "downloads": n},
                            f"You pulled {n} things from {host} in {month}. What rabbit hole or "
                            f"project was that?",
                            "high" if n >= 20 else "medium"))
    return out[:12]

def era_turning_points(d):
    corr = read_json(os.path.join(d, "correlations.json"))
    out = []
    for s in corr.get("era_seams", []):
        win = s.get("window", ""); signals = s.get("signals", [])
        if not win: continue
        out.append(seed("era-turning-point", f"{win} was a turning point", win,
                        {"window": win, "signals": signals},
                        f"Several parts of your life shifted around {win} "
                        f"({', '.join(signals)}). What changed for you then?",
                        "high"))
    return out

def note_moments(d):
    """Inner layer, opt-in only. Quote the user's own note titles + dates VERBATIM; never paraphrase."""
    path = os.path.join(d, "Apple-Notes-Full-Export.md")
    if not os.path.exists(path): return []
    text = open(path, encoding="utf-8", errors="ignore").read()
    out = []
    # match "### Title\n*created YYYY-MM-DD ..."
    for m in re.finditer(r'^###\s+(.+?)\s*\n\*created\s+([0-9?]{4}-?[0-9?]{0,2}-?[0-9?]{0,2})',
                         text, re.MULTILINE):
        title = m.group(1).strip()[:120]; created = m.group(2)
        if len(title) < 4 or title.lower().startswith("(untitled"): continue
        out.append(seed("note-moment", f"A note: “{title}”", created,
                        {"note_title_verbatim": title, "created": created},
                        "What's the story behind this note — what was going on when you wrote it?",
                        "medium"))
        if len(out) >= 20: break
    return out

def main():
    ap = argparse.ArgumentParser(description="Mine extracts for journal-ready story seeds (local).")
    ap.add_argument("extract_dir")
    ap.add_argument("--include-personal", action="store_true",
                    help="Also mine the inner-layer note export (verbatim quotes). Off by default.")
    ap.add_argument("--max", type=int, default=40, help="Max seeds to emit (default 40)")
    a = ap.parse_args()
    d = a.extract_dir
    if not os.path.isdir(d):
        print(f"ERROR: extract dir not found: {d}"); sys.exit(2)

    seeds = []
    seeds += era_turning_points(d)   # strongest signal first
    seeds += project_origins(d)
    seeds += adoption_moments(d)
    seeds += research_bursts(d)
    personal = False
    if a.include_personal:
        ns = note_moments(d)
        personal = bool(ns)
        seeds += ns
    seeds = seeds[:a.max]

    out = {"schema_version": "1.0", "personal_layer_included": personal,
           "count": len(seeds), "seeds": seeds}
    json.dump(out, open(os.path.join(d, "story-seeds.json"), "w"), indent=2)

    md = ["# Story Seeds — moments your disk remembers", "",
          "*Journal-ready starting points mined locally from your own data. The **evidence** is "
          "factual; the **draft** is for the skill to write in your voice from that evidence — "
          "grounded, never dramatized. The **prompt** is yours to answer.*", "",
          f"*personal layer: {'included' if personal else 'excluded'} · {len(seeds)} seeds*", ""]
    if not seeds:
        md.append("*(Not enough dated signal yet — run more extractor layers, then re-run.)*")
    for s in seeds:
        md.append(f"## {s['title']} — _{s['when']}_  ·  ({s['type']}, confidence: {s['confidence']})")
        md.append(f"**The evidence.** `{json.dumps(s['evidence'])}`")
        md.append("**The draft.** _(skill to write a short first-person paragraph from the evidence above)_")
        md.append(f"**A prompt.** {s['prompt']}\n")
    open(os.path.join(d, "story-seeds.md"), "w").write("\n".join(md))

    by_type = collections.Counter(s["type"] for s in seeds)
    print(f"story_seeds: {len(seeds)} seeds "
          f"({', '.join(f'{k}:{v}' for k, v in by_type.items()) or 'none'}) "
          f"(personal={'on' if personal else 'off'}) -> story-seeds.json + story-seeds.md")

if __name__ == "__main__":
    main()
