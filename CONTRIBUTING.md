# Contributing to digital-self-forensics

Thanks for your interest! This is a privacy-first, local-only tool, and contributions are
welcome — as long as they keep that posture intact.

## The non-negotiables (please read first)

Any change must preserve the guarantees in [`SECURITY.md`](SECURITY.md):

- **No network.** No telemetry, no uploads, no third-party calls with personal data. Ever.
- **Read-only on sources.** Copy databases before querying; never modify originals.
- **Consent stays off by default in code.** The personal/inner layer requires an explicit flag.
- **Ship zero personal data.** Nothing about any individual may be hardcoded — everything is
  computed at runtime on the host. Examples must use synthetic/fake data.

PRs that weaken any of these will be declined on principle, not preference.

## Ways to contribute

- **Native extractors** — the biggest gap. Windows/Linux deep extractors mirroring
  `macos_extract.py` (see `references/` for the artifact maps).
- **New sources** — photo EXIF, calendar/email metadata, media history, etc. Each must be
  opt-in and consent-gated.
- **Story Seeds / Handoff Pack** — see `docs/` for the design specs.
- **Docs, examples, and trigger evals** — improvements to clarity and coverage.

## Development

1. Fork and branch from `main`.
2. Keep scripts dependency-light — they auto-detect tools and degrade gracefully (see
   `render_docs.py` for the pattern). Standard library first.
3. Test against **synthetic** extract data, never your real personal data in commits.
4. Update `CHANGELOG.md` and the relevant `docs/` spec.

## Opening a PR

- Describe what changed and, explicitly, how it preserves the privacy guarantees.
- Run the trigger evals if you touched `SKILL.md`'s description/triggers.
- Be kind in review — see [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

Questions? Open an issue or a discussion. — *Maintained by [@HighTechTorres](https://github.com/HighTechTorres) · Sun Vision Digital LLC*
