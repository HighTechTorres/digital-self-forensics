# Changelog — digital-self-forensics

## v3.0
Attribution + accountability release (no behavioral change to the audit itself).
- Added **`SECURITY.md`** — an explicit, verifiable statement of the security posture: no
  network/telemetry/exfiltration, read-only, consent-off-by-default, not for others' devices,
  and a clear "this gives operators zero new ability to harvest their users' data."
- Attribution: maintained by **Christian Torres ([@HighTechTorres](https://github.com/HighTechTorres))**
  under **Sun Vision Digital LLC**; `LICENSE` copyright holder updated accordingly (MIT).
- README gains an "Author & license" and a "Responsible use & safety" section.
- Still ships **zero personal data** beyond the maintainer's public attribution.

## v2.0
The disk goes from a *retrieval target* to a *reasoning substrate*: v1 found what's **in** each
source; v2 finds what's **between** them. Backward-compatible with v1 extract folders.

**Safety & consent (the foundation)**
- **Personal layer is now OFF by default in code**, not just in prose. Apple Notes bodies are
  extracted only with `--include-personal`. `--no-notes` is kept as a deprecated no-op.
- **`--dry-run`** prints the inventory + extraction plan and writes nothing.
- **Consent banner** prints before anything is touched, stating exactly which layers run and
  whether the inner layer is enabled.
- **Cloud-sync guard**: the extractor refuses to write the inner layer under Dropbox / iCloud /
  OneDrive / Google Drive / Box roots.
- **No personal data ships** in this repo — everything is computed at runtime on the host.

**New capability**
- **`correlate.py`** (WI-1) — OS-agnostic correlation engine over the local extract CSVs:
  consume→create crossover, adoption leaps, era seams (≥2 sources shifting together), and
  (personal-only, conservative) stated-intention extraction. Emits `correlations.json` + `.md`.
- **New extractor layers** (WI-4): `installs` (tool-adoption chronology), `shell` (terminal
  tool frequency), `spotlight` (most-used docs), `agents` (LaunchAgents = automated cognition).
- **`--source PATH`** (WI-5, experimental) — run against an old drive / Time Machine / migrated
  tree instead of `~`, for cross-machine "ghost self" reconstruction. Paths resolve relative to
  the source root; the live `~` is never read.
- **`diff_runs.py`** (WI-3, experimental) — compare two runs (new/dropped SaaS, repo/commit
  growth, new download sources) and **accumulate** app-usage into a growing
  `behavior-history.csv`, so monthly re-runs build the longitudinal rhythm a single ~2–4 week
  knowledgeC snapshot can't show.
- **Findings-first report** (WI-7) — the report leads with cross-source findings (each: number
  + date + source-join + "so what"); per-layer detail moves to appendices; adds a
  "What this portrait is avoiding" section.
- **Adversarial review phase** (WI-2) — a fresh-context local subagent challenges the portrait
  (over-reach, under-reach, the most flattering sentence, 3 avoided questions). **No automatic
  external-model calls** — cross-provider diffing is documented manual guidance only, on the
  redacted edition, never the inner layer.

**Cross-platform note**
- The correlate / diff / report layers are OS-agnostic (they read CSVs). Deep extraction is
  still macOS-native (`macos_extract.py`); Windows/Linux run from the documented commands in
  `references/`. Native Win/Linux extractors are the v2.1 roadmap.

## v1.0
Initial release: OS detection + assessment, browser-profile/era census, deep-artifact pass
(behavior, provenance, notes, accounts, dev/infra), super-timeline, Markdown→Word/PDF export.
Trigger-accuracy benchmark 19/19.
