# Design — Story Seeds (journal mining)

*Status: spec / not yet built. Proposed as a new synthesis layer for Phase 7.*

## The idea

The current reports answer *"how do I operate?"* — metrics, eras, turning points. Story Seeds
answers a different, more human question: *"what are the moments worth remembering?"*

Your disk is full of small narratives — the origin of a project, the summer you picked up a
hobby, a trip reconstructed from download and photo timestamps, the week your work changed
shape. Story Seeds surfaces those as **journal-ready entries**: not data, but the start of a
story you can keep. The output is meant to drop straight into a personal journal.

## Output

A new document, `story-seeds.md` (and per-seed entries), each shaped as:

```
## [Title] — [approx date / window]
**The evidence.** What on disk points to this (files, dates, sources) — kept factual.
**The draft.** A short first-person paragraph in the user's voice, written to be edited, not published.
**A prompt.** One open question to pull the memory out: "What were you hoping would happen here?"
```

Hard rule, inherited from the skill: **quote, don't dramatize.** Drafts stay grounded in what the
data actually shows; the user supplies the meaning. Nothing is diagnosed, sensationalized, or
invented. Inference is labeled.

## How seeds are detected

Candidate detectors, ranked by signal, all running over existing extracts (no new disk access):

1. **Project origins** — first-commit dates in `git-timeline.csv` → "the day X began."
2. **Adoption moments** — a tool cluster in `installs.csv` that coincides with a new project
   ("the month you went all-in on video editing").
3. **Bursts** — a spike in downloads from one domain in a short window (`download-provenance.csv`)
   = a research rabbit-hole or a new obsession.
4. **Era seams** — windows from `correlations.json` where multiple sources shift together = a
   genuine life chapter boundary.
5. **(Opt-in) note moments** — dated entries in the inner layer that read like milestones; quoted
   verbatim, never paraphrased.
6. **(Roadmap) photo/EXIF moments** — trips and gatherings from clustered photo timestamps + places.

## Consent & privacy

- Story Seeds run on the **non-personal layers by default**. The note-derived and photo detectors
  are opt-in, gated exactly like the existing personal layer.
- Because the output is emotionally resonant and quotable, the same "redacted edition is the
  default shareable artifact" rule applies.

## Why it matters

It's the emotional counterpart to the Handoff Pack. The pack seeds your next *machine*; the seeds
feed your *memory*. Together they make the audit something you'd want to run every year — not for
the metrics, but for the stories you'd otherwise lose.

## Build sketch

A `scripts/story_seeds.py` mirroring `correlate.py`'s shape: read the extract dir, run the
detectors above, emit `story-seeds.json` + `story-seeds.md`. Drafting the first-person paragraph
is done by the skill (the model), from the structured seed — the script supplies evidence and
prompts, never invented prose.
