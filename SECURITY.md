# Security & Responsible Use

**Maintainer:** Christian Torres ([@HighTechTorres](https://github.com/HighTechTorres)) · **Sun Vision Digital LLC**

This tool reads deeply personal data from a computer, so its security posture is the product. This document states — plainly and accountably — what it does, what it deliberately refuses to do, and how to report a problem. I put my name and my company on this because I want it judged by these guarantees.

---

## What this tool is for

`digital-self-forensics` is a **self-audit** tool. Its only sanctioned purpose is to help a person understand **their own** computer — the one they own and operate. That's it.

## What it deliberately does NOT do

These aren't promises in prose only — they're enforced in the code and verifiable in this repo:

- **No network. No exfiltration. No telemetry.** Nothing is uploaded, posted, pushed, synced, or sent to any API or third party. All processing is local to the machine it runs on. There are no external calls in the extraction or analysis path. (The optional adversarial-review step runs as a *local* agent; cross-provider review is documentation-only and never automated.)
- **No third-party / end-user data harvesting.** This is not a product that collects data from *your* users, customers, or visitors. It has no server, no account, no collection endpoint, and no business model built on anyone's data. If you are an operator who runs services, this tool gives you **zero** new ability to extract your users' data — and is not designed to.
- **Not for other people's devices.** It is built for self-audit. Running it against a device you do not own or have explicit consent to examine is misuse, unsupported, and — at the routing layer — the skill is written to decline "analyze my partner's/coworker's/client's device" requests.
- **Read-only on your data.** Databases are copied to a temp location before they're queried; original artifacts are never modified or deleted.
- **The personal layer is OFF by default, in code.** The contents of your notes are extracted only when you pass an explicit `--include-personal` flag, and the extractor **refuses to write that layer to a cloud-synced folder** (Dropbox/iCloud/OneDrive/Google Drive/Box).
- **Ships zero personal data.** Nothing about any individual is hardcoded anywhere in this repository. Every insight is computed at runtime, on the host machine, from that machine's own data.

## How to verify these claims

This repo is small and readable on purpose. To check the guarantees yourself:

- **Search for network calls** — there are none in the analysis path. `grep -rinE "requests|urllib|http|socket|curl|upload|post(" scripts/` returns nothing that transmits data.
- **Check the consent default** — `scripts/macos_extract.py` excludes the inner (notes) layer unless `--include-personal` is set, and prints a consent banner before touching anything.
- **Check the sync-guard** — the same script refuses inner-layer writes under detected cloud-sync roots.
- Run with `--dry-run` first: it prints exactly what it would read and write, and writes nothing.

## Responsible use

By using this tool you agree to run it only on machines you **own or are explicitly authorized to examine**, and to keep any output (especially the inner layer) on local, non-shared storage unless you intend otherwise. Self-knowledge is the goal; surveillance is not.

## Reporting a vulnerability or concern

Found a bug, a privacy gap, or a way the tool could be misused? Please open a private security advisory or issue on the GitHub repository, or reach the maintainer via [@HighTechTorres](https://github.com/HighTechTorres). Responsible disclosure is appreciated and will be acknowledged.

---

*Accountability matters to me. If any part of this tool's behavior doesn't match the guarantees above, that's a bug — report it and it will be fixed. — Christian Torres, Sun Vision Digital LLC*
