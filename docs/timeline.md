# Design — Super-timeline (Phase 6)

*Status: v1 shipped (`scripts/timeline.py`, Phase 6). This doc is the spec + roadmap.*

## Why a script

Phase 6 used to be "merge every dated event into one chronology" with no tool behind it, so every run
rebuilt it by hand, differently each time. `timeline.py` makes the chronology deterministic: the same
extracts always give the same timeline, which matters for monthly re-runs (Phase 7.6) and keeps the
model's effort on *interpretation* rather than date wrangling.

## Inputs → one schema

Each source is optional; missing files are skipped and listed at the bottom of `timeline.md`.

| File | `source` | `event` | `detail` |
|---|---|---|---|
| `download-provenance.csv` | downloads | download | page/file host |
| `git-timeline.csv` | git | repo started / last commit | repo folder name |
| `installs.csv` | installs | tool adopted | tool |
| `photo-exif.csv` | photos | photo | camera (GPS never copied) |
| `app-usage.csv` | app-usage | app session | short app name |
| notes export | notes | note written | *(empty)* — `--include-personal` only |

Output: `timeline.csv` (`date,year,month,source,event,detail`, sorted) + `timeline.md`.

## What `timeline.md` reports (all FACT — counts, not readings)

- **Events per year × source** — the shape of the years at a glance.
- **Busiest months** — excluding short-window sources.
- **First / last activity per source** — when each kind of record begins and ends on this disk.
- **Inflection points** — per source, the biggest year-over-year rise and drop, ignoring swings
  where both years are under 5 events (noise floor).

The *meaning* of a swing ("this is when you stopped consuming and started building") is inference and
belongs in the report, labelled as such — usually cross-checked against `correlations.md`.

## Design decisions

- **Short-window sources aren't trends.** knowledgeC keeps ~2–4 weeks, `last` rotates, UserAssist
  only has recent focus. Those rows appear in the per-year table but are excluded from busiest-months
  and inflections, where a retention window would masquerade as a behavior change.
- **Notes contribute dates only.** Even with `--include-personal`, no title or body enters the
  timeline. It's a counting artifact that may be shared; quotes belong in Story Seeds and the report,
  under their own consent rules.
- **Stdlib only, extracts only.** No disk re-query, no network, OS-agnostic.

## Roadmap

- Feed `timeline.csv` into Strata's year chart and Story Seeds' detectors (today they read the raw
  extracts directly).
- New sources (calendar/email metadata, media history) should emit rows in this schema.
