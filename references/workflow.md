# Workflow detail — phase by phase

`SKILL.md` holds the ground rules, the phase order, and the one command per phase. This file holds the
detail: read the section for a phase when you reach it. Every command runs from the skill root, works
only on local files, and never touches the network.

---

## Phase 1 — Interview

Use AskUserQuestion if it's available; otherwise ask inline. Cover:

- **Purpose:** self-knowledge · founder/personal-brand story · résumé/portfolio · habits/productivity · curiosity.
- **Depth:** surface (browser/era level) or deep (behavioral + personal notes).
- **Privacy comfort:** there are two separate opt-ins, and both are **off by default**:
  - the **inner layer**: notes on health, money, relationships, and beliefs;
  - **photo location**: GPS, which amounts to a map of where they've been.
- **Audience:** just them, or something they'll share? If they'll share it, plan a redacted edition too.
- **Output formats:** Markdown (always kept), PDF, Word/.docx, in any combination. The default is
  Markdown + PDF. Carry the choice to Phase 8 as `--formats`.
- **Deliverables:** **Strata** (8.5), the **Handoff Pack** (9; offer it especially if the request mentions
  a new or old computer), and **Story Seeds** (7.7). Offer all three and build the ones they ask for.

Reflect the answers back in one line, then proceed.

### Reading the audience → lens + voice

Infer how this person makes sense of their world from their purpose, language, and audience. Let that
decide what the outputs **lead with**. Do it quietly and never name the model.

| Signal | Strata `--lens` | Report leads with | Voice |
|---|---|---|---|
| founder story, personal brand, résumé, "results" energy | `achievement` | output, rankings, wins | crisp, performance framing |
| community, wellness, relationships, sharing with people | `community` | the human story + rhythm | warm, first-person |
| how they work, workflows, "how it all connects" | `systems` | cross-source findings + era seams | analytical |
| self-knowledge, meaning, the long view, curiosity | `holistic` | the arc + turning points | reflective |
| unsure, mixed, strictly professional | `professional` | balanced | neutral |

Pick one lens as the primary. People are blends, so you can borrow one section's emphasis from a second
lens. Confirm the fit by showing it, not by interrogating them.

---

## Phase 5 — Deep-artifact extraction

All three extractors share one CLI contract, one output schema, and one consent model:

| OS | Command | Inner layer | OS-specific extras |
|---|---|---|---|
| macOS | `python3 scripts/macos_extract.py <out>` | Apple Notes | spotlight, launch agents |
| Linux | `python3 scripts/linux_extract.py <out>` | — (none) | recent files, autostart |
| Windows | `python scripts/windows_extract.py <out>` | Sticky Notes | recent, autostart (UserAssist ≈ knowledgeC) |

Run them in this order:
1. **`--dry-run` first.** It prints the inventory and exactly what each layer would extract, and writes
   nothing. Show this output to the user.
2. **Standard run:** just `<out>`. It covers behavior, provenance, accounts, dev/infra, installs, shell,
   and the OS extras. A consent banner states what's on.
3. **Inner layer (only on an explicit opt-in):** add `--include-personal`. The extractor refuses to write
   it under a cloud-sync root. Naming `notes` in `--layers` does **not** bypass this.
4. **Old drive or backup ("ghost self"):** add `--source <path>`, e.g. `/Volumes/Old/Users/<name>`,
   `/mnt/old/home/<name>`, or `D:\Users\<name>`. Live-only layers (registry, `/var/log`) skip themselves.
5. **Longitudinal:** add `--run-id YYYYMMDD` so the output goes to `<out>/run-YYYYMMDD/`.

What each layer yields:

| Layer | What it shows |
|---|---|
| behavior | daily rhythm |
| provenance | the consume→create signal (downloads + where they came from) |
| accounts | SaaS footprint (domains only, never passwords) |
| dev | git timeline, remotes |
| installs + shell | tool-adoption chronology (substrate leaps) |
| notes | the inner layer (opt-in) |

Behavioral retention is short: knowledgeC keeps about 2–4 weeks, and `last` rotates. Treat it as a
window, never as "how you've always worked".

**Photos (optional, cross-platform):** `python3 scripts/photo_exif.py <out>` (repeatable `--source DIR`)
writes `photo-exif.csv` and `photo-map.md`, with dates and camera only. `--include-location` adds GPS;
it's off by default and refused under a sync root. HEIC/RAW files need Pillow (+pillow-heif); without
it they're skipped, and the skip is reported. See `docs/photo-exif.md`.

Tell the user the **non-obvious** findings, not just the data.

---

## Phase 6 — Super-timeline

`python3 scripts/timeline.py <out>` writes `timeline.csv` (`date,year,month,source,event,detail`) and
`timeline.md`. The markdown covers events per year by source, the busiest months, first/last activity
per source, and the biggest year-over-year swings. Short-window sources (app-usage) appear per year but
are kept out of the "busiest" and "swing" sections. Note dates count only with `--include-personal`,
and even then it's dates alone, never titles or bodies. See `docs/timeline.md`.

Use it to tell the chronology: when the behavior changed, the peaks, and the consume→create flip.

---

## Phase 6.5 — Correlate

`python3 scripts/correlate.py <out>` writes `correlations.json` and `.md`:
- **consume→create crossover:** the year acquisition fell while output rose.
- **adoption leaps:** years with clustered new tooling.
- **era seams:** years where two or more sources shift together, i.e. the real chapter boundaries.
- **stated intentions:** only if a notes export exists (it only exists if the user opted in). Verdicts
  default to `unknown`. The user judges fulfillment; the skill never rates a person.

These findings lead the report.

---

## Phase 7 — Synthesis

Use `assets/report-template.md`, findings first. Specifically:
- Quote the user's own words for any inner-layer claim. Never dramatize, diagnose, or narrativize pain.
- The **redacted business-only edition** is the default shareable artifact. An edition that includes the
  inner layer needs the user's explicit confirmation.
- For Phase 4 era deep-dives and the Phase 7 reports, spawn parallel subagents (one per era) if
  subagents are available.

## Phase 7.5 — Adversarial review

Spawn a fresh subagent with no prior context. Give it the drafted report (the redacted edition) and the
raw extracts, and have it write `blind-spots.md` covering:
- over-reach: claims the data doesn't support;
- under-reach: patterns the report ignored;
- whether the data earns the most flattering sentence;
- three questions the portrait avoided.

Instruct it to be disagreeable on substance and to cite the data line or say nothing. **Make no
external-model API calls.** Running the review through a different provider is optional manual guidance
for the user, on the redacted edition only. Fold the result into "What this portrait is avoiding".

## Phase 7.6 — Longitudinal

Run monthly with `--run-id`. `python3 scripts/diff_runs.py <old_run> <new_run>` reports new and dropped
services, repo/commit growth, and new download sources. It also accumulates `behavior-history.csv`,
which a single snapshot can't produce.

## Phase 7.7 — Story Seeds

`python3 scripts/story_seeds.py <out> [--include-personal]` writes `story-seeds.json` and `.md`. Each
seed has a title, a window, evidence, and a prompt. The detectors are project origins, toolkit jumps,
research bursts, turning-point years, and photo memory-bursts and trips (trips only when location was
extracted). **The script never writes prose.** You write each seed's short first-person draft from its
evidence, labelling inference. The note detector is opt-in and quotes note titles verbatim. See
`docs/story-seeds.md`.

---

## Phase 8 — Package & export

- Put everything in one folder in Downloads named for the audit, with `raw-data/` holding the extracts.
- Render **only the chosen formats**: `python3 scripts/render_docs.py <folder> --formats pdf[,docx]`. It
  tries pandoc → textutil → LibreOffice for docx, and Chrome/Chromium → pandoc → wkhtmltopdf for PDF.
  Skip this step entirely if the user chose Markdown only.
- Add a top-level `README`, a `00-OVERVIEW` index, and a one-line note on which files are sensitive.

## Phase 8.5 — Strata

`python3 scripts/strata.py <out> --lens <lens>` writes a self-contained `strata.html`. The vendored
uPlot + Scrollama (MIT) libraries are **inlined**, so the page has no CDNs, fonts, trackers, or network
calls, and everything still shows with JS off.
- `--lens professional|achievement|community|systems|holistic` sets the section order, framing, and
  accent (see the Phase 1 table).
- `--accent <hex>` or `--palette orange|green|yellow|turquoise|blue` overrides the accent. Use one
  accent, never more.
- `--title`, `--subtitle`, `--out`.
- Privacy: note-derived seeds appear only with `--include-personal`, raw note bodies never appear, and
  GPS is never plotted. Treat the page as shareable. See `docs/strata.md`.

## Phase 9 — Handoff Pack

`python3 scripts/build_handoff_pack.py <out>` writes `context-pack/`, containing `profile.json`,
`PROFILE.md`, a drop-in `CLAUDE.md`, a provider-neutral `ABOUT-ME.md`, a `provisioning.md` checklist,
and a `README.md`. The personal layer stays **out** even if it was extracted. `--include-personal`
adds a `private/` section and is refused under a sync root. Tell the user to move the pack with a
*local* transfer, drop `CLAUDE.md` where their AI tooling reads memory, and work through
`provisioning.md`. See `docs/handoff-pack.md`.
