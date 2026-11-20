# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2)
"""Offline tests for collect.py and analyze.py (no network)."""
import json
import os
import sys
import tempfile
import unittest
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze  # noqa: E402
import collect  # noqa: E402


class CollectTests(unittest.TestCase):
    def test_months_crosses_year(self):
        self.assertEqual(list(collect.months("2025-11", "2026-02")),
                         [(2025, 11), (2025, 12), (2026, 1), (2026, 2)])

    def test_month_range_leap_year(self):
        self.assertEqual(collect.month_range(2024, 2), "2024-02-01..2024-02-29")
        self.assertEqual(collect.month_range(2026, 11), "2026-11-01..2026-11-30")

    def test_build_url_encodes_query(self):
        url = collect.build_url(collect.SERIES["label_issues"].format(r="2024-01-01..2024-01-31"))
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        self.assertEqual(q["q"][0], 'is:issue label:"\U0001F48E Bounty" created:2024-01-01..2024-01-31')
        self.assertEqual(q["per_page"][0], "1")

    def test_parse_item_keeps_needed_fields(self):
        item = {"repository_url": "https://api.github.com/repos/acme/widget", "number": 7,
                "created_at": "2024-01-02T00:00:00Z", "closed_at": None, "state": "open",
                "state_reason": None, "comments": 4, "labels": [{"name": "\U0001F48E Bounty"}, {"name": "$100"}],
                "author_association": "MEMBER", "body": "long text", "user": {"login": "x"}}
        p = collect.parse_item(item, "2024-01")
        self.assertEqual(p["repo"], "acme/widget")
        self.assertEqual(p["labels"], ["\U0001F48E Bounty", "$100"])
        self.assertNotIn("body", p)
        self.assertNotIn("user", p)


def counts_for(month, issues, prs, merged):
    return [{"month": month, "series": "bot_issues", "total_count": issues},
            {"month": month, "series": "bot_prs", "total_count": prs},
            {"month": month, "series": "bot_prs_merged", "total_count": merged},
            {"month": month, "series": "label_issues", "total_count": issues}]


def issue(month, comments, state="closed", reason="completed", repo="acme/widget"):
    return {"month": month, "repo": repo, "comments": comments, "state": state, "state_reason": reason}


class AnalyzeTests(unittest.TestCase):
    def synthetic(self):
        counts = []
        for m in ["2023-06", "2024-03", "2024-06"]:
            counts += counts_for(m, 100, 40, 30)
        for m in ["2025-09", "2026-03"]:
            counts += counts_for(m, 50, 100, 20)
        for m in ["2026-09", "2026-10"]:  # after P1 ends (2026-08), inside the collapse window
            counts += counts_for(m, 5, 2, 1)
        issues = [issue("2024-03", 3) for _ in range(40)]
        issues += [issue("2026-03", 9, state="open", reason=None) for _ in range(40)]
        issues += [issue("2026-03", 500, repo="ClankerNation/OpenAgents") for _ in range(40)]
        return counts, issues

    def test_median_and_quantile(self):
        self.assertEqual(analyze.median([3, 1, 2]), 2.0)
        self.assertEqual(analyze.median([1, 2, 3, 4]), 2.5)
        self.assertIsNone(analyze.median([]))
        self.assertAlmostEqual(analyze.quantile([0, 10], 0.9), 9.0)

    def test_farm_filter(self):
        self.assertTrue(analyze.is_farm("ClankerNation/OpenAgents"))
        self.assertFalse(analyze.is_farm("calcom/cal.com"))

    def test_grade_synthetic(self):
        counts, issues = self.synthetic()
        res, rows, issue_rows = analyze.grade(counts, issues)
        h = res["hypotheses"]
        self.assertEqual(res["n_issues_after_farm_filter"], 80)
        self.assertEqual(h["H1_attempt_flood"]["ratio"], 3.0)
        self.assertEqual(h["H1_attempt_flood"]["verdict"], "PASS")
        lo, hi = h["H1_attempt_flood"]["ci95"]
        self.assertAlmostEqual(lo, 3.0)
        self.assertAlmostEqual(hi, 3.0)
        self.assertAlmostEqual(h["H2_claim_acceptance_drop"]["drop_pp"], 55.0)
        self.assertEqual(h["H2_claim_acceptance_drop"]["verdict"], "PASS")
        self.assertAlmostEqual(h["H3_completion_drop"]["drop_pp"], 100.0)
        self.assertAlmostEqual(h["H4_board_collapse"]["share"], 0.05)
        self.assertEqual(h["H4_board_collapse"]["verdict"], "PASS")
        self.assertEqual([r["month"] for r in rows][0], "2023-06")
        self.assertAlmostEqual(rows[0]["merged_share"], 0.75)

    def test_small_samples_are_inconclusive(self):
        counts = counts_for("2024-03", 10, 5, 4) + counts_for("2026-03", 10, 5, 1)
        issues = [issue("2024-03", 3) for _ in range(5)] + [issue("2026-03", 9) for _ in range(5)]
        res, _, _ = analyze.grade(counts, issues)
        h = res["hypotheses"]
        self.assertEqual(h["H1_attempt_flood"]["verdict"], "INCONCLUSIVE")
        self.assertEqual(h["H2_claim_acceptance_drop"]["verdict"], "INCONCLUSIVE")
        self.assertEqual(h["H3_completion_drop"]["verdict"], "INCONCLUSIVE")

    def test_main_writes_outputs(self):
        counts, issues = self.synthetic()
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "counts.jsonl"), "w", encoding="utf-8") as f:
                f.write("\n".join(json.dumps(c) for c in counts))
            with open(os.path.join(d, "issues.jsonl"), "w", encoding="utf-8") as f:
                f.write("\n".join(json.dumps(i) for i in issues))
            analyze.main(["--in-dir", d, "--out-dir", d])
            for name in ("results.json", "monthly.csv", "issue_months.csv"):
                self.assertTrue(os.path.exists(os.path.join(d, name)), name)


if __name__ == "__main__":
    unittest.main()
