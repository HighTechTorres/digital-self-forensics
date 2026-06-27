# Design — The Handoff Pack

*Status: v1 shipped (`scripts/build_handoff_pack.py`). This doc is the spec + roadmap.*

## The idea

The reports (Phase 7) are written for a **human to read**. The Handoff Pack is written for a
**machine to ingest**. When you move to a new computer, you usually drag over a few folders and
never open them again — the *value* in your old machine (how you work, what you build, the tools
you reach for, who you are online) stays trapped. The Handoff Pack extracts that value into a
small, portable bundle that gives a fresh machine — and the AI assistant running on it — instant
context instead of a cold start.

It turns a one-time audit into something with a forward use: **seed the next machine.**

## What it produces

Built by `build_handoff_pack.py` from the local extracts (OS-agnostic; reads the same
CSV/TXT/JSON `correlate.py` reads — never re-queries the disk, never transmits):

| File | For | Contents |
|---|---|---|
| `profile.json` | machines | Structured source-of-truth: rhythm, tooling, projects, services, eras |
| `PROFILE.md` | humans | The same profile, readable |
| `CLAUDE.md` | Claude Code on the new machine | Drop-in memory: how I work, what I build, defaults to assume |
| `ABOUT-ME.md` | any AI assistant | Provider-neutral version of the same |
| `provisioning.md` | you | Checklist: brew packages, apps, CLI tools, automations, services to re-login |
| `README.md` | you | How to seed the new machine |
| `private/` | you only | Note-derived context — **only** with `--include-personal`, never auto-shared |

## Safety model

- **Safe to move by default.** The personal/inner layer is left OUT even when it was extracted —
  a pack you carry to a new machine is exactly where you don't want health/money/relationship
  notes embedded. `--include-personal` adds a clearly marked `private/` section and **refuses**
  to write it under a cloud-sync root.
- **Fact vs inference preserved.** Counts come from data; any "reads as" phrasing is labeled
  inference for the user to confirm.
- **Local-only**, like the rest of the skill.

## How it derives the profile

- **Work rhythm** ← `app-usage.csv` (sum minutes per app; peak hours from timestamps)
- **Tech stack** ← `installs.csv` (tool adoption chronology)
- **Terminal stack** ← `shell-tools.csv`
- **Projects + code hosts** ← `git-timeline.csv` (remotes → hosting domains)
- **Services to re-login** ← `saas-account-footprint.txt`
- **Automations** ← `launch-agents.txt`
- **Eras / inflections** ← `correlations.json`

## Roadmap (v2+)

1. **Dotfile capture** — copy `.zshrc`/`.gitconfig`/editor settings into a `dotfiles/` seed (opt-in).
2. **Provisioning script generator** — emit an idempotent `setup.sh` from the manifest (review-before-run).
3. **Preference inference** — communication style, naming conventions, indentation, tabs-vs-spaces
   from real code, folded into `CLAUDE.md`.
4. **Diff-aware refresh** — when run over a longitudinal series, update the pack instead of regenerating.
5. **Encryption option** — `--encrypt` to wrap the pack (and always the `private/` layer) at rest.
