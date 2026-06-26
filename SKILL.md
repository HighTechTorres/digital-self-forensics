---
name: digital-self-forensics
description: Audit the user's OWN computer to mine it for self-insight — reconstruct their eras, work rhythm, habits, and what mattered to them from on-disk artifacts (browser profiles, downloads, notes, app-usage logs, git history, infrastructure), then produce narrative report documents. Use this whenever the user wants to "audit my computer," "see what my machine says about me," analyze their old/new laptop for personal or professional insights, profile their own digital habits, build a personal timeline from their data, or do self-directed digital self-discovery on a machine they own. Trigger even without the word "forensics" — "what does my computer know about me," "analyze my Mac/PC," "extract insights from my old laptop," and "profile how I work from my data" all qualify. v2 also correlates across sources (the year behavior changed, era seams, adoption leaps), supports longitudinal re-runs, and reconstructs a "ghost self" from an old drive. Works on macOS, Windows, and Linux.
---

# Digital Self-Forensics

Turn the user's own computer into a mirror. Years of browser profiles, downloads, notes, code, and behavioral logs sit on the disk — an honest record of who they've been, what they chased, and how they actually spend their time. This skill reads those artifacts and synthesizes them into **narrative insight about the user**, delivered as polished report documents (Markdown + Word/PDF).

It was distilled from a complete real session. The bundled scripts encode the techniques that are easy to get wrong (timestamp math, decompressing Notes, copying locked databases, rendering documents), so each run is fast and reliable instead of reinventing them.

## Non-negotiable ground rules (state these to the user up front)

These protect the user and are the whole basis of trust — follow them and say you are:

- **Own machine only.** This is self-audit. If the user asks to run it on someone else's device, decline — that's surveillance, not self-discovery.
- **100% local.** Never upload, push, sync, or transmit the user's data anywhere. No external API calls with their personal content. Everything stays on disk.
- **Read-only on sources.** Always *copy* a database to a temp dir before querying it; never modify, delete, or write to original artifacts.
- **The user controls depth.** The personal layer (notes on health, money, relationships, beliefs) is theirs to include or exclude — ask before extracting it, and honor the answer.
- **Flag inference vs. fact.** Ground every claim in real data; label guesses as guesses.

## Process overview

Run these phases in order, showing results and checking in between. Don't dump everything at once — this is a guided experience, and the user's reactions improve the output.

1. **Interview** — capture intent (what they want, how deep, privacy comfort).
2. **Detect OS & assess the machine** — snapshot + data inventory.
3. **Request permissions** — the deep layers need elevated access (e.g. Full Disk Access on macOS). Walk them through it.
4. **Persona/era census** — map browser profiles (and key folders) to life/work eras.
5. **Deep-artifact extraction** — behavior, download provenance, notes, accounts, dev/infra.
6. **Super-timeline** — merge every dated event into one chronology; find inflection points.
7. **Synthesis** — write the report(s), including (if permitted) the personal layer.
8. **Package & export** — one folder, every doc as Markdown + Word + PDF, with an index.

---

## Phase 1 — Interview (capture intent)

Before touching the disk, ask the user a few questions so the output serves *their* purpose. Use the AskUserQuestion tool if available; otherwise ask inline. Cover:

- **Purpose** — what's this for? (self-knowledge · a personal-brand/founder story · a résumé/portfolio · understanding their own habits/productivity · just curiosity)
- **Depth** — surface (browser/era level) or deep (behavioral + personal notes)?
- **Privacy comfort** — include the sensitive layer (health/money/relationships/beliefs notes), or business/neutral only?
- **Audience** — just them, or something they'll share? (If shareable, plan to also produce a redacted edition.)

Reflect their answers back in one line and proceed. The purpose shapes the voice of the final report (warm-personal vs. professional-portfolio).

## Phase 2 — Detect OS & assess the machine

Identify the OS, then snapshot the system and inventory the data sources worth mining.

- Run `scripts/assess_system.sh` (macOS/Linux). On **Windows**, follow `references/windows.md` (PowerShell commands).
- Then read the OS-specific reference for the full artifact map:
  - macOS → `references/macos.md`
  - Windows → `references/windows.md`
  - Linux → `references/linux.md`
- Report: hardware/OS/disk/uptime/updates, and a prioritized list of which artifact sources EXIST and are richest on *this* machine.

## Phase 3 — Request the permissions the deep layers need

The most revealing data (app-usage behavior, Notes, Mail/Messages) is access-gated. Tell the user plainly that without it those layers return "authorization denied," and walk them through granting it — then have them confirm before continuing.

- **macOS:** *System Settings → Privacy & Security → Full Disk Access → ➕ add Terminal (or their terminal app) → toggle ON → restart the terminal.* Verify by reading one gated DB (see `references/macos.md`).
- **Windows / Linux:** usually no extra grant for the user's own files; note where admin/sudo is needed (see the OS reference). 

Phases 4 can run without elevated access; Phase 5's behavioral/personal layers need it.

## Phase 4 — Persona/era census

Map the user's identities and eras from their browser profiles (the highest-signal, lowest-friction source).

- For every profile in every browser: name + email, bookmark count + **folder names** + top domains, history date-range + most-visited + recent searches. **Copy** `Bookmarks`/`History` to temp first (locked while the browser runs).
- Produce a table mapping each profile → a job/business/persona/era, and flag the richest ones.
- If the user doesn't use profiles, substitute Downloads/Documents/Desktop clusters and shell history as the "era" sources.
- For each meaningful era, write a **deep-dive** narrative doc (second person, insight-driven: a "why this era mattered" opener, tables, "Insight:" callouts, a timeline, "what this reveals about you"). If subagents are available, spawn them in parallel — one per era — to write concurrently.

## Phase 5 — Deep-artifact extraction (the layers bookmarks can't show)

Use the bundled extractor and the OS reference. On macOS, `scripts/macos_extract.py` pulls it all. **The inner layer is OFF by default in code** — Notes bodies are written only with `--include-personal`, honoring the Phase-1 consent answer mechanically, not just in prose.

- **First pass:** `python3 scripts/macos_extract.py <out> --dry-run` — prints the inventory + exactly what each layer would extract, writing nothing. Show this to the user.
- **Standard run (no inner layer):** `python3 scripts/macos_extract.py <out>` → behavior, provenance, accounts, dev/infra, plus **installs** (tool-adoption chronology), **shell** (terminal tool frequency), **spotlight** (most-used docs), **agents** (LaunchAgents). The consent banner states what's on.
- **Only if the user opted into the inner layer:** add `--include-personal`. The script refuses to write the inner layer under a cloud-sync root.
- **Old drive / backup (cross-machine):** add `--source /Volumes/Old/Users/<name>` to read a ghost machine instead of `~` (experimental).

What each layer yields: behavior (daily rhythm), provenance (consume→create signal), accounts (SaaS footprint, domains only — never passwords), dev/infra (git timeline, server fleet, automations), installs+shell (substrate-leap dates), notes (the inner layer, opt-in).

Then tell the user the **non-obvious** findings, not just the data — but the real cross-source synthesis happens in Phase 6.5.

## Phase 6 — Super-timeline

Merge every dated event — downloads, git commits, note dates, app installs — into one monthly+yearly chronology (the extractor emits the data; assemble the narrative). Surface the **inflection points**: the year their behavior changed, peaks, the consume→create flip. This is where scattered artifacts become a single story.

## Phase 6.5 — Correlate (the headline of v2)

v1 found what's *in* each source; the insight density is in what's *between* them. Run the OS-agnostic correlation engine over the extracts (no disk re-query):

`python3 scripts/correlate.py <extract_dir>` → `correlations.json` + `correlations.md`.

It computes: the **consume→create crossover** (the datable year acquisition fell while output rose), **adoption leaps** (years of clustered new tooling), **era seams** (years ≥2 sources shift together = the true chapter boundaries), and — only if the inner layer was extracted — a conservative **stated-intention** list pulled from the notes (verdicts default to `unknown`; the user judges fulfillment, the skill never auto-rates a person). Every finding separates **fact** from **inference**. These findings become the *lead* of the report (Phase 7), not an afterthought.

## Phase 7 — Synthesis

Write the deliverables, matching the voice to the Phase-1 purpose:

- **Complete report** — all layers consolidated, ending with a one-paragraph portrait of *how they operate and what mattered to them*.
- **The super-timeline doc** (from Phase 6).
- If the user opted into the personal layer, include it with care and dignity (their own words; no sensationalizing).
- If the output will be shared, also produce a **business-only redacted edition** with the personal layer removed.

Use the structure in `assets/report-template.md` (findings-first — the cross-source findings lead; per-layer detail goes to appendices). Ground everything in the extracted data; keep fact and inference distinct. For any inner-layer claim, **quote the user's own words** — never dramatize, diagnose, or narrativize pain. The redacted business-only edition is the default shareable artifact; an edition that includes the inner layer requires the user to explicitly confirm.

## Phase 7.5 — Adversarial review (challenge the portrait)

A self-portrait written by one agent has one agent's blind spots, and the flattering version is the easy version. Spawn a **fresh subagent with no prior context** whose only job is to read the drafted report + the raw extracts and write `blind-spots.md`:

- claims the data does **not** support (over-reach);
- patterns in the data the report **ignored** (under-reach);
- the most flattering sentence — does the data earn it?
- 3 questions the portrait avoided.

Instruct it to be disagreeable on substance: cite the data line or say nothing; no praise, no hedging. Default target is the **redacted edition**, never the inner layer unless the user opts in. **Do not make external-model API calls** — running the same review through a different provider is optional manual guidance for the user, on the redacted edition only. Fold its output into the report's "What this portrait is avoiding" section.

## Phase 7.6 — Longitudinal (optional — turn the snapshot into a practice)

Behavioral retention is short (knowledgeC ~2–4 weeks), so a single run captures a sliver and calls it "rhythm." Frame the skill as **run monthly**: each run writes a timestamped `run-YYYYMMDD/` folder (use `--run-id`), and `python3 scripts/diff_runs.py <old_run> <new_run>` reports what changed (new/dropped services, repo/commit growth, new download sources) and **accumulates** app-usage into a growing `behavior-history.csv` the single snapshot can't produce. The first run is the baseline.

## Phase 8 — Package & export

Make it portable and self-explaining.

- Create a folder in the user's Downloads named for the audit.
- Convert every document to **Word + PDF** with `python3 scripts/render_docs.py <folder_or_file>` (it auto-detects available tools: pandoc → textutil → LibreOffice for docx; headless Chrome/Chromium → pandoc → wkhtmltopdf for PDF).
- Copy all docs + a `raw-data/` folder of source extracts in.
- Write a top-level `README` + `00-OVERVIEW` index, and a one-line privacy note about which files are sensitive.

---

## Output quality bar

The reports are the product. Make them genuinely insightful: specific (cite the host's real numbers and dates, computed at runtime — never any figure baked into this skill), narrative (eras and turning points, not a data dump), and honest (turning points and contradictions are the most valuable findings). Lead with the cross-source findings from Phase 6.5, each carrying number + date + source-join + a "so what". A reader should finish understanding themselves better. Avoid generic horoscope-speak — every sentence earned by something on *their* disk.

**This skill ships zero personal data.** Nothing about any specific person is hardcoded anywhere in it; every insight is derived live from the machine it runs on. Keep it that way.

## Reference & script index

- `references/macos.md` — macOS artifacts, exact queries, gotchas (timestamp `+978307200`, gzip Notes, WAL copy, TCC).
- `references/windows.md` — Windows artifacts (registry UserAssist/RecentDocs, Prefetch, `Zone.Identifier`, PowerShell history) + PowerShell snippets.
- `references/linux.md` — Linux artifacts (shell/python history, `recently-used.xbel`, journald, `~/.config`).
- `scripts/assess_system.sh` — cross-Unix system snapshot + OS detection + data-source inventory.
- `scripts/macos_extract.py` — macOS deep extractor (v2): consent flags (`--include-personal` off by default, `--dry-run`, `--source`), layers behavior/provenance/accounts/dev/installs/shell/spotlight/agents/notes → CSV/MD. Run with `-h` for the full contract.
- `scripts/correlate.py` — OS-agnostic cross-source engine → `correlations.json` + `.md` (crossover, era seams, adoption leaps, opt-in intentions).
- `scripts/diff_runs.py` — longitudinal diff between two runs + accumulating `behavior-history.csv`.
- `scripts/render_docs.py` — robust Markdown → Word + PDF (pandoc → textutil → LibreOffice; Chrome → wkhtmltopdf).
- `assets/report-template.md` — findings-first report skeleton.
- `CHANGELOG.md` — version history (currently v3.0).

---
*Maintained by Christian Torres (@HighTechTorres) · Sun Vision Digital LLC · MIT · self-audit only — see SECURITY.md.*
