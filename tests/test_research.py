"""Tests for the research estimands, missing data and reproducibility."""
from contextlib import closing
import importlib.util
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "code/python"))
import analyse
import research
import prepare_sources


def sector_fixture():
    rows = []
    for year in [2019, 2024]:
        for name in prepare_sources.REGIONS.values():
            for sector in research.SECTORS:
                rows.append({"year": year, "region": name, "sector": sector,
                             "employees": 100 if year == 2019 else 110})
    return rows


class ResearchTests(unittest.TestCase):
    def test_uniform_growth_has_no_mix_or_within_component(self):
        _, summaries = research.shift_share(sector_fixture(), 2019, 2024)
        for row in summaries:
            self.assertAlmostEqual(row["actual_growth_pct"], 10)
            self.assertAlmostEqual(row["national_growth_pp"], 10)
            self.assertAlmostEqual(row["industry_mix_pp"], 0)
            self.assertAlmostEqual(row["within_industry_pp"], 0)

    def test_extra_local_jobs_are_in_the_within_industry_remainder(self):
        fixture = sector_fixture()
        next(r for r in fixture if r["year"] == 2024 and r["region"] == "North West" and r["sector"] == "C")["employees"] += 95
        _, summaries = research.shift_share(fixture, 2019, 2024, "Rest of England")
        nw, wm = summaries
        self.assertAlmostEqual(nw["actual_growth_pct"], 15)
        self.assertAlmostEqual(nw["national_growth_pp"], 10)
        self.assertAlmostEqual(nw["industry_mix_pp"], 0)
        self.assertAlmostEqual(nw["within_industry_pp"], 5)
        self.assertAlmostEqual(wm["within_industry_pp"], 0)

    def test_industry_mix_uses_baseline_shares(self):
        fixture = sector_fixture()
        for row in fixture:
            if row["sector"] == "C":
                row["employees"] = 200 if row["year"] == 2019 else 240
            else:
                row["employees"] = 100
        # North West has twice as many baseline manufacturing jobs.
        for row in fixture:
            if row["region"] == "North West" and row["sector"] == "C":
                row["employees"] *= 2
        _, summaries = research.shift_share(fixture, 2019, 2024, "Rest of England")
        nw, wm = summaries
        self.assertAlmostEqual(nw["within_industry_pp"], 0)
        self.assertAlmostEqual(nw["actual_growth_pct"], 80 / 2200 * 100)
        self.assertGreater(nw["industry_mix_pp"], wm["industry_mix_pp"])

    def test_missing_industry_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing region"):
            research.shift_share(sector_fixture()[1:], 2019, 2024)

    def test_zero_local_baseline_can_have_new_jobs(self):
        fixture = sector_fixture()
        next(r for r in fixture if r["year"] == 2019 and r["region"] == "North West" and r["sector"] == "B")["employees"] = 0
        details, _ = research.shift_share(fixture, 2019, 2024, "Rest of England")
        birth = next(r for r in details if r["region"] == "North West" and r["industry"] == "B")
        self.assertEqual(birth["industry_mix_jobs"], 0)
        self.assertEqual(birth["within_industry_jobs"], 110)

    def test_aggregation_and_benchmark_change_preserve_actual_growth(self):
        fixture = sector_fixture()
        fixture[0]["employees"] = 80
        _, section = research.shift_share(fixture, 2019, 2024)
        _, broad = research.shift_share(fixture, 2019, 2024, "Rest of England", "broad")
        for a, b in zip(section, broad):
            self.assertAlmostEqual(a["actual_growth_pct"], b["actual_growth_pct"])
            self.assertAlmostEqual(b["actual_growth_pct"], b["national_growth_pp"] + b["industry_mix_pp"] + b["within_industry_pp"])

    def test_bres_published_total_is_not_forced_to_match_components(self):
        rows = [{"year": 2019, "region": "North West", "division": f"{low:02d}", "employees": 10}
                for low, _, _ in research.SECTORS.values()]
        rows.append({"year": 2019, "region": "North West", "division": "TOTAL", "employees": 200})
        _, reconciliation = research.aggregate_bres(rows)
        self.assertEqual(reconciliation[0]["published_total"], 200)
        self.assertEqual(reconciliation[0]["sum_sections_a_s"], 190)
        self.assertEqual(reconciliation[0]["division_sum_minus_published"], -10)

    def test_calendar_baseline_needs_twelve_unique_months(self):
        rows = [{"region": "North West", "period": f"2019-{m:02d}", "payrolled_employees": 100} for m in range(1, 13)]
        self.assertEqual(research.annual_average(rows, 2019, "North West"), 100)
        with self.assertRaisesRegex(ValueError, "complete calendar"):
            research.annual_average(rows[:-1], 2019, "North West")
        with self.assertRaises(ValueError):
            research.annual_average(rows + rows[:1], 2019, "North West")

    def test_missing_source_values_are_not_zero(self):
        for marker in ["x", "..", ":", "-", "", float("nan")]:
            with self.subTest(marker=marker):
                self.assertIsNone(prepare_sources.numeric(marker))
        self.assertEqual(prepare_sources.numeric(0), 0)

    def test_latest_aps_tests_use_published_margins_and_holm(self):
        observations = [{"period_end": "2026-06", "indicator": indicator, "region": name, "confidence_pp": value}
                        for indicator, margins in [("employment", [0.8, 1.0]), ("inactivity", [0.7, 0.9])]
                        for name, value in zip(research.FOCUS, margins)]
        latest = [{"period_end": "2026-06", "indicator": indicator, "region_a": "North West",
                   "region_b": "West Midlands", "gap_pp": gap}
                  for indicator, gap in [("employment", 0.8), ("inactivity", 0.4)]]
        tests = research.aps_tests(observations, latest)
        self.assertAlmostEqual(tests[0]["approx_ci_lower_pp"], -0.4806248475)
        self.assertAlmostEqual(tests[0]["approx_p_two_sided"], 0.2208005047)
        self.assertAlmostEqual(tests[0]["holm_adjusted_p"], 0.4416010093)
        self.assertAlmostEqual(tests[1]["holm_adjusted_p"], 0.4916962127)

    def test_missing_confidence_margin_leaves_test_unavailable(self):
        observations = [{"period_end": "2026-06", "indicator": "employment", "region": name, "confidence_pp": value}
                        for name, value in zip(research.FOCUS, [None, 1])]
        tests = research.aps_tests(observations, [{"period_end": "2026-06", "indicator": "employment",
                    "region_a": "North West", "region_b": "West Midlands", "gap_pp": 0.8}])
        self.assertIsNone(tests[0]["approx_p_two_sided"])
        self.assertIsNone(tests[0]["reject_5pct_after_holm"])

    def test_real_pay_uses_matching_april_not_an_annual_price_average(self):
        tables, _ = research.load_inputs(PROJECT / "data/extended")
        earnings, comparisons, _ = research.earnings_analysis(tables["ashe"], tables["cpih"])
        current = next(r for r in earnings if r["year"] == 2026 and r["industry"] == "ALL" and
                       r["region"] == "North West" and r["work_pattern"] == "all")
        april = next(r["cpih_index"] for r in tables["cpih"] if r["period"] == "2026-04")
        baseline = next(r["cpih_index"] for r in tables["cpih"] if r["period"] == "2019-04")
        self.assertEqual(current["cpih_april_index"], april)
        self.assertAlmostEqual(current["median_in_april_2019_gbp"], 17.79 * baseline / april)

    def test_full_research_runs_offline_from_release_inputs(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(analyse, "download", side_effect=AssertionError("Network used")):
            result = research.run(Path(directory))
            self.assertEqual(result["source_rows"], {"bres": 5607, "paye": 1332, "ashe": 480, "cpih": 106})
            for name in ["paye_recovery", "hourly_pay", "shift_share", "sector_contributions"]:
                for extension in ["png", "svg"]:
                    self.assertTrue((Path(directory) / "figures" / f"{name}.{extension}").is_file())
            text = (Path(directory) / "findings.md").read_text(encoding="utf-8")
            self.assertIn("2019-2024", text)
            self.assertIn("5.65%", text)
            self.assertNotIn(str(PROJECT), text)


if __name__ == "__main__":
    unittest.main()
