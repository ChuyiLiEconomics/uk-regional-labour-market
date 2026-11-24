"""Synthetic fixtures test data safeguards, never substantive labour market findings."""
import csv
from contextlib import closing
import importlib.util
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("analyse", PROJECT / "code/python/analyse.py")
analyse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyse)


def fixture(regions=None):
    regions = analyse.REGIONS if regions is None else regions
    rows = []
    for date, label in [("2025-03", "Apr 2024-Mar 2025"), ("2025-06", "Jul 2024-Jun 2025")]:
        for geography, (region, ons_code) in regions.items():
            for variable, (_, variable_name) in analyse.INDICATORS.items():
                for measure in ["20599", "21003"]:
                    rows.append({"DATE": date, "DATE_NAME": label, "GEOGRAPHY": geography,
                        "GEOGRAPHY_NAME": region, "GEOGRAPHY_CODE": ons_code, "GEOGRAPHY_TYPE": "regions",
                        "VARIABLE": variable, "VARIABLE_NAME": variable_name, "MEASURES": measure,
                        "OBS_VALUE": "72.0" if measure == "20599" else "1.2", "OBS_STATUS": "A", "OBS_CONF": "F", "RECORD_COUNT": "16"})
    return rows


def encoded(rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


class DataIntegrityTests(unittest.TestCase):
    def test_missing_and_suppressed_values_do_not_become_zero(self):
        rows = fixture()
        rows[0]["OBS_VALUE"] = ""
        rows[2].update(OBS_VALUE="95", OBS_STATUS="S")
        cleaned, quality = analyse.clean_csv(encoded(rows))
        self.assertEqual(sum(r["rate_pct"] is None for r in cleaned), 2)
        self.assertEqual(quality["excluded_or_missing_values"], 2)

    def test_wrong_geography_names_are_rejected(self):
        rows = fixture()
        rows[0]["GEOGRAPHY_NAME"] = "Great Britain"
        with self.assertRaisesRegex(ValueError, "Geography"):
            analyse.clean_csv(encoded(rows))

    def test_changed_indicator_definition_is_rejected(self):
        rows = fixture()
        rows[0]["VARIABLE_NAME"] = "Employment rate - aged 16+"
        with self.assertRaisesRegex(ValueError, "Indicator definition"):
            analyse.clean_csv(encoded(rows))

    def test_duplicate_observations_are_not_aggregated(self):
        rows = fixture()
        rows[-1] = rows[0].copy()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            analyse.clean_csv(encoded(rows))

    def test_truncated_download_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            analyse.clean_csv(encoded(fixture()[:-1]))

    def test_non_public_observations_are_rejected(self):
        rows = fixture()
        rows[0]["OBS_CONF"] = "C"
        with self.assertRaisesRegex(ValueError, "free for publication"):
            analyse.clean_csv(encoded(rows))

    def test_invalid_numeric_values_are_rejected(self):
        for value in ["NaN", "inf", "-1", "101", "oops"]:
            with self.subTest(value=value):
                rows = fixture()
                rows[0]["OBS_VALUE"] = value
                with self.assertRaises(ValueError):
                    analyse.clean_csv(encoded(rows))

    def test_sql_uses_latest_common_valid_period_and_correct_gap(self):
        rows = fixture()
        for row in rows:
            if row["MEASURES"] != "20599":
                continue
            row["OBS_VALUE"] = "74.0" if row["GEOGRAPHY_NAME"] == "North West" else "71.0"
            if row["DATE"] == "2025-06" and row["VARIABLE"] == "45" and row["GEOGRAPHY_NAME"] == "West Midlands":
                row["OBS_VALUE"] = ""
        cleaned, _ = analyse.clean_csv(encoded(rows))
        with closing(sqlite3.connect(":memory:")) as connection:
            analyse.load_database(connection, cleaned)
            summary = {row["indicator"]: row for row in analyse.summaries(connection)[1]}
            self.assertEqual(summary["employment"]["period_end"], "2025-03")
            self.assertEqual(summary["inactivity"]["period_end"], "2025-06")
            self.assertEqual(summary["employment"]["gap_pp"], 3.0)
            # Check that a real zero is retained, unlike a missing rate.
            connection.execute("UPDATE observations SET rate_pct=0 WHERE indicator='inactivity' AND region_code='E12000002'")
            result = {row["indicator"]: row for row in analyse.summaries(connection)[1]}
            self.assertEqual(result["inactivity"]["region_a_pct"], 0.0)

    def test_another_region_pair_does_not_depend_on_default_names(self):
        regions = {"2013265921": ("North East", "E12000001"),
                   "2013265923": ("Yorkshire and The Humber", "E12000003")}
        rows = fixture(regions)
        for row in rows:
            if row["MEASURES"] == "20599":
                row["OBS_VALUE"] = "70" if row["GEOGRAPHY"] == "2013265921" else "73"
        cleaned, _ = analyse.clean_csv(encoded(rows), regions)
        with closing(sqlite3.connect(":memory:")) as connection:
            analyse.load_database(connection, cleaned, regions)
            _, latest = analyse.summaries(connection, regions)
        self.assertEqual(latest[0]["region_a"], "North East")
        self.assertEqual(latest[0]["region_b"], "Yorkshire and The Humber")
        self.assertEqual(latest[0]["gap_pp"], -3.0)

    def test_reversing_region_order_reverses_gap(self):
        rows = fixture()
        for row in rows:
            if row["MEASURES"] == "20599":
                row["OBS_VALUE"] = "74" if row["GEOGRAPHY_NAME"] == "North West" else "71"
        cleaned, _ = analyse.clean_csv(encoded(rows))
        regions = dict(reversed(list(analyse.REGIONS.items())))
        with closing(sqlite3.connect(":memory:")) as connection:
            analyse.load_database(connection, cleaned, regions)
            _, latest = analyse.summaries(connection, regions)
        self.assertEqual(latest[0]["region_a"], "West Midlands")
        self.assertEqual(latest[0]["gap_pp"], -3.0)

    def test_baseline_changes_use_levels_and_percentage_point_gaps(self):
        rows = fixture()
        for row in rows:
            if row["MEASURES"] == "20599":
                is_a = row["GEOGRAPHY_NAME"] == "North West"
                row["OBS_VALUE"] = str((70 if is_a else 71) if row["DATE"] == "2025-03" else (73 if is_a else 72))
        cleaned, _ = analyse.clean_csv(encoded(rows))
        with closing(sqlite3.connect(":memory:")) as connection:
            analyse.load_database(connection, cleaned)
            periods, latest = analyse.summaries(connection)
        changes = analyse.baseline_changes(periods, latest, "2025-03")
        self.assertEqual(changes[0]["change_region_a_pp"], 3.0)
        self.assertEqual(changes[0]["change_region_b_pp"], 1.0)
        self.assertEqual(changes[0]["change_in_gap_pp"], 2.0)

    def test_missing_baseline_does_not_substitute_another_period(self):
        cleaned, _ = analyse.clean_csv(encoded(fixture()))
        with closing(sqlite3.connect(":memory:")) as connection:
            analyse.load_database(connection, cleaned)
            periods, latest = analyse.summaries(connection)
        changes = analyse.baseline_changes(periods, latest, "2019-12")
        self.assertTrue(all(row["change_region_a_pp"] is None for row in changes))
        self.assertTrue(all(row["baseline_period_end"] == "2019-12" for row in changes))

    def test_snapshot_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            (destination / "nomis.csv").write_bytes(encoded(fixture()))
            import json
            (destination / "source.json").write_text(json.dumps({
                "format": analyse.FORMAT, "dataset": analyse.DATASET,
                "raw_file": "nomis.csv", "sha256": "0" * 64,
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                analyse.load_snapshot(destination)

    def test_duplicate_ons_regions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "different ONS codes"):
            analyse.validate_regions({"2013265921": ("North East", "E12000001"),
                                     "2013265922": ("Alias", "E12000001")})

    def test_bundled_snapshot_runs_offline_in_a_temporary_output_directory(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(analyse, "download", side_effect=AssertionError("Network used")):
            result = analyse.run(output_dir=directory)
            self.assertEqual(result["observations"], 184)
            self.assertEqual(result["latest_comparison"][0]["gap_pp"], 0.8)
            self.assertEqual(result["baseline_changes"][0]["change_in_gap_pp"], 0.2)
            with (Path(directory) / "tables/observations.csv").open(encoding="utf-8") as stream:
                exported = list(csv.DictReader(stream))
            self.assertEqual(len(exported), 184)
            self.assertTrue((Path(directory) / "figures/regional_gaps.png").is_file())
            self.assertTrue((Path(directory) / "findings.md").is_file())


if __name__ == "__main__":
    unittest.main()
