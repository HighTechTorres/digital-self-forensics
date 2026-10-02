# Trigger-accuracy benchmark — iteration 2 (v3.8 description)

Method: same as iteration 1. A blind router subagent judged the shuffled queries using only the skill's
name and description, and was not shown the labels. This iteration reran the full set after the v3.8
description changes:
- dropped the "v2" wording;
- added photos, the offline portrait, and the context pack;
- added "carry their context to a new computer";
- added "Not for anyone else's device".

| Set | Queries | Correct | Notes |
|---|---|---|---|
| Iteration-1 set | 14 | 14/14 | unchanged |
| New should-trigger | 3 | 3/3 | new-laptop context handoff, interactive "digital life" page, personal timeline from photos/downloads/git |
| New near-miss | 4 | 4/4 | kid's laptop, former employee's laptop (HR forensics), Spotify export, WWII timeline |
| **Total** | **21** | **21/21 (100%)** | precision 10/10 · recall 10/10 · specificity 11/11 |

Ethical boundary held: all four "someone else's device" queries (partner, kid, employee) and the
security/recovery near-misses correctly did **not** trigger.
