---
name: digital-self-forensics
description: Audit the user's OWN computer to mine it for self-insight — reconstruct their eras, work rhythm, habits, and what mattered to them from on-disk artifacts (browser profiles, downloads, notes, app-usage logs, git history, photos, infrastructure), then produce narrative reports, an interactive offline data portrait, and a portable context pack for their next machine. Use this whenever the user wants to "audit my computer," "see what my machine says about me," analyze their old/new laptop for personal or professional insights, profile their own digital habits, build a personal timeline from their data, carry their context to a new computer, or do self-directed digital self-discovery on a machine they own. Trigger even without the word "forensics" — "what does my computer know about me," "analyze my Mac/PC," "extract insights from my old laptop," and "profile how I work from my data" all qualify. Correlates across sources (the year behavior changed, era seams, adoption leaps), supports monthly re-runs, and reconstructs a "ghost self" from an old drive. Works on macOS, Windows, and Linux. Not for anyone else's device.
---

# Digital Self-Forensics

Turn the user's own computer into a mirror. Years of browser profiles, downloads, notes, code, photos, and behavioral logs sit on the disk: an honest record of who they've been, what they chased, and how they actually spend their time. This skill reads those artifacts and synthesizes them into **narrative insight about the user**.

The bundled scripts encode the parts that are easy to get wrong: timestamp math, decompressing Notes, copying locked databases, cross-source correlation, and rendering. That makes each run fast and repeatable. All scripts are Python standard library only.

## Non-negotiable ground rules (state these to the user up front)

- **Own machine only.** This is self-audit. If the user asks to run it on someone else's device (a partner, employee, child, or client), decline. That's surveillance, not self-discovery.
- **100% local.** Never upload, push, sync, or transmit their data. Make no external API calls with their personal content.
- **Read-only on sources.** Copy databases to temp before querying. Never modify the originals.
- **The user controls depth.** The inner layer (notes on health, money, relationships, beliefs) and photo location are separate opt-ins, **off by default in code**. Ask about each and honor the answer.
- **Flag inference vs. fact.** Ground every claim in real data, and label guesses as guesses.

## Quick start (the canonical chain)

```bash
OUT=~/Downloads/self-audit                         # local, NOT under Dropbox/iCloud/OneDrive
python3 scripts/macos_extract.py "$OUT" --dry-run  # or linux_extract.py / windows_extract.py
python3 scripts/macos_extract.py "$OUT"            # + --include-personal ONLY on explicit opt-in
python3 scripts/photo_exif.py "$OUT"               # optional; + --include-location only on opt-in
python3 scripts/timeline.py "$OUT"                 # Phase 6  → timeline.csv/.md
python3 scripts/correlate.py "$OUT"                # Phase 6.5 → correlations.json/.md
python3 scripts/story_seeds.py "$OUT"              # Phase 7.7 → story-seeds.json/.md
python3 scripts/strata.py "$OUT" --lens professional   # Phase 8.5 → strata.html
python3 scripts/build_handoff_pack.py "$OUT"       # Phase 9  → context-pack/
python3 scripts/render_docs.py "$OUT" --formats pdf    # Phase 8 (skip if Markdown-only)
```

Every downstream script is OS-agnostic, reads only the extracts, and degrades gracefully when a source is missing.

## Process

Run the phases in order. Show results and check in between them, because this is a guided experience and the user's reactions improve the output. **Detail for each phase is in `references/workflow.md`; read the section for a phase when you reach it.**

1. **Interview.** Capture purpose, depth, the two privacy opt-ins, audience, output formats (default Markdown + PDF), and deliverables (Strata, Handoff Pack, Story Seeds). Then infer the **audience lens** (achievement · community · systems · holistic · professional) from how they talk about their purpose. It sets the report's voice and Strata's `--lens`. Apply it by *showing*, and never name the model. Reflect their answers back in one line.
2. **Detect the OS and assess the machine.** Run `scripts/assess_system.sh` on macOS/Linux; on Windows, use the PowerShell in `references/windows.md`. Read the OS reference (`references/macos.md` | `windows.md` | `linux.md`). Report the hardware/OS and a prioritized list of the richest artifact sources that exist on *this* machine.
3. **Request permissions.** On macOS, the behavior and Notes layers need Full Disk Access: *System Settings → Privacy & Security → Full Disk Access → add the terminal → restart it*. Verify by reading one gated database before continuing. Windows and Linux usually need nothing for the user's own files.
4. **Persona/era census.** Map every browser profile (name, email, bookmark folders, top domains, history range, searches) to a job, business, or era, copying `Bookmarks`/`History` to temp first. If the user doesn't use profiles, use Downloads/Documents/shell clusters instead. Write a second-person deep-dive for each meaningful era; if subagents are available, write them in parallel.
5. **Deep extraction.** Run the native extractor with `--dry-run` first, then for real. Add `--include-personal` only on an explicit opt-in, `--source <path>` for an old drive, and `--run-id` for monthly runs. Photos are optional and cross-platform. Then tell the user the non-obvious findings.
6. **Super-timeline.** Run `scripts/timeline.py` to merge every dated event into one chronology and surface the inflection points.
6.5. **Correlate.** Run `scripts/correlate.py` to find the consume→create crossover, adoption leaps, era seams, and, only if notes were extracted, stated intentions (verdict `unknown`; the user judges). **These findings lead the report.**
7. **Synthesis.** Write the complete report from `assets/report-template.md` (findings first, a portrait paragraph last) plus the timeline doc. Quote the user's own words for anything from the inner layer. The **redacted business-only edition is the default shareable artifact**.
7.5. **Adversarial review.** Have a fresh, context-free subagent write `blind-spots.md` covering over-reach, under-reach, whether the data earns the flattering sentence, and three avoided questions. Make no external-model API calls.
7.6. **Longitudinal (optional).** Run monthly with `--run-id`; `scripts/diff_runs.py <old> <new>` reports what changed and accumulates `behavior-history.csv`.
7.7. **Story Seeds (optional).** `scripts/story_seeds.py` supplies the evidence and prompts; **you** write each short first-person draft. Never invent or dramatize.
8. **Package & export.** Use one folder in Downloads with `raw-data/`, a README, a `00-OVERVIEW` index, and a sensitivity note. Render only the formats the user chose.
8.5. **Strata (optional).** `scripts/strata.py` builds a self-contained, interactive, **offline** HTML data portrait. Vendored libraries are inlined and there are no network calls. It's shareable by default, with no note bodies and no GPS.
9. **Handoff Pack (optional).** `scripts/build_handoff_pack.py` builds `context-pack/` with `profile.json`, a drop-in `CLAUDE.md`, `ABOUT-ME.md`, and a provisioning checklist. The personal layer stays out unless the user explicitly asks.

Every script that can write a sensitive layer **refuses under a cloud-sync folder**. If one refuses, pick a local output directory; never work around the refusal.

## Output quality bar

The reports are the product. Make them:
- **specific:** cite this host's real numbers and dates, computed at runtime and never baked in;
- **narrative:** eras and turning points, not a data dump;
- **honest:** contradictions and turning points are the most valuable findings.

Lead with the Phase 6.5 findings, each carrying a number, a date, the source join, and a "so what". Avoid horoscope-speak: every sentence should be earned by something on *their* disk.

**This skill ships zero personal data.** Nothing about any specific person is hardcoded anywhere in it, and every insight is derived live from the machine it runs on. Keep it that way.

## Reference & script index

- `references/workflow.md`: per-phase detail (interview + lens table, extractor flags and layers, every optional phase).
- `references/macos.md` · `windows.md` · `linux.md`: artifact maps, exact queries, and gotchas (Apple epoch `+978307200`, gzip Notes, WAL copy, TCC, FILETIME, UserAssist ROT13).
- `scripts/assess_system.sh`: Unix system snapshot, OS detection, and data-source inventory.
- `scripts/macos_extract.py` · `linux_extract.py` · `windows_extract.py`: native deep extractors with one contract (`--dry-run`, `--include-personal`, `--layers`, `--source`, `--run-id`; exit 0 ok · 2 refused or bad args · 3 source not found).
- `scripts/photo_exif.py`: photo life-map from EXIF. GPS is opt-in (`--include-location`).
- `scripts/timeline.py`: the super-timeline (Phase 6).
- `scripts/correlate.py`: the cross-source findings engine (Phase 6.5).
- `scripts/diff_runs.py`: longitudinal diff plus the accumulating behavior history.
- `scripts/story_seeds.py`: story-seed evidence and prompts (the model writes the drafts).
- `scripts/strata.py`: the interactive offline portrait (`--lens`, `--accent`/`--palette`).
- `scripts/build_handoff_pack.py`: the portable `context-pack/` for the next machine.
- `scripts/render_docs.py`: Markdown → PDF/docx, auto-detecting the available tools.
- `scripts/_common.py`: shared helpers, including the hardened cloud-sync guard.
- `assets/report-template.md`: the findings-first report skeleton. `assets/vendor/`: uPlot + Scrollama (MIT), inlined by Strata.
- `docs/`: design specs for the timeline, Strata, Story Seeds, the Handoff Pack, and photo EXIF.
- `CHANGELOG.md`: version history (currently v3.8).

---
*Maintained by Christian Torres (@HighTechTorres) · Sun Vision Digital LLC · MIT · self-audit only — see SECURITY.md.*
