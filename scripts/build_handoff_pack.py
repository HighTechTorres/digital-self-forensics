#!/usr/bin/env python3
"""
build_handoff_pack.py — turn the local extracts into a portable Handoff Pack that seeds
your NEXT computer (and the AI assistant on it) with who you are and how you work.

The reports (Phase 7) are written for a human to *read*. The Handoff Pack is written for a
machine to *ingest*: a structured profile, a drop-in AI-context file, and a re-provisioning
manifest, so a fresh machine starts out already knowing your tools, projects, rhythm, and
domains instead of being a blank slate.

Local-only, OS-agnostic: it reads ONLY the extract files already produced on this machine
(the same CSV/TXT/JSON that correlate.py reads). It never re-queries the disk and never
transmits anything.

Usage:
    python3 build_handoff_pack.py EXTRACT_DIR [--out DIR] [--name LABEL] [--include-personal]

By default the pack is SAFE TO MOVE: the personal/inner layer (Apple Notes bodies) is left
OUT even when it was extracted — a pack you carry to a new machine is exactly where you do
not want health/money/relationship notes embedded. Pass --include-personal to add a clearly
marked private/ section anyway (it refuses to do so under a cloud-sync output root).

Outputs (in EXTRACT_DIR/context-pack/ unless --out is given):
    profile.json      machine-readable profile (the source of truth)
    PROFILE.md        the same profile, human-readable
    CLAUDE.md         drop-in memory file for Claude Code on the new machine
    ABOUT-ME.md       provider-neutral "what an AI should know about me"
    provisioning.md   re-provisioning manifest (apps, packages, CLI, automations, logins)
    README.md         how to seed the new machine with this pack
    private/          ONLY with --include-personal — note-derived context, never auto-shared
"""
import os, sys, csv, json, re, argparse, collections, datetime

SYNC_ROOTS = ["Dropbox", "Mobile Documents", "iCloud", "OneDrive", "Google Drive",
              "GoogleDrive", "pCloud", "Box Sync"]

def under_sync_root(path):
    ap = os.path.abspath(path)
    return next((s for s in SYNC_ROOTS if f"/{s}" in ap or ap.endswith(s)), None)

def read_csv(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8", errors="ignore") as f:
        return list(csv.DictReader(f))

def read_lines(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8", errors="ignore") as f:
        return [ln.strip() for ln in f if ln.strip()]

def read_json(path):
    if not os.path.exists(path): return {}
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return json.load(f)
    except Exception:
        return {}

def short_app(name):
    # com.apple.Safari -> Safari ; keep plain names as-is
    return name.split(".")[-1] if "." in name else name

def host_of(url):
    m = re.sub(r'^\w+://', '', url or '').split('/')[0].replace('www.', '')
    return m.lower() if m else ""

def build_profile(d):
    p = {"schema_version": "1.0",
         "generated": datetime.datetime.now().isoformat(timespec="seconds"),
         "note": "Derived locally from on-disk extracts. Facts are counted from data; "
                 "any 'reads as' phrasing is inference for you to confirm."}

    # ---- work rhythm + primary apps (app-usage.csv) ----
    by_app = collections.Counter(); by_hour = collections.Counter()
    for r in read_csv(os.path.join(d, "app-usage.csv")):
        try: mins = float(r.get("minutes") or 0)
        except ValueError: mins = 0
        app = short_app(r.get("app", "") or "")
        if app: by_app[app] += mins
        m = re.search(r'T(\d\d):', r.get("start", "") or "")
        if m: by_hour[int(m.group(1))] += mins
    primary_apps = [{"app": a, "hours": round(m / 60, 1)} for a, m in by_app.most_common(10)]
    peak_hours = [h for h, _ in by_hour.most_common(4)]

    # ---- tech stack adopted (installs.csv) ----
    adopted = []
    for r in read_csv(os.path.join(d, "installs.csv")):
        adopted.append({"tool": r.get("tool", ""), "first_seen": r.get("first_seen", ""),
                        "source": r.get("source", "")})
    adopted.sort(key=lambda x: x.get("first_seen", ""))

    # ---- CLI tools (shell-tools.csv) ----
    cli = [{"command": r.get("command", ""), "count": int(r.get("count") or 0)}
           for r in read_csv(os.path.join(d, "shell-tools.csv"))]
    cli = [c for c in cli if c["command"]][:25]

    # ---- projects (git-timeline.csv) ----
    projects = []
    code_hosts = collections.Counter()
    for r in read_csv(os.path.join(d, "git-timeline.csv")):
        rem = r.get("remote", "") or ""
        if rem: code_hosts[host_of(rem)] += 1
        projects.append({"repo": r.get("repo", ""), "commits": int(r.get("commits") or 0),
                         "first": r.get("first", ""), "last": r.get("last", ""), "remote": rem})
    projects.sort(key=lambda x: -x["commits"])

    # ---- services to re-authenticate (saas-account-footprint.txt) ----
    services = read_lines(os.path.join(d, "saas-account-footprint.txt"))

    # ---- automations (launch-agents.txt) ----
    automations = read_lines(os.path.join(d, "launch-agents.txt"))

    # ---- download sources (download-provenance.csv) ----
    dl_hosts = collections.Counter()
    for r in read_csv(os.path.join(d, "download-provenance.csv")):
        h = host_of(r.get("page_url", ""))
        if h: dl_hosts[h] += 1

    # ---- eras / inflections (correlations.json) ----
    corr = read_json(os.path.join(d, "correlations.json"))
    inflections = [{"id": f.get("id"), "inference": f.get("inference"),
                    "so_what": f.get("so_what")} for f in corr.get("findings", [])]
    era_seams = [s.get("window") for s in corr.get("era_seams", [])]

    p["work_rhythm"] = {"peak_hours": peak_hours, "primary_apps": primary_apps}
    p["tooling"] = {"tech_stack_adopted": adopted, "cli_tools": cli,
                    "automations": automations}
    p["projects"] = projects[:40]
    p["code_hosts"] = code_hosts.most_common()
    p["services"] = services
    p["download_sources_top"] = dl_hosts.most_common(15)
    p["eras"] = {"inflections": inflections, "era_seams": era_seams}
    p["provisioning"] = {
        "apps": [a["tool"] for a in adopted if a.get("source") == "app-created"],
        "brew": [a["tool"] for a in adopted if a.get("source") == "brew"],
        "cli": [c["command"] for c in cli],
        "automations": automations,
        "services_to_relogin": services,
    }
    return p

def md_profile(p):
    L = ["# Profile — who this machine says you are", "",
         f"*Generated {p['generated']} · derived locally from on-disk extracts.*", ""]
    wr = p["work_rhythm"]
    if wr["peak_hours"]:
        L += [f"**Work rhythm.** Most-active hours: {', '.join(f'{h:02d}:00' for h in wr['peak_hours'])}.", ""]
    if wr["primary_apps"]:
        L += ["**Primary apps (by tracked hours):**",
              ", ".join(f"{a['app']} ({a['hours']}h)" for a in wr["primary_apps"][:8]), ""]
    if p["tooling"]["cli_tools"]:
        L += ["**Terminal stack:** " + ", ".join(c["command"] for c in p["tooling"]["cli_tools"][:15]), ""]
    if p["tooling"]["tech_stack_adopted"]:
        recent = p["tooling"]["tech_stack_adopted"][-12:]
        L += ["**Recently adopted tooling:** " + ", ".join(f"{a['tool']}" for a in recent), ""]
    if p["projects"]:
        L += ["**Top projects (by commits):**"]
        L += [f"- `{pr['repo']}` — {pr['commits']} commits ({pr['first']}→{pr['last']})"
              for pr in p["projects"][:10]] + [""]
    if p["services"]:
        L += [f"**Service footprint:** {len(p['services'])} domains with saved logins "
              "(re-login list in provisioning.md).", ""]
    if p["eras"]["inflections"]:
        L += ["**Inflection points:**"]
        L += [f"- {i['inference']}" for i in p["eras"]["inflections"] if i.get("inference")] + [""]
    return "\n".join(L)

def md_claude(p):
    apps = ", ".join(a["app"] for a in p["work_rhythm"]["primary_apps"][:6])
    cli = ", ".join(c["command"] for c in p["tooling"]["cli_tools"][:12])
    hosts = ", ".join(h for h, _ in p["code_hosts"][:3])
    projects = ", ".join(pr["repo"] for pr in p["projects"][:6])
    hrs = ", ".join(f"{h:02d}:00" for h in p["work_rhythm"]["peak_hours"])
    return f"""# About me (seeded from my previous machine)

This file was generated by digital-self-forensics from my old computer so you (Claude Code)
know how I work from day one. Treat it as starting context, not gospel — confirm before
acting on anything load-bearing.

## How I work
- Most-active hours: {hrs or 'unknown'}.
- Primary apps: {apps or 'n/a'}.
- Terminal tools I reach for: {cli or 'n/a'}.

## What I build
- I host code mainly on: {hosts or 'n/a'}.
- Recent / notable projects: {projects or 'n/a'}.
- When suggesting tooling or conventions, prefer what's already in my stack above.

## Defaults to assume
- I value local-first, privacy-respecting workflows (this very file came from a local-only audit).
- Match the conventions of whatever repo we're in; mirror surrounding code.

*Source: digital-self-forensics Handoff Pack. Regenerate after a fresh audit to keep current.*
"""

def md_about(p):
    return ("# What an AI assistant should know about me\n\n"
            "Provider-neutral context distilled from my previous computer. Load this into any "
            "assistant to skip the cold-start.\n\n" + md_profile(p).split("\n", 2)[2])

def md_provisioning(p):
    pv = p["provisioning"]
    L = ["# Re-provisioning manifest", "",
         "A checklist to make a new machine feel like home. Nothing here is executed for you — "
         "it's a guide. Review before installing anything.", ""]
    if pv["brew"]:
        L += ["## Homebrew packages to consider", "```", "brew install " + " ".join(pv["brew"][:80]), "```", ""]
    if pv["apps"]:
        L += ["## Applications previously installed", ", ".join(pv["apps"][:60]), ""]
    if pv["cli"]:
        L += ["## CLI tools you used most", ", ".join(pv["cli"][:25]), ""]
    if pv["automations"]:
        L += ["## Automations to recreate (were LaunchAgents)", ""]
        L += [f"- {a}" for a in pv["automations"]] + [""]
    if pv["services_to_relogin"]:
        L += ["## Services to sign back into", ""]
        L += [f"- {s}" for s in pv["services_to_relogin"][:80]] + [""]
    return "\n".join(L)

SEED_README = """# Your Handoff Pack — how to seed the new machine

This folder is a portable snapshot of how you worked on your old computer, built to give a
fresh machine (and its AI assistant) instant context instead of a blank slate.

**What's inside**
- `profile.json` / `PROFILE.md` — the structured profile (source of truth + readable form).
- `CLAUDE.md` — drop into a new repo (or `~/.claude/`) so Claude Code knows you immediately.
- `ABOUT-ME.md` — same idea, provider-neutral, for any assistant.
- `provisioning.md` — a checklist to reinstall tools, recreate automations, and re-login.
- `private/` — only present if you explicitly included the personal layer; keep it off shared drives.

**To seed the new machine**
1. Copy this folder to the new computer (a USB stick or a *local* transfer — not a public share).
2. Drop `CLAUDE.md` where your AI tooling reads memory (e.g. a project root or `~/.claude/`).
3. Work through `provisioning.md` to rebuild your environment.
4. Re-run digital-self-forensics on the new machine in a month to refresh the pack.

*Everything here was produced locally. Nothing was uploaded. The pack is only as private as
where you store it — treat it like the keys to your digital self.*
"""

def main():
    ap = argparse.ArgumentParser(description="Build a portable Handoff Pack from local extracts.")
    ap.add_argument("extract_dir", help="Directory containing the extract CSV/TXT/JSON files")
    ap.add_argument("--out", default="", help="Output dir (default: EXTRACT_DIR/context-pack)")
    ap.add_argument("--name", default="", help="Optional label for the pack (used in headers)")
    ap.add_argument("--include-personal", action="store_true",
                    help="Also write a private/ section from the inner layer (off by default)")
    a = ap.parse_args()

    d = a.extract_dir
    if not os.path.isdir(d):
        print(f"ERROR: extract dir not found: {d}"); sys.exit(2)
    out = a.out or os.path.join(d, "context-pack")

    if a.include_personal:
        s = under_sync_root(out)
        if s:
            print(f"REFUSING: --include-personal under a cloud-sync root ({s}). "
                  "Choose a local, non-synced --out.")
            sys.exit(2)

    os.makedirs(out, exist_ok=True)
    p = build_profile(d)
    if a.name: p["name"] = a.name
    p["personal_layer_included"] = bool(a.include_personal)

    json.dump(p, open(os.path.join(out, "profile.json"), "w"), indent=2)
    open(os.path.join(out, "PROFILE.md"), "w").write(md_profile(p))
    open(os.path.join(out, "CLAUDE.md"), "w").write(md_claude(p))
    open(os.path.join(out, "ABOUT-ME.md"), "w").write(md_about(p))
    open(os.path.join(out, "provisioning.md"), "w").write(md_provisioning(p))
    open(os.path.join(out, "README.md"), "w").write(SEED_README)

    wrote_private = False
    notes_path = next((os.path.join(d, f) for f in
                       ("Apple-Notes-Full-Export.md", "notes-export.md")
                       if os.path.exists(os.path.join(d, f))), None)
    if a.include_personal and notes_path:
        priv = os.path.join(out, "private"); os.makedirs(priv, exist_ok=True)
        import shutil
        shutil.copy2(notes_path, os.path.join(priv, "notes-export.md"))
        open(os.path.join(priv, "README.md"), "w").write(
            "# Private layer\n\nThis folder contains note-derived context. Keep it OFF shared or "
            "synced drives. It is never auto-shared and was only written because you passed "
            "--include-personal.\n")
        wrote_private = True

    print(f"Handoff Pack written to: {out}")
    print(f"  profile.json · PROFILE.md · CLAUDE.md · ABOUT-ME.md · provisioning.md · README.md"
          f"{' · private/' if wrote_private else ''}")
    print(f"  {len(p['projects'])} projects · {len(p['services'])} services · "
          f"{len(p['tooling']['tech_stack_adopted'])} tools · "
          f"{'personal INCLUDED' if wrote_private else 'personal excluded (safe to move)'}")

if __name__ == "__main__":
    main()
