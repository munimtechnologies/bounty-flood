# bounty-flood

Did AI coding agents break paid open-source bounties? This is an open, pre-registered measurement from public GitHub data. It counts the bounty issues and claim PRs that Algora's own GitHub App commented on, from 2022 to 2026. It asks:

- whether each bounty draws far more attempts since coding agents arrived;
- whether claims are merged less often;
- whether fewer bounties end completed;
- whether the board collapsed.

The hypotheses and pass rules are in [PREREG.md](PREREG.md), committed before any outcome data was collected.

By MV2 of Munim, Inc. (mv2@munimtech.com). The code, analysis and text were made with AI agents working in his name. No human expert has reviewed them yet.

## Results (2026-11-25)

The grading used whole-period GitHub search totals. [ADDENDUM-2026-11-25.md](ADDENDUM-2026-11-25.md) explains why and how this differs from the plan. Results: [results/results-manual.json](results/results-manual.json). Raw totals and every query: [results/manual-counts-2026-11-25.json](results/manual-counts-2026-11-25.json).

| Hypothesis | Measured | Verdict |
|---|---|---|
| H1: the median comments per bounty at least double | 8 before (2023-24, n=2,512) and 8 after (Jul 2025-Aug 2026, n=801) | FAIL |
| H2: the merged share of claim PRs drops at least 15 points | 64.5% → 94.7%, a rise, probably from a change in when Algora's app comments | FAIL |
| H3: the completed share drops at least 10 points (farms excluded) | 91.4% → 89.6% | FAIL |
| H4: Jul-Oct 2026 has at most 25% of the 2024 monthly bounties | 0 vs 136.8 a month | PASS |

On real projects, the numbers show no flood of attempts and no fall in completion. What collapsed is the supply of bounties: new bounty issues stopped in June 2026. Without the farm filter, completion would appear to fall by 19 points. That fall comes from bounty farms, which make up 198 of 999 agent-era bounty issues and completed one of them.

## Run it

Standard library Python 3.10+ only. No token is needed.

```sh
python -m unittest -v
python grade_counts.py results/manual-counts-2026-11-25.json      # the 2026-11-25 grading
python collect.py --out-dir out                                  # the pre-registered monthly sample (~40 min)
python analyze.py --in-dir out --out-dir out
```

## Licence

Code: Apache-2.0 (see LICENSE). Text and data: CC BY 4.0.
