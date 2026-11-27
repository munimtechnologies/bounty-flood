# bounty-flood phase 2: Expensify's paid "Help Wanted" program (pre-registration)

Written 2026-11-27, before any per-issue outcome data for this phase was collected. By MV2 of Munim, Inc. (mv2@munimtech.com); made with AI agents working in his name. Apache-2.0 (code), CC BY 4.0 (text).

## Why a second program

Phase 1 ([PREREG.md](PREREG.md), graded in [ADDENDUM-2026-11-25.md](ADDENDUM-2026-11-25.md)) found no attempt flood on real Algora bounties, and found that Algora's supply of bounties stopped in mid-2026. Algora could be a special case: it was winding down its public board. This phase asks the same question of the largest public paid-contribution program outside Algora. Expensify/App pays outside contributors (usually $250 per issue, through Upwork) for issues labelled `Help Wanted`. Contributors post written proposals as issue comments before anyone is hired.

Since April 2026 at the latest, Expensify's own AI agent (GitHub login `MelvinBot`) also posts a proposal on these issues, often first, and can write the fix itself when asked (example: [Expensify/App#87517](https://github.com/Expensify/App/issues/87517), 2026-04-09). So the program lets us test a second hypothesis besides the flood: **in-sourcing**, where the company's own agent replaces the paid outside contributor.

## Population and periods

- Population: issues in `Expensify/App` that carry the label `Help Wanted` when counted, by issue creation date (GitHub search `repo:Expensify/App label:"Help Wanted" is:issue created:<range>`).
- P0 (before agents): 2023-01-01..2024-12-31. P1 (agent era): 2025-07-01..2026-08-31. Same periods as phase 1.
- Counts come from GitHub search `total_count` with `incomplete_results` false. Any query that returns `incomplete_results: true` is re-run later; if it still fails, that test is reported as not graded.

## What was already seen before writing this (disclosed)

While deciding whether this phase was worth doing, we ran five supply queries (2026-11-27, between 18:45 and 19:30 UTC):

| created | Help Wanted issues |
|---|---|
| 2024-09-01..2024-11-26 | 265 |
| 2025-09-01..2025-11-26 | 424 |
| 2026-01-01..2026-04-30 | 515 |
| 2026-05-01..2026-08-31 | 236 |
| 2026-09-01..2026-11-26 | 20 |

So a fall in supply since May 2026 is already known to us and is **not** a test here. It is reported as exploratory. The supply hypothesis below (X4) is a forecast of months that have not happened yet. We also read the comments of one issue (#87517) to find MelvinBot's login. No comment counts, close reasons or MelvinBot counts for any period were looked at.

## Hypotheses and pass rules

- **X1 attempt flood.** The median number of comments per Help Wanted issue in P1 is at least 1.5 times the median in P0. Median from the cumulative counts `comments:0..k`: the median is the smallest k with count(comments ≤ k) ≥ n/2. PASS if ratio ≥ 1.5.
- **X2 fewer completed.** The share of Help Wanted issues closed with reason "completed" (`is:closed reason:completed`) falls by at least 10 percentage points from P0 to P1. PASS if the drop is ≥ 10 points.
- **X3 in-sourcing.** Among Help Wanted issues created 2026-05-01..2026-08-31, the share on which `MelvinBot` commented (`commenter:MelvinBot`) is at least 50%, and in 2024 it is at most 1%. PASS if both hold.
- **X4 no recovery (forecast).** Help Wanted issues created 2026-12-01..2027-01-31 average at most 25% of the 2024 monthly mean. Counted on or after 2027-02-15 so late labels can land. PASS if ≤ 25%.

X1-X3 are graded at the next run that can make about 40 GitHub search queries. X4 is graded on or after 2027-02-15.

## Secondary (descriptive, no pass rule)

- Monthly Help Wanted issues per half-year, 2022-2026, and the MelvinBot share per half-year, to show the timing of supply and in-sourcing together.
- Median comments per issue per half-year.

## Limits known in advance

- `label:` matches the labels an issue has now. Issues whose `Help Wanted` label was later removed are missed. If this is common in one period and not the other, it biases the comparison.
- Comments include bots (`melvin-bot[bot]`, `github-actions[bot]`, ProposalPolice) whose behaviour changed over time, so X1 is a proxy for proposals, not a count of them. If the grading run can also count `-commenter:` restricted totals, it will report a sensitivity check without bot-only issues.
- `commenter:` counts issues where the account commented at least once, not proposals.
- A fall in completion or supply can have causes unrelated to AI (company priorities, hiring, a product freeze). This is association over time, not cause.
