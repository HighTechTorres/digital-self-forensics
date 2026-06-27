# Changelog — digital-self-forensics

## v3.6.1
Privacy hardening (from code review).
- **Photo EXIF sync-root guard is now case-insensitive + segment-based.** `under_sync_root` in
  `photo_exif.py` used case-sensitive substring matching, so on case-insensitive filesystems a
  synced output path with different casing (e.g. `C:\Users\me\onedrive\out`) could slip past and
  let `--include-location` write GPS under a synced root. It now matches lowercased path *segments*
  across both separators and catches provider-prefixed enterprise folders (`OneDrive - Contoso`)
  without false-matching `OneDriveBackup` — the same robust matcher used by `build_handoff_pack.py`.
  The sync-root list is also broadened (Box Sync, Nextcloud, ownCloud, iCloudDrive, …).

## v3.6
The signature artifact — **Strata**, an interactive data portrait.
- **New: `scripts/strata.py` (Phase 8.5)** — renders the extracts into **Strata**, a single,
  self-contained, *interactive*, *offline* HTML portrait of your digital life: big callout numbers,
  an interactive multi-series "shape of your years" chart, a daily-rhythm chart, ranked bars, the
  cross-source findings as the lead, an era-seam timeline, story-seed cards, and a scroll-reveal
  narrative. The data drives the design; sections appear only when their data exists.
- **Interactivity is vendored + inlined, never fetched.** Two small MIT libraries — **uPlot**
  (charts) and **Scrollama** (scroll reveal) — are vendored into `assets/vendor/` and inlined into
  the output, so the page is fully interactive yet **opens offline with no CDNs, fonts, trackers, or
  network calls**. Progressive enhancement: JS-off still shows everything (SVG fallback). ~60–80 KB.
- **Design controls:** `--title`/`--subtitle`, single accent via `--accent <hex>` or
  `--palette <orange|green|yellow|turquoise|blue>`.
- **Privacy:** personal layer excluded by default — note-derived story seeds only with
  `--include-personal`, never raw note bodies; photo GPS never plotted (counts only).
- Docs: `docs/strata.md`. New `assets/vendor/` (uPlot, Scrollama + their MIT licenses). Interview
  "deliverables" now offers report + Strata + Handoff Pack.

## v3.5
Photos as a source — the richest dated record most people own.
- **New: `scripts/photo_exif.py`** — cross-platform photo life-map from EXIF. Emits
  `photo-exif.csv` (taken/year/month/lat/lon/camera) + `photo-map.md` (photos by year, camera
  eras, location clusters). **Pure stdlib** built-in JPEG/TIFF EXIF reader (validated on a
  synthesized EXIF image incl. GPS N/S/E/W sign handling); uses Pillow as a faster, broader-format
  fast-path if it's installed.
- **Location is opt-in.** By default only dates + camera are written; `--include-location` adds
  GPS and refuses to write coordinates under a cloud-sync root.
- **HEIC/RAW/PNG flow through the Pillow path** when Pillow (+pillow-heif) is installed — they're
  hard-skipped only when Pillow is unavailable or a file yields no usable EXIF (reported, not
  silent). The reader in use (built-in vs Pillow) is printed.
- **Story Seeds gains photo detectors** — memory-burst months and (when location was extracted)
  trips, surfaced as journal-ready seeds.
- Interview "privacy comfort" now treats the inner layer and photo location as two distinct
  opt-ins. Same safety posture: local-only, read-only, consent off by default.

## v3.4.1
Security/consent hardening (from code review — no behavioral change to a correctly-used run).
- **Handoff Pack sync-root guard is now cross-platform.** `under_sync_root` matched Unix paths
  only, so `--include-personal` could write the private layer under a Windows synced folder
  (e.g. `C:\Users\me\OneDrive\…`). It now matches path segments case-insensitively across both
  separators, catches **provider-prefixed enterprise folders** (`OneDrive - Contoso`,
  incl. the macOS `CloudStorage/OneDrive - Org` layout) without false-matching names like
  `OneDriveBackup`, and the sync-root list is broader (Box, Nextcloud, ownCloud, iCloudDrive, …).
- **`--layers notes` no longer bypasses consent.** In the macOS and Windows extractors, naming a
  personal layer via `--layers` ran it even without `--include-personal`. Personal layers are now
  dropped (with a printed note) unless `--include-personal` is set.
- **Linux `installs` no longer reads the host `/var/log` under `--source`.** During an
  old/migrated-drive run it would attribute this machine's package history to the source; it now
  skips with an explicit live-only message (matching the other live-only layers).

## v3.4
Native Windows + Linux extractors — deep extraction is no longer Mac-only.
- **New: `scripts/linux_extract.py`** — layers behavior (`last` session rhythm), provenance
  (Chrome/Firefox history + `recently-used.xbel`), accounts (Chrome Login Data + Firefox
  logins.json), dev (git), installs (dpkg/rpm/pacman/flatpak/snap with dates), shell, recent,
  autostart. No inner layer (no notes equivalent on Linux).
- **New: `scripts/windows_extract.py`** (pure Python + stdlib `winreg`) — layers behavior
  (UserAssist, the knowledgeC analog with focus time), provenance (NTFS `Zone.Identifier` ADS),
  accounts, dev (git), installs (registry Uninstall + InstallDate), shell (PSReadLine), recent,
  autostart (Startup + Run keys), and an **opt-in Sticky Notes inner layer**.
- **Identical contract + output schema** to `macos_extract.py`, so correlate / Story Seeds /
  Handoff Pack / export all work unchanged on every OS. Registry/live-only layers auto-skip under
  `--source` (old-drive mode).
- **Cross-platform inner layer:** downstream tools now recognize both `Apple-Notes-Full-Export.md`
  (macOS) and `notes-export.md` (Windows Sticky Notes).
- Same safety posture: local-only, read-only, consent off by default, cloud-sync guard on the
  inner layer.

## v3.3
Story Seeds — the audit's emotional counterpart to the Handoff Pack.
- **New: Story Seeds (Phase 7.7).** `scripts/story_seeds.py` mines the local extracts for
  journal-ready *moments* — project origins (first-commit dates), toolkit-jump years, research
  bursts (download clusters), and turning-point years (era seams). Each seed carries a title, a
  window, the on-disk **evidence**, and a **prompt**; the skill writes the first-person draft from
  that evidence (the script never invents prose). Emits `story-seeds.json` + `story-seeds.md`.
- **Opt-in note detector** (`--include-personal`) quotes the user's own note titles **verbatim**,
  under the same consent rule as the rest of the personal layer.
- `docs/story-seeds.md` updated from spec to shipped; interview "deliverables" question and the
  README now cover both Story Seeds and the Handoff Pack.

## v3.2
The audit gains a *forward* use: seed your next machine.
- **New: the Handoff Pack (Phase 9).** `scripts/build_handoff_pack.py` turns the local extracts
  into a portable `context-pack/` — `profile.json` (structured source of truth), `PROFILE.md`, a
  drop-in **`CLAUDE.md`** for Claude Code on the new machine, a provider-neutral **`ABOUT-ME.md`**,
  a **`provisioning.md`** re-provisioning checklist, and a seed `README.md`. OS-agnostic (reads the
  same extracts `correlate.py` does). The personal layer is left OUT by default so the pack is safe
  to move; `--include-personal` adds a marked `private/` section and refuses cloud-sync roots.
- **Interview** now asks which deliverables the user wants (report and/or Handoff Pack).
- **Docs:** added `docs/handoff-pack.md` (shipped) and `docs/story-seeds.md` (roadmap — journal
  mining). README reframed around the fuller vision: mirror → handoff → stories.
- **Repo health:** added `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue/PR templates, and a
  synthetic `examples/sample-report.md`.
- No change to the safety posture: still local-only, read-only, consent-off-by-default, zero
  personal data shipped.

## v3.1
Output-format control (less file clutter, same audit).
- **New Phase-1 interview question: output format(s).** The user picks any combination of
  **Markdown / PDF / Word (.docx)** up front, so a run only emits the rendered docs they'll
  actually open instead of every format for every edition. Default when unspecified is
  **Markdown + PDF**.
- **`render_docs.py` gains `--formats pdf,docx`** (and `--pdf` / `--docx` shortcuts). Markdown
  stays the always-kept working source; the flag only governs which *rendered* formats are
  produced. Default with no flag remains both (back-compatible). A `md`/`markdown` value in
  `--formats` is accepted and ignored (it's the source, not a render target).
- **Phase 8** now renders only the chosen formats, and **skips rendering entirely** when the
  user picked Markdown only.
- No change to extraction, correlation, or the safety posture.

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
