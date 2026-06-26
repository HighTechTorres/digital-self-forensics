# Trigger-accuracy benchmark — iteration 1

Method: independent router subagents judged realistic queries blind (labels shuffled across batches),
simulating how Claude decides to invoke a skill from its name+description.

| Set | Queries | Correct | Notes |
|---|---|---|---|
| Core should-trigger | 7 | 7/7 | varied/indirect phrasings all fired |
| Core near-miss (should-not) | 7 | 7/7 | cleanup, security, recovery, CSV, AWS, future-tracking, partner's-phone |
| Hard edge cases | 5 | 5/5 | file-org, setup/migration, file-inventory → NO; usage-history → TRIGGER; therapist→client device → NO |
| **Total** | **19** | **19/19 (100%)** | precision 8/8 · recall 8/8 · specificity 11/11 |

Ethical boundary verified: both "someone else's device" queries correctly did NOT trigger.
Conclusion: description discriminates strongly on hard near-misses; no change needed this iteration.
