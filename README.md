# bounty-flood

Did AI coding agents break paid open-source bounties? This is an open, pre-registered measurement built from public GitHub data. It tracks the bounty issues and claim PRs that Algora's GitHub App acted on, month by month from 2022 to 2026. It asks:

- whether each bounty draws far more attempts since coding agents arrived;
- whether claims are merged less often;
- whether fewer bounties end completed;
- whether the board collapsed.

Hypotheses and pass rules are in [PREREG.md](PREREG.md). They were committed before the collection job ran.

By MV2 of Munim, Inc. (mv2@munimtech.com). The code, analysis and text were made with AI agents working in his name.

## Run it

Standard library Python 3.10+ only. No token is needed: the collector paces itself under GitHub's unauthenticated search limit, and a full run takes about 40 minutes.

```sh
python -m unittest -v
python collect.py --out-dir out
python analyze.py --in-dir out --out-dir out
```

Outputs:

- `counts.jsonl`: monthly totals from GitHub search
- `issues.jsonl`: a sample of bounty issues with comment count, state and close reason only
- `results.json`: graded hypotheses
- `monthly.csv`
- `issue_months.csv`

## Licence

Code: Apache-2.0 (see LICENSE). Text and data: CC BY 4.0.
