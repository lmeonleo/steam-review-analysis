"""Fast integrity tests for generated Steam analysis results."""

import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "output/results/local"


class ResultIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
        cls.top = pd.read_csv(RESULTS / "top_reliable.csv")
        cls.price = pd.read_csv(RESULTS / "price_band.csv")

    def test_primary_key_survives_cleaning(self):
        self.assertEqual(self.summary["clean_rows"], self.summary["distinct_appids"])
        self.assertEqual(self.summary["clean_rows"], 27075)

    def test_review_counts_are_consistent(self):
        total = self.summary["total_positive_ratings"] + self.summary["total_negative_ratings"]
        self.assertEqual(total, 32803682)
        self.assertGreater(self.summary["overall_weighted_positive_pct"], 0)
        self.assertLessEqual(self.summary["overall_weighted_positive_pct"], 100)

    def test_wilson_ranking_is_descending_and_eligible(self):
        self.assertTrue(self.top["wilson_pct"].is_monotonic_decreasing)
        self.assertTrue((self.top["total_reviews"] >= 1000).all())
        self.assertTrue((self.top["wilson_pct"] <= self.top["rating_pct"]).all())

    def test_price_bands_are_complete(self):
        self.assertEqual(self.price["games"].sum(), self.summary["clean_rows"])
        self.assertEqual(self.price["price_band"].tolist(), ["Free", "Under 5", "5-10", "10-20", "20-40", "40+"])


if __name__ == "__main__":
    unittest.main()
