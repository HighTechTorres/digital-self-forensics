# 🪞 digital-self-forensics

**A Claude Code skill that turns your own computer into a mirror.** Point Claude at a machine you own and it reconstructs your eras, work rhythm, habits, and what mattered to you — from the browser profiles, downloads, notes, app-usage logs, git history, and infrastructure already on the disk — then writes it up as narrative report documents (Markdown + Word + PDF).

*Maintained by [@HighTechTorres](https://github.com/HighTechTorres) · Sun Vision Digital LLC · MIT licensed · self-audit only — see [SECURITY.md](SECURITY.md).*

> v1 found what's *in* each source. **v2 finds what's *between* them** — the year your behavior changed, the seams between chapters, the leaps where your tooling (and your capability) shifted.

---

## Privacy-first by design

This reads deeply personal data, so the defaults are conservative and enforced **in code**, not just prose:

- **Your machine only.** It's self-audit, not surveillance. Requests on someone else's device are declined.
- **100% local.** Nothing is uploaded, pushed, or sent to any API. All processing stays on disk.
- **Read-only.** Databases are copied before querying; originals are never modified.
- **The personal layer is OFF by default.** Your notes' contents are extracted only with an explicit `--include-personal` flag, and never written to a cloud-synced folder.
- **Ships zero personal data.** Nothing about any individual is hardcoded; every insight is computed at runtime on the host machine.

---

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
The skill triggers, interviews you (purpose, depth, privacy comfort, **and which output formats you want**), assesses the machine, requests any needed permissions, runs the audit, and drops the report in your Downloads in the formats you chose (Markdown always kept; PDF and/or Word as selected) — so you don't get a pile of files you'll never open.

---

## The flow (8 phases + v2 additions)

1. **Interview** — purpose, depth, privacy comfort, output format(s)
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

## What's in the box

```
digital-self-forensics/
├── SKILL.md                 # orchestration + the 8-phase process
├── CHANGELOG.md
├── scripts/
│   ├── assess_system.sh     # system snapshot + data-source inventory (macOS/Linux)
│   ├── macos_extract.py      # macOS deep extractor (consent flags, --source, --dry-run)
│   ├── correlate.py          # OS-agnostic cross-source engine → correlations.json/.md
│   ├── diff_runs.py          # longitudinal diff + accumulating behavior history
│   └── render_docs.py        # Markdown → Word + PDF (pandoc/textutil/LibreOffice/Chrome)
├── references/              # macos.md · windows.md · linux.md (artifact maps + queries)
├── assets/report-template.md
└── evals/                   # trigger-accuracy benchmark (19/19)
```

## Platform support

| Layer | macOS | Windows | Linux |
|---|---|---|---|
| Assess / inventory | ✅ script | 📄 reference | ✅ script |
| Deep extraction | ✅ `macos_extract.py` | 📄 PowerShell reference | 📄 reference |
| Correlate / diff / report | ✅ | ✅ | ✅ (OS-agnostic) |

Native Windows/Linux extractors are the v2.1 roadmap; today non-Mac users run the deep layer from the documented commands in `references/`.

## Responsible use & safety

This tool reads deeply personal data, so its guarantees are the point. In short: **it never sends anything anywhere** (no network, no telemetry, no third-party data collection), it's **read-only** on your files, the **personal layer is off by default in code**, and it's **for machines you own** — the skill is written to decline requests to examine someone else's device. It gives operators **zero** new ability to harvest their users' data; that's not what it's for. Full statement and how to verify the claims yourself: **[SECURITY.md](SECURITY.md)**.

## Author & license

Built and maintained by **Christian Torres** ([@HighTechTorres](https://github.com/HighTechTorres)) under **Sun Vision Digital LLC**. Licensed **MIT** — see [`LICENSE`](LICENSE). Use it, fork it, share it.

---

*Self-audit only. Keep the output off shared/synced drives unless you intend to — the personal layer is genuinely sensitive.*
