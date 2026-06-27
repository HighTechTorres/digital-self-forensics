# 🪞 digital-self-forensics

**Turn a computer you own into a mirror — then hand what it learns to your next one.**

[![License: MIT](https://img.shields.io/badge/License-MIT-2b5fa8.svg)](LICENSE)
[![Claude Code skill](https://img.shields.io/badge/Claude%20Code-skill-5b9bd5.svg)](https://claude.com/claude-code)
[![Local only](https://img.shields.io/badge/data-100%25%20local-2ea44f.svg)](SECURITY.md)
[![Platform](https://img.shields.io/badge/macOS%20%C2%B7%20Windows%20%C2%B7%20Linux-supported-444.svg)](#platform-support)
[![Version](https://img.shields.io/badge/version-3.2-15233a.svg)](CHANGELOG.md)

A Claude Code skill that reads the years of browser history, downloads, notes, git history, and
app-usage already sitting on a machine you own, and reconstructs **who you've been, how you work,
and what mattered to you** — then turns that into things you can actually use: narrative reports,
a portable **Handoff Pack** that seeds your next computer (and its AI) with your context, and
journal-ready **stories** from your own life *(roadmap)*.

*Maintained by [@HighTechTorres](https://github.com/HighTechTorres) · Sun Vision Digital LLC · MIT · self-audit only — see [SECURITY.md](SECURITY.md).*

> 👀 **See it first:** a fictional, synthetic-data [**sample report**](examples/sample-report.md)
> shows what a run produces — without anyone's real data.

---

## Contents

- [Why this exists](#why-this-exists)
- [Who it's for & what you'll get](#who-its-for--what-youll-get)
- [Privacy-first by design](#privacy-first-by-design)
- [Quick start](#quick-start)
- [The flow](#the-flow)
- [What it produces](#what-it-produces)
- [What's in the box](#whats-in-the-box)
- [Platform support](#platform-support)
- [Roadmap](#roadmap)
- [Responsible use & safety](#responsible-use--safety)
- [Author & license](#author--license)

## Why this exists

Since personal computers became *personal*, our machines have quietly recorded the most honest
record of our lives that exists anywhere — not the curated version we post, but what we actually
read, built, chased, and spent our hours on. Then we get a new computer, drag over a folder or
two, and leave all of that value behind, never to be opened again.

This skill goes in and **extracts that value**: it mines the on-disk artifacts for self-insight,
packages your context so a new machine starts out knowing you, and surfaces the small stories your
disk remembers but you've forgotten. The audit stops being a one-time curiosity and becomes
something with a forward use.

## Who it's for & what you'll get

**For you if** you're moving to a new computer, cleaning out an old laptop, building a personal-brand
or founder story, trying to understand your own habits and productivity, or just curious what your
machine knows about you.

**You'll get:**
- 📄 **A narrative report** — your eras, work rhythm, turning points, and a portrait of how you
  operate, grounded in real numbers from *your* disk (not horoscope-speak).
- 🎒 **A Handoff Pack** — a portable bundle (`profile.json`, a drop-in `CLAUDE.md`/`ABOUT-ME.md`,
  and a re-provisioning checklist) that seeds your next machine and its AI assistant with your
  context from day one.
- 📖 **Story Seeds** *(roadmap)* — journal-ready entries: a date, the evidence, a draft in your
  voice, and a prompt — the moments your disk remembers that you'd want to keep.

## Privacy-first by design

This reads deeply personal data, so the defaults are conservative and enforced **in code**, not just prose:

- **Your machine only.** It's self-audit, not surveillance. Requests on someone else's device are declined.
- **100% local.** Nothing is uploaded, pushed, or sent to any API. All processing stays on disk.
- **Read-only.** Databases are copied before querying; originals are never modified.
- **The personal layer is OFF by default.** Your notes' contents are extracted only with an explicit `--include-personal` flag, and never written to a cloud-synced folder. The Handoff Pack excludes it by default too — so it's safe to carry between machines.
- **Ships zero personal data.** Nothing about any individual is hardcoded; every insight is computed at runtime on the host machine. (Even the [sample report](examples/sample-report.md) is synthetic.)

## Quick start

**Requires:** [Claude Code](https://claude.com/claude-code) + Python 3. On macOS, grant your terminal **Full Disk Access** for the behavioral/personal layers (System Settings → Privacy & Security → Full Disk Access → add Terminal → restart it).

**Install** (either way):
```bash
# A) one-file package
#   install digital-self-forensics.skill via Claude Code

# B) from source
cp -R digital-self-forensics ~/.claude/skills/
```

**Run** — in a fresh Claude Code session, just say:
```
Audit my computer and tell me what it says about how I work and what mattered to me.
```
The skill triggers, interviews you (purpose, depth, privacy comfort, output formats, and which
deliverables you want), assesses the machine, requests any needed permissions, runs the audit, and
drops the results in your Downloads — in the formats you chose, optionally with a Handoff Pack to
seed your next computer.

## The flow

1. **Interview** — purpose, depth, privacy comfort, output format(s), deliverables
2. **Assess** — detect OS, snapshot the machine, inventory data sources
3. **Permissions** — walk you through Full Disk Access (macOS) / elevation notes (Win/Linux)
4. **Persona census** — map browser profiles to life/work eras → per-era deep dives
5. **Deep extraction** — behavior, downloads, accounts, dev/infra, installs, shell, agents (+ notes, opt-in)
6. **Super-timeline** — merge every dated event into one chronology
6.5 **Correlate** — the headline: consume→create crossover, era seams, adoption leaps
7. **Synthesize** — findings-first report (+ redacted business-only edition)
7.5 **Adversarial review** — a fresh-context agent challenges the portrait (local only)
7.6 **Longitudinal** — re-run monthly and diff over time
8. **Package & export** — one folder, in your chosen formats (Markdown + PDF/Word as selected), with an index
9. **Handoff Pack** *(optional)* — a portable bundle to seed your next machine and its AI assistant

## What it produces

| Output | Built for | What it is |
|---|---|---|
| **Reports** | you, to read | Findings-first narrative: eras, turning points, a portrait of how you operate |
| **Handoff Pack** | your next machine | `profile.json` + `CLAUDE.md`/`ABOUT-ME.md` + a re-provisioning checklist ([design](docs/handoff-pack.md)) |
| **Story Seeds** *(roadmap)* | your journal | Journal-ready story candidates mined from your own data ([design](docs/story-seeds.md)) |

## What's in the box

```
digital-self-forensics/
├── SKILL.md                  # orchestration + the 9-phase process
├── CHANGELOG.md
├── scripts/
│   ├── assess_system.sh      # system snapshot + data-source inventory (macOS/Linux)
│   ├── macos_extract.py      # macOS deep extractor (consent flags, --source, --dry-run)
│   ├── correlate.py          # OS-agnostic cross-source engine → correlations.json/.md
│   ├── diff_runs.py          # longitudinal diff + accumulating behavior history
│   ├── render_docs.py        # Markdown → Word and/or PDF (--formats pdf,docx)
│   └── build_handoff_pack.py # OS-agnostic → portable context-pack/ for a new machine
├── references/               # macos.md · windows.md · linux.md (artifact maps + queries)
├── docs/                     # handoff-pack.md · story-seeds.md (design specs)
├── assets/report-template.md
├── examples/sample-report.md # synthetic sample of the output
└── evals/                    # trigger-accuracy benchmark
```

## Platform support

| Layer | macOS | Windows | Linux |
|---|---|---|---|
| Assess / inventory | ✅ script | 📄 reference | ✅ script |
| Deep extraction | ✅ `macos_extract.py` | 📄 PowerShell reference | 📄 reference |
| Correlate / report / Handoff Pack | ✅ | ✅ | ✅ (OS-agnostic) |

Native Windows/Linux extractors are on the roadmap; today non-Mac users run the deep layer from the documented commands in `references/`.

## Roadmap

- **Native Windows/Linux extractors** — biggest reach unlock (mirroring `macos_extract.py`).
- **Story Seeds** — journal mining ([spec](docs/story-seeds.md)).
- **Richer sources** — photo EXIF (a life-map), calendar/email metadata, media & reading history — all opt-in.
- **Handoff Pack v2** — dotfile capture, a review-before-run `setup.sh` generator, preference inference, an encryption option.
- **Ask-your-own-data** — a local Q&A mode over the extracts.

See [CONTRIBUTING.md](CONTRIBUTING.md) — native extractors and new sources are the most valuable contributions.

## Responsible use & safety

This tool reads deeply personal data, so its guarantees are the point. In short: **it never sends anything anywhere** (no network, no telemetry, no third-party data collection), it's **read-only** on your files, the **personal layer is off by default in code**, and it's **for machines you own** — the skill is written to decline requests to examine someone else's device. It gives operators **zero** new ability to harvest their users' data; that's not what it's for. Full statement and how to verify the claims yourself: **[SECURITY.md](SECURITY.md)**.

## Author & license

Built and maintained by **Christian Torres** ([@HighTechTorres](https://github.com/HighTechTorres)) under **Sun Vision Digital LLC**. Licensed **MIT** — see [`LICENSE`](LICENSE). Use it, fork it, share it.

---

*Self-audit only. Keep the output off shared/synced drives unless you intend to — the personal layer is genuinely sensitive.*
