# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2)
import json
import os
import unittest

import grade_counts as g

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "results", "manual-counts-2026-11-25.json")

COUNTS = {
    "prs_P0": 780, "merged_P0": 503, "prs_P1": 243, "merged_P1": 230,
    "issues_2024": 1642, "issues_2026_07_10": 0,
    "issues_P0": 2535, "issues_P1": 999, "completed_P0": 2311, "completed_P1": 719,
    "issues_P0_nofarm": 2512, "issues_P1_nofarm": 801,
    "completed_P0_nofarm": 2297, "completed_P1_nofarm": 718,
    "le6_P0_nofarm": 962, "le7_P0_nofarm": 1192, "le8_P0_nofarm": 1375,
    "le6_P1_nofarm": 322, "le7_P1_nofarm": 395, "le8_P1_nofarm": 446,
}


def inline_data():
    return {
        "periods": {"P0": "2023-01-01..2024-12-31", "P1": "2025-07-01..2026-08-31"},
        "counts": {k: {"n": v} for k, v in COUNTS.items()},
        "series_issues": {"note": "x", "2024H1": {"n": 614, "months": 6}},
        "series_prs": {"note": "x", "2022": {"prs": 1, "merged": None}, "2023": {"prs": 176, "merged": 129}},
    }


class TestRankHelpers(unittest.TestCase):
    def test_value_at_rank(self):
        cdf = {6: 10, 7: 20, 8: 30}
        self.assertEqual(g.value_at_rank(cdf, 15), 7)
        self.assertEqual(g.value_at_rank(cdf, 20), 7)
        self.assertEqual(g.value_at_rank(cdf, 21), 8)
        self.assertIsNone(g.value_at_rank(cdf, 5))    # at or below the smallest known key
        self.assertIsNone(g.value_at_rank(cdf, 31))   # above the largest known key

    def test_gap_in_keys_is_undetermined(self):
        self.assertIsNone(g.value_at_rank({4: 10, 8: 30}, 20))

    def test_median_even_and_odd(self):
        cdf = {6: 10, 7: 20, 8: 30}
        self.assertEqual(g.median_from_cdf(cdf, 31), 7)    # odd n: rank 16 has value 7
        self.assertEqual(g.median_from_cdf(cdf, 40), 7.5)  # even n: ranks 20 and 21 have values 7 and 8


class TestGrade(unittest.TestCase):
    def setUp(self):
        self.res = g.grade(inline_data())
        self.h = self.res["hypotheses"]

    def test_h1_medians_equal(self):
        h1 = self.h["H1_attempt_flood"]
        self.assertEqual(h1["median_P0"], 8)
        self.assertEqual(h1["median_P1"], 8)
        self.assertEqual(h1["median_ci95_P0"], [8, 8])
        self.assertEqual(h1["median_ci95_P1"], [7, 8])
        self.assertAlmostEqual(h1["ratio"], 1.0)
        self.assertEqual(h1["ratio_interval_conservative"], [0.875, 1.0])
        self.assertEqual(h1["verdict"], "FAIL")

    def test_h2_reverses(self):
        h2 = self.h["H2_claim_acceptance_drop"]
        self.assertAlmostEqual(h2["share_P0"], 503 / 780)
        self.assertAlmostEqual(h2["share_P1"], 230 / 243)
        self.assertLess(h2["drop_pp"], 0)
        self.assertEqual(h2["verdict"], "FAIL")

    def test_h3_fails_without_farms(self):
        h3 = self.h["H3_completion_drop"]
        self.assertAlmostEqual(h3["drop_pp"], 100 * (2297 / 2512 - 718 / 801))
        self.assertEqual(h3["verdict"], "FAIL")
        s = h3["sensitivity_with_farms"]
        self.assertGreater(s["drop_pp"], 10)
        self.assertEqual(s["farm_issues_P1"], 198)
        self.assertEqual(s["farm_completed_P1"], 1)

    def test_h4_passes(self):
        h4 = self.h["H4_board_collapse"]
        self.assertAlmostEqual(h4["mean_2024"], 1642 / 12)
        self.assertEqual(h4["share"], 0)
        self.assertEqual(h4["verdict"], "PASS")

    def test_series_skip_notes_and_nulls(self):
        self.assertEqual(self.res["issues_per_month"], {"2024H1": 102.3})
        self.assertEqual(self.res["claim_pr_merged_share"], {"2023": 0.733})


class TestShippedData(unittest.TestCase):
    def test_file_matches_inline_counts(self):
        if not os.path.exists(DATA):
            self.skipTest("data file not present next to the test")
        with open(DATA, encoding="utf-8") as f:
            data = json.load(f)
        for k, v in COUNTS.items():
            self.assertEqual(data["counts"][k]["n"], v, k)
        res = g.grade(data)
        verdicts = {k: v["verdict"] for k, v in res["hypotheses"].items()}
        self.assertEqual(verdicts, {"H1_attempt_flood": "FAIL", "H2_claim_acceptance_drop": "FAIL",
                                    "H3_completion_drop": "FAIL", "H4_board_collapse": "PASS"})


if __name__ == "__main__":
    unittest.main()
