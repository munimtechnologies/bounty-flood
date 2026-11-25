#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2)
"""Grade the pre-registered hypotheses from whole-period GitHub search counts.

This is the 2026-11-25 addendum route (see ADDENDUM-2026-11-25.md). Instead of a
sample of up to 300 issues per month, it uses GitHub search totals for the whole
population of Algora-app bounty issues in each period:

  H1  medians come from cumulative counts (comments:0..k) for k around the median,
      with a distribution-free 95% order-statistic interval for each period's median;
  H2  pooled merged share of claim PRs, exactly as in analyze.py;
  H3  share of non-farm issues closed as completed (reason:completed);
  H4  monthly mean of bounty issues, Jul-Oct 2026 vs 2024.

Standard library only. Usage:
  python grade_counts.py results/manual-counts-2026-11-25.json results/results-manual.json
"""
import json
import math
import sys

THRESH_H1 = 2.0
THRESH_H2_PP = 15.0
THRESH_H3_PP = 10.0
THRESH_H4 = 0.25
MIN_N = 30


def value_at_rank(cdf, rank):
    """Smallest k with cdf[k] >= rank, where cdf maps k -> number of items with value <= k.

    Returns None if the known keys cannot pin it down (the rank falls at or below
    the smallest known key, or between non-consecutive keys).
    """
    ks = sorted(cdf)
    for i, k in enumerate(ks):
        if cdf[k] >= rank:
            if i == 0:
                return None
            prev = ks[i - 1]
            if prev != k - 1 or cdf[prev] >= rank:
                return None
            return k
    return None


def median_from_cdf(cdf, n):
    if n % 2:
        return value_at_rank(cdf, (n + 1) // 2)
    a = value_at_rank(cdf, n // 2)
    b = value_at_rank(cdf, n // 2 + 1)
    if a is None or b is None:
        return None
    return (a + b) / 2.0


def median_ci95(cdf, n):
    """Distribution-free 95% interval for the median from order statistics."""
    half = 1.96 * math.sqrt(n) / 2.0
    lo_rank = int(math.floor(n / 2.0 - half))
    hi_rank = int(math.ceil(1 + n / 2.0 + half))
    return value_at_rank(cdf, lo_rank), value_at_rank(cdf, hi_rank)


def grade(data):
    c = {k: v["n"] for k, v in data["counts"].items()}
    out = {"route": "whole-period search counts (ADDENDUM-2026-11-25.md)",
           "periods": data["periods"], "hypotheses": {}}

    # H1
    n0, n1 = c["issues_P0_nofarm"], c["issues_P1_nofarm"]
    cdf0 = {6: c["le6_P0_nofarm"], 7: c["le7_P0_nofarm"], 8: c["le8_P0_nofarm"]}
    cdf1 = {6: c["le6_P1_nofarm"], 7: c["le7_P1_nofarm"], 8: c["le8_P1_nofarm"]}
    m0, m1 = median_from_cdf(cdf0, n0), median_from_cdf(cdf1, n1)
    ci0, ci1 = median_ci95(cdf0, n0), median_ci95(cdf1, n1)
    h1 = {"n_P0": n0, "n_P1": n1, "median_P0": m0, "median_P1": m1,
          "median_ci95_P0": list(ci0), "median_ci95_P1": list(ci1),
          "share_le8_P0": c["le8_P0_nofarm"] / n0, "share_le8_P1": c["le8_P1_nofarm"] / n1,
          "threshold_ratio": THRESH_H1}
    if n0 >= MIN_N and n1 >= MIN_N and m0 and m1 is not None:
        h1["ratio"] = m1 / m0
        if None not in ci0 and None not in ci1 and ci0[0]:
            h1["ratio_interval_conservative"] = [ci1[0] / ci0[1], ci1[1] / ci0[0]]
        h1["verdict"] = "PASS" if h1["ratio"] >= THRESH_H1 else "FAIL"
    else:
        h1["verdict"] = "INCONCLUSIVE"
    out["hypotheses"]["H1_attempt_flood"] = h1

    # H2
    p0, g0, p1, g1 = c["prs_P0"], c["merged_P0"], c["prs_P1"], c["merged_P1"]
    h2 = {"prs_P0": p0, "merged_P0": g0, "prs_P1": p1, "merged_P1": g1, "threshold_pp": THRESH_H2_PP}
    if p0 >= MIN_N and p1 >= MIN_N:
        h2["share_P0"], h2["share_P1"] = g0 / p0, g1 / p1
        h2["drop_pp"] = 100 * (h2["share_P0"] - h2["share_P1"])
        h2["verdict"] = "PASS" if h2["drop_pp"] >= THRESH_H2_PP else "FAIL"
    else:
        h2["verdict"] = "INCONCLUSIVE"
    out["hypotheses"]["H2_claim_acceptance_drop"] = h2

    # H3 (farm repos excluded, as pre-registered)
    d0, d1 = c["completed_P0_nofarm"], c["completed_P1_nofarm"]
    h3 = {"n_P0": n0, "completed_P0": d0, "n_P1": n1, "completed_P1": d1, "threshold_pp": THRESH_H3_PP}
    if n0 >= MIN_N and n1 >= MIN_N:
        h3["share_P0"], h3["share_P1"] = d0 / n0, d1 / n1
        h3["drop_pp"] = 100 * (h3["share_P0"] - h3["share_P1"])
        h3["verdict"] = "PASS" if h3["drop_pp"] >= THRESH_H3_PP else "FAIL"
    else:
        h3["verdict"] = "INCONCLUSIVE"
    # Not pre-registered: the same share without the farm filter.
    a0, a1 = c["issues_P0"], c["issues_P1"]
    h3["sensitivity_with_farms"] = {
        "share_P0": c["completed_P0"] / a0, "share_P1": c["completed_P1"] / a1,
        "drop_pp": 100 * (c["completed_P0"] / a0 - c["completed_P1"] / a1),
        "farm_issues_P1": a1 - n1, "farm_completed_P1": c["completed_P1"] - d1,
    }
    out["hypotheses"]["H3_completion_drop"] = h3

    # H4
    base = c["issues_2024"] / 12.0
    recent = c["issues_2026_07_10"] / 4.0
    h4 = {"mean_2024": base, "mean_2026_07_10": recent, "threshold_share": THRESH_H4}
    if base:
        h4["share"] = recent / base
        h4["verdict"] = "PASS" if h4["share"] <= THRESH_H4 else "FAIL"
    else:
        h4["verdict"] = "INCONCLUSIVE"
    out["hypotheses"]["H4_board_collapse"] = h4

    # Descriptive series (not graded)
    out["issues_per_month"] = {k: round(v["n"] / v["months"], 1)
                               for k, v in data["series_issues"].items() if isinstance(v, dict)}
    out["claim_pr_merged_share"] = {k: round(v["merged"] / v["prs"], 3)
                                    for k, v in data["series_prs"].items()
                                    if isinstance(v, dict) and v.get("merged") is not None and v["prs"]}
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    src = argv[0] if argv else "results/manual-counts-2026-11-25.json"
    dst = argv[1] if len(argv) > 1 else None
    with open(src, encoding="utf-8") as f:
        res = grade(json.load(f))
    text = json.dumps(res, indent=2)
    if dst:
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
