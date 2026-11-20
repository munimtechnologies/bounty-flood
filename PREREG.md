# Pre-registration: did AI coding agents break paid open-source bounties?

Written 2026-11-20 by AI agents working for MV2 (Munim, Inc.). This was committed before the full collection job ran. Licence: CC BY 4.0 for this text; the code is Apache-2.0.

## Question

Cash bounties on GitHub issues, mostly funded through Algora, were a working way to pay outside contributors from 2022 to 2024. In 2025 and 2026, coding agents such as Claude Code, Codex, Copilot's coding agent and Devin became widely used, and maintainers began to complain in public:

- the curl project ended its bug bounty in January 2026;
- comma.ai removed a $500 openpilot bounty on 2026-09-15 with the words "it's all slop";
- Algora's site now sells technical recruiting and has no public bounty board.

So far the evidence is anecdotes and one-day snapshots. We measure it month by month from public GitHub data, using only the actions of Algora's own GitHub App (`app/algora-pbc`) so that copied labels and bounty "farms" can't inflate the counts.

## Data (collect.py)

For each month from 2022-01 to 2026-10, GitHub search counts:

- `bot_issues`: issues where Algora's bot commented. This is our proxy for a real Algora-funded bounty.
- `bot_prs`: PRs where Algora's bot commented, which happens when a PR claims a bounty.
- `bot_prs_merged`: the merged subset of `bot_prs`.
- `label_issues`: issues carrying the `💎 Bounty` label. This is for context only, because farms copy the label.

We also take a sample of up to 300 bounty issues per month (`bot_issues`, sorted by creation). For each one we keep the repo, its comment count, its state and its close reason. We keep no issue text and no personal data.

The job runs without a token and paces itself under GitHub's unauthenticated search limit.

## Periods (fixed now)

- **P0, before agents:** 2023-01 to 2024-12.
- **P1, agent era:** 2025-07 to 2026-08. It ends 2026-08 so every issue has had at least 60 days to collect comments.
- 2025-01 to 2025-06 is a transition window and is left out of the tests.

## Hypotheses and pass rules

- **H1, attempt flood.** The median comment count per Algora bounty issue is at least 2.0× higher in P1 than in P0. On Algora, a contributor says they are working on a bounty by commenting "/attempt", so comments are a proxy for attempts. We report a 95% bootstrap CI (2,000 resamples, seed 20261120). The test needs at least 30 issues in each period; otherwise it is INCONCLUSIVE.
- **H2, claims get rejected.** The pooled share of claim PRs that were merged is at least 15 percentage points lower in P1 than in P0. It needs at least 30 PRs in each period.
- **H3, fewer bounties completed.** The share of sampled bounty issues closed as "completed" is at least 10 points lower in P1 than in P0.
- **H4, the board collapsed.** New Algora bounty issues per month, averaged over 2026-07 to 2026-10, are at most 25% of the 2024 monthly average.

Issues in repos on our known farm list (analyze.py `FARM_OWNERS`) are excluded from H1 and H3. Each verdict is PASS, FAIL or INCONCLUSIVE, and every one will be published, including failures.

## What we already saw (pilot, before this file)

While checking whether the queries work, we ran a few of them by hand on 2026-11-20:

| Month | `bot_issues` | `bot_prs` | `bot_prs_merged` |
|---|---|---|---|
| 2023-01 | 16 | 0 | 0 |
| 2023-07 | 101 | 14 | 9 |
| 2024-01 | not run | 67 | not run |
| 2026-10 | not run | 1 | 1 |

So we already had a hint that the PR series falls sharply by late 2026, which bears on H4. We did not look at comment counts (H1) or close reasons (H3) before writing this file.

## Known limits

- Comments are a proxy for attempts. They also include maintainers' replies and bot messages.
- `commenter:app/algora-pbc` depends on how Algora's bot behaved, and that changed over time. A fall in the series can mean Algora wound down, not only that contributors flooded in. H1 and H3 are within-bounty measures that do not depend on how many bounties exist.
- GitHub search counts can be approximate. We record `incomplete_results` for every count.
- This measures association over time, not cause: the agent era also overlaps with Algora's own business change.
