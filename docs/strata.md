# Design — Strata (the interactive data portrait)

*Status: v1 shipped (`scripts/strata.py`, Phase 8.5). This doc is the spec + roadmap.*

## The idea

**Strata** turns the whole audit into a single, beautiful, *interactive*, *offline* HTML page —
the layers and eras your machine has quietly recorded, rendered as a portrait you'd actually want
to share or frame. The skill's documents are clinical (findings, appendices); Strata is the
showpiece on top of the same data substrate (the extract CSVs, `correlations.json`,
`story-seeds.json`, `photo-exif.csv`).

The name evokes geological **strata** — the sediment of a digital life, with the era-seams as the
visible boundaries between chapters.

## Design language (modern personal-data-visualization)

Drawn from the established personal-data-visualization tradition and Tufte's data-integrity rules:

- **The data drives the design.** Sections render only when their data exists; nothing is decorative.
- **High data-ink ratio / restraint.** White ground, near-black ink (`#1a1a1a`), one accent color,
  hairline rules, generous whitespace. No gradients, no chrome.
- **Compressed typography as architecture.** Big tabular-number callouts, a monospace face for every
  data label, uppercase compressed headings.
- **Small multiples + macro view.** Per-year series and a daily-rhythm chart so the eye compares
  like with like; the cross-source findings are the *lead*, the era-seam timeline frames the chapters.
- **Narrative reveal.** Sections animate in on scroll — a guided, in-order read rather than a wall.

## A restrained accent system

Named single-accent palettes let the accent match the audience — **one** accent only, never a
rainbow: `orange` (achievement), `green` (community), `yellow` (systems), `turquoise` (holistic),
`blue` (default, neutral/professional). Or pass any `--accent <hex>`.

## Audience lenses (`--lens`)

The deepest way Strata fits the person is not color but **emphasis** — *who the report is for*
changes what it leads with, the framing copy, and the accent. `--lens` selects an audience preset
(plain names, no jargon in any output) that reorders the sections accordingly:

| Lens | Leads with | Framing · accent |
|---|---|---|
| `professional` (default) | balanced order | neutral · blue |
| `achievement` | rankings + output, then the year chart | results/performance · orange |
| `community` | story seeds + daily rhythm | warm, human story · green |
| `systems` | cross-source findings + era seams | analytical, how-it-connects · yellow |
| `holistic` | the arc: findings → seams → years → seeds | reflective, long view · turquoise |

The ordering reflects what each audience's **center of gravity** values most (informed by
developmental value-systems models): output-driven readers want results first; community-minded
readers want the human story first; systems thinkers want the relationships between sources; the
long-view reader wants the arc. The skill infers the lens during the Phase-1 interview from the
user's purpose and audience — a soft inference applied by *showing*, never by labeling anyone.
`--accent`/`--palette` override the lens's accent if needed.

## Interactivity — vendored, inlined, offline

The skill's #1 rule is **100% local, never transmit** — so Strata does **not** load anything from a
CDN. Two small MIT-licensed libraries are **vendored into the skill** (`assets/vendor/`) and
**inlined into the output HTML** at generation time:

- **uPlot** (`assets/vendor/uPlot.iife.min.js` + `.min.css`) — a fast, tiny charting library; powers
  the interactive "shape of your years" hero (hover the multi-series year chart).
- **Scrollama** (`assets/vendor/scrollama.min.js`) — drives the scroll-reveal narrative.

Because they're inlined, the result is a single self-contained file (~60–80 KB) that opens with **no
network connection** — no CDNs, web fonts, or trackers. Progressive enhancement: with JavaScript
disabled, every section is fully visible and the year data falls back to inline SVG small multiples.
Licenses ship alongside the code (`assets/vendor/*.LICENSE`).

## Privacy

A publication layer, conservative like the redacted edition:
- Personal/inner layer **excluded by default**. `--include-personal` folds in note-derived story
  seeds only — **raw note bodies are never embedded**.
- Photo **GPS is never plotted** — counts only (photos by year, geotagged count, camera eras).
- Everything is computed locally; nothing is transmitted.

## Roadmap (v2+)

1. **Stepper scrollytelling** — Scrollama "sticky graphic" steps that scrub a single chart through
   states (consume→create crossover animated), not just reveal-on-enter.
2. **Per-era strata** — a small-multiple panel per era/seam, linked from the masthead.
3. **Brand tokens** — accept a CSS/brand token file for personal- or org-branded editions.
4. **Print/PDF polish** — refine `@media print` so Strata doubles as a press-ready PDF via the
   existing `render_docs.py` Chrome path.
