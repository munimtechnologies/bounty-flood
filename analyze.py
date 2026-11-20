#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2)
"""Grade the pre-registered bounty-flood hypotheses (see PREREG.md).

Reads counts.jsonl and issues.jsonl written by collect.py and writes
results.json, monthly.csv and issue_months.csv. Standard library only.
"""
import argparse
import csv
import json
import os
import random

# Fixed before any data was collected (PREREG.md).
P0 = ("2023-01", "2024-12")   # before agentic coding tools were in wide use
P1 = ("2025-07", "2026-08")   # agentic coding era, leaving >= 60 days for comments to accrue
COLLAPSE_RECENT = ("2026-07", "2026-10")
COLLAPSE_BASE = ("2024-01", "2024-12")
MIN_N = 30
SEED = 20261120
BOOT = 2000

# Repos known to post fake or never-paid bounties (MV2 software playbook, 2026-11-19).
FARM_OWNERS = {
    "limitlessprojects", "securebananalabs", "unsafelabs", "zhangjiayang6835-cyber", "relayhop",
    "mscrnt", "varun3ware", "tine1117", "arakoodev", "clankernation", "furongjun-1999",
    "ditto-assistant", "xpex-systems-ai", "willsmithte", "lukiod", "scottonchain", "pg-agi",
    "splurt-station", "speakers-in-tech", "ikalus1988", "jira44", "habibdxb01", "bawes-universe",
    "thesolaai", "javelin-anticheat", "bu1ldth3futur3", "warps", "phankhoa95", "hanzoai",
    "theselfish", "bshelby88", "kwesigaamon8-web", "ophirpay", "xevrion-v2", "alfrexo95",
    "fractal-neurons",
}


def load_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def in_window(month, window):
    return window[0] <= month <= window[1]


def is_farm(repo):
    owner = (repo or "").split("/")[0].lower()
    return owner in FARM_OWNERS


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    mid = n // 2
    return float(xs[mid]) if n % 2 else (xs[mid - 1] + xs[mid]) / 2.0


def quantile(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def monthly_table(counts):
    table = {}
    for c in counts:
        row = table.setdefault(c["month"], {"month": c["month"]})
        row[c["series"]] = int(c["total_count"])
        if c.get("incomplete"):
            row["incomplete"] = True
    for row in table.values():
        prs = row.get("bot_prs", 0)
        iss = row.get("bot_issues", 0)
        row["merged_share"] = (row.get("bot_prs_merged", 0) / prs) if prs else None
        row["prs_per_issue"] = (prs / iss) if iss else None
    return [table[k] for k in sorted(table)]


def bootstrap_median_ratio(a, b, boot=BOOT, seed=SEED):
    """95% percentile CI for median(b)/median(a), resampling issues."""
    rng = random.Random(seed)
    ratios = []
    for _ in range(boot):
        ra = [a[rng.randrange(len(a))] for _ in a]
        rb = [b[rng.randrange(len(b))] for _ in b]
        ma, mb = median(ra), median(rb)
        if ma:
            ratios.append(mb / ma)
    if not ratios:
        return None, None
    return quantile(ratios, 0.025), quantile(ratios, 0.975)


def grade(counts, issues):
    rows = monthly_table(counts)
    clean = [i for i in issues if not is_farm(i.get("repo")) and i.get("comments") is not None]
    res = {"periods": {"P0": P0, "P1": P1}, "n_issues_sampled": len(issues),
           "n_issues_after_farm_filter": len(clean), "hypotheses": {}}

    # H1: attempt flood, measured as comments per Algora bounty issue.
    c0 = [i["comments"] for i in clean if in_window(i["month"], P0)]
    c1 = [i["comments"] for i in clean if in_window(i["month"], P1)]
    h1 = {"n_P0": len(c0), "n_P1": len(c1), "median_P0": median(c0), "median_P1": median(c1),
          "p90_P0": quantile(c0, 0.9), "p90_P1": quantile(c1, 0.9), "threshold_ratio": 2.0}
    if len(c0) >= MIN_N and len(c1) >= MIN_N and h1["median_P0"]:
        h1["ratio"] = h1["median_P1"] / h1["median_P0"]
        h1["ci95"] = bootstrap_median_ratio(c0, c1)
        h1["verdict"] = "PASS" if h1["ratio"] >= 2.0 else "FAIL"
    else:
        h1["verdict"] = "INCONCLUSIVE"
    res["hypotheses"]["H1_attempt_flood"] = h1

    # H2: merged share of claim PRs falls by >= 15 percentage points.
    def pooled(window):
        prs = sum(r.get("bot_prs", 0) for r in rows if in_window(r["month"], window))
        mer = sum(r.get("bot_prs_merged", 0) for r in rows if in_window(r["month"], window))
        return prs, mer
    p0, m0 = pooled(P0)
    p1, m1 = pooled(P1)
    h2 = {"prs_P0": p0, "merged_P0": m0, "prs_P1": p1, "merged_P1": m1, "threshold_pp": 15}
    if p0 >= MIN_N and p1 >= MIN_N:
        h2["share_P0"], h2["share_P1"] = m0 / p0, m1 / p1
        h2["drop_pp"] = 100 * (h2["share_P0"] - h2["share_P1"])
        h2["verdict"] = "PASS" if h2["drop_pp"] >= 15 else "FAIL"
    else:
        h2["verdict"] = "INCONCLUSIVE"
    res["hypotheses"]["H2_claim_acceptance_drop"] = h2

    # H3: share of bounty issues closed as completed falls by >= 10 points.
    def completed(window):
        xs = [i for i in clean if in_window(i["month"], window)]
        done = sum(1 for i in xs if i.get("state") == "closed" and i.get("state_reason") == "completed")
        return len(xs), done
    n0, d0 = completed(P0)
    n1, d1 = completed(P1)
    h3 = {"n_P0": n0, "completed_P0": d0, "n_P1": n1, "completed_P1": d1, "threshold_pp": 10}
    if n0 >= MIN_N and n1 >= MIN_N:
        h3["share_P0"], h3["share_P1"] = d0 / n0, d1 / n1
        h3["drop_pp"] = 100 * (h3["share_P0"] - h3["share_P1"])
        h3["verdict"] = "PASS" if h3["drop_pp"] >= 10 else "FAIL"
    else:
        h3["verdict"] = "INCONCLUSIVE"
    res["hypotheses"]["H3_completion_drop"] = h3

    # H4: new Algora bounty issues per month in Jul-Oct 2026 <= 25% of the 2024 monthly mean.
    base = mean(r.get("bot_issues", 0) for r in rows if in_window(r["month"], COLLAPSE_BASE))
    recent = mean(r.get("bot_issues", 0) for r in rows if in_window(r["month"], COLLAPSE_RECENT))
    h4 = {"mean_2024": base, "mean_2026_07_10": recent, "threshold_share": 0.25}
    if base and recent is not None:
        h4["share"] = recent / base
        h4["verdict"] = "PASS" if h4["share"] <= 0.25 else "FAIL"
    else:
        h4["verdict"] = "INCONCLUSIVE"
    res["hypotheses"]["H4_board_collapse"] = h4

    # Descriptive, per month (not graded).
    by_month = {}
    for i in clean:
        by_month.setdefault(i["month"], []).append(i)
    issue_rows = []
    for mth in sorted(by_month):
        xs = by_month[mth]
        cs = [i["comments"] for i in xs]
        issue_rows.append({
            "month": mth, "n": len(xs), "median_comments": median(cs),
            "p90_comments": quantile(cs, 0.9),
            "completed_share": sum(1 for i in xs if i.get("state_reason") == "completed") / len(xs),
            "open_share": sum(1 for i in xs if i.get("state") == "open") / len(xs),
            "repos": len({i["repo"] for i in xs}),
        })
    return res, rows, issue_rows


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    counts = load_jsonl(os.path.join(a.in_dir, "counts.jsonl"))
    issues = load_jsonl(os.path.join(a.in_dir, "issues.jsonl"))
    res, rows, issue_rows = grade(counts, issues)
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    write_csv(os.path.join(a.out_dir, "monthly.csv"), rows,
              ["month", "bot_issues", "bot_prs", "bot_prs_merged", "label_issues",
               "merged_share", "prs_per_issue", "incomplete"])
    write_csv(os.path.join(a.out_dir, "issue_months.csv"), issue_rows,
              ["month", "n", "median_comments", "p90_comments", "completed_share", "open_share", "repos"])
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
