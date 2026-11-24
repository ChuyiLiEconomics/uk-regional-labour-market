"""Compare regional employment, pay and industry growth from frozen official inputs."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path

import analyse

ROOT = Path(__file__).resolve().parents[2]
FOCUS = ["North West", "West Midlands"]
SECTORS = {
    "A": (1, 3, "Agriculture"), "B": (5, 9, "Mining"),
    "C": (10, 33, "Manufacturing"), "D": (35, 35, "Energy"),
    "E": (36, 39, "Water and waste"), "F": (41, 43, "Construction"),
    "G": (45, 47, "Wholesale and retail"), "H": (49, 53, "Transport and storage"),
    "I": (55, 56, "Accommodation and food"), "J": (58, 63, "Information and communication"),
    "K": (64, 66, "Finance and insurance"), "L": (68, 68, "Real estate"),
    "M": (69, 75, "Professional and technical"), "N": (77, 82, "Administrative services"),
    "O": (84, 84, "Public administration"), "P": (85, 85, "Education"),
    "Q": (86, 88, "Health and social work"), "R": (90, 93, "Arts and recreation"),
    "S": (94, 96, "Other services"),
}
COARSE = {key: ("A-F" if key <= "F" else "G-I" if key <= "I" else "J-N" if key <= "N" else "O-S")
          for key in SECTORS}


def load_inputs(directory: Path) -> tuple[dict, dict]:
    manifest = json.loads((directory / "sources.json").read_text(encoding="utf-8"))
    if manifest.get("format") != "uk-regional-research-inputs-v1":
        raise ValueError("Unknown research input format")
    tables = {}
    numeric_columns = {
        "bres.csv": ["employees"],
        "paye.csv": ["payrolled_employees"],
        "ashe.csv": ["median_gbp_per_hour", "median_cv_pct", "p10_gbp_per_hour", "p90_gbp_per_hour"],
        "cpih.csv": ["cpih_index"],
    }
    keys = {"bres.csv": ["year", "region_code", "division"], "paye.csv": ["period", "region_code"],
            "ashe.csv": ["year", "region_code", "work_pattern", "industry"], "cpih.csv": ["period"]}
    for filename, columns in numeric_columns.items():
        raw = (directory / filename).read_bytes()
        expected = manifest["prepared_inputs"][filename]
        if hashlib.sha256(raw).hexdigest() != expected["sha256"]:
            raise ValueError("Prepared input hash mismatch: " + filename)
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
        if len(rows) != expected["rows"]:
            raise ValueError("Prepared input row count mismatch")
        seen = set()
        for row in rows:
            key = tuple(row[k] for k in keys[filename])
            if key in seen:
                raise ValueError("Duplicate prepared input key")
            seen.add(key)
            for column in columns:
                row[column] = None if row[column] == "" else float(row[column])
                if row[column] is not None and (not math.isfinite(row[column]) or row[column] < 0):
                    raise ValueError("Invalid prepared numeric value")
            if "year" in row:
                row["year"] = int(row["year"])
        tables[filename[:-4]] = rows
    return tables, manifest


def annual_average(rows: list[dict], year: int, region: str) -> float:
    selected = [r for r in rows if r["region"] == region and r["period"].startswith(str(year) + "-")]
    if {r["period"] for r in selected} != {f"{year}-{m:02d}" for m in range(1, 13)} or len(selected) != 12:
        raise ValueError(f"A complete calendar year is required for {region}, {year}")
    return math.fsum(r["payrolled_employees"] for r in selected) / 12


def paye_analysis(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    names = sorted({r["region"] for r in rows})
    expected_names = {"North East", "North West", "Yorkshire and The Humber", "East Midlands",
                      "West Midlands", "East", "London", "South East", "South West"}
    if set(names) != expected_names:
        raise ValueError("PAYE input must cover all nine English regions")
    by_month = defaultdict(list)
    for row in rows:
        by_month[row["period"]].append(row)
    for period, items in by_month.items():
        if len(items) != 9 or {r["region"] for r in items} != expected_names:
            raise ValueError("Incomplete PAYE regional month")
    early = max(r["period"] for r in rows if r["is_early"] == "1")
    if any((r["is_early"] == "1") != (r["period"] == early) for r in rows):
        raise ValueError("Inconsistent PAYE early-estimate flags")
    main_period = max(r["period"] for r in rows if r["is_early"] == "0")
    series = []
    for row in rows:
        base = annual_average(rows, 2019, row["region"])
        series.append({**row, "baseline_year": 2019, "baseline_average_employees": base,
                       "index_2019_100": 100 * row["payrolled_employees"] / base})
    for period, items in sorted(by_month.items()):
        value = math.fsum(r["payrolled_employees"] for r in items)
        base = math.fsum(annual_average(rows, 2019, name) for name in names)
        series.append({"period": period, "region": "England", "region_code": "E92000001",
                       "payrolled_employees": value, "is_early": int(period == early),
                       "source_sheet": "Sum of nine English regions", "source_cell": "",
                       "baseline_year": 2019, "baseline_average_employees": base, "index_2019_100": 100 * value / base})
    summaries = []
    for name in FOCUS:
        for baseline in [2018, 2019]:
            base = annual_average(rows, baseline, name)
            for period, label in [(main_period, "latest_non_early"), (early, "early_estimate")]:
                current = next(r for r in rows if r["region"] == name and r["period"] == period)
                previous_year = f"{int(period[:4])-1}{period[4:]}"
                previous = next(r for r in rows if r["region"] == name and r["period"] == previous_year)
                summaries.append({"region": name, "period": period, "estimate_status": label,
                                  "baseline_year": baseline, "baseline_average_employees": base,
                                  "payrolled_employees": current["payrolled_employees"],
                                  "growth_from_baseline_pct": 100 * (current["payrolled_employees"] / base - 1),
                                  "year_on_year_pct": 100 * (current["payrolled_employees"] / previous["payrolled_employees"] - 1),
                                  "growth_to_2024_average_pct": 100 * (annual_average(rows, 2024, name) / base - 1)})
    return sorted(series, key=lambda r: (r["region"], r["period"])), summaries


def sector_for(division: str) -> str | None:
    if division == "TOTAL":
        return None
    for key, (low, high, _) in SECTORS.items():
        if low <= int(division) <= high:
            return key
    return None


def aggregate_bres(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    groups = defaultdict(float)
    all_divisions = defaultdict(float)
    reported = {}
    for row in rows:
        key = (row["year"], row["region"])
        value = row["employees"]
        if value is None:
            raise ValueError("Missing BRES count cannot be replaced with zero")
        if row["division"] == "TOTAL":
            reported[key] = value
            continue
        all_divisions[key] += value
        sector = sector_for(row["division"])
        if sector:
            groups[(*key, sector)] += value
    region_years = {(y, name) for y, name, _ in groups}
    if len(groups) != len(region_years) * len(SECTORS):
        raise ValueError("Incomplete BRES section coverage")
    sectors = [{"year": y, "region": name, "sector": sector, "sector_label": SECTORS[sector][2], "employees": value}
               for (y, name, sector), value in sorted(groups.items())]
    reconciliations = []
    for (year, name), total in sorted(reported.items()):
        covered = math.fsum(value for (y, n, _), value in groups.items() if (y, n) == (year, name))
        reconciliations.append({"year": year, "region": name, "published_total": total,
                                "sum_all_divisions": all_divisions[(year, name)], "sum_sections_a_s": covered,
                                "division_sum_minus_published": all_divisions[(year, name)] - total,
                                "outside_sections_a_s": all_divisions[(year, name)] - covered})
    return sectors, reconciliations


def shift_share(sectors: list[dict], start: int, end: int, benchmark: str = "England",
                grouping: str = "sections") -> tuple[list[dict], list[dict]]:
    if start >= end or benchmark not in {"England", "Rest of England"} or grouping not in {"sections", "broad", "divisions"}:
        raise ValueError("Invalid shift-share specification")
    values = defaultdict(float)
    labels = {}
    for row in sectors:
        group = COARSE[row["sector"]] if grouping == "broad" else row["sector"]
        values[(row["year"], row["region"], group)] += row["employees"]
        labels[group] = group if grouping == "broad" else row.get("sector_label", group)
    industries = (sorted({r["sector"] for r in sectors}) if grouping == "divisions" else
                  sorted(SECTORS) if grouping == "sections" else sorted(set(COARSE.values())))
    names = {r["region"] for r in sectors}
    if not set(FOCUS).issubset(names):
        raise ValueError("Missing focal region")
    reference = names if benchmark == "England" else names - set(FOCUS)
    if len(reference) != (9 if benchmark == "England" else 7):
        raise ValueError("Benchmark requires the complete English regional coverage")
    for year in [start, end]:
        for name in names:
            for industry in industries:
                if (year, name, industry) not in values:
                    raise ValueError("Missing region, year or industry")
    # An all-zero division contributes no jobs or growth. Never drop an industry
    # with a zero benchmark baseline if any region has jobs at either endpoint.
    inactive = [i for i in industries if grouping == "divisions" and
                all(values[(y, n, i)] == 0 for y in [start, end] for n in names)]
    industries = [i for i in industries if i not in inactive]
    ref0 = {i: math.fsum(values[(start, n, i)] for n in reference) for i in industries}
    ref1 = {i: math.fsum(values[(end, n, i)] for n in reference) for i in industries}
    if any(v <= 0 for v in ref0.values()):
        raise ValueError("Benchmark industry has no positive baseline")
    overall = math.fsum(ref1.values()) / math.fsum(ref0.values()) - 1
    details, summaries = [], []
    case = f"{start}-{end}_{benchmark.lower().replace(' ', '_')}_{grouping}"
    for name in FOCUS:
        base = math.fsum(values[(start, name, i)] for i in industries)
        if base <= 0:
            raise ValueError("Region has no positive baseline")
        current = math.fsum(values[(end, name, i)] for i in industries)
        region_details = []
        for industry in industries:
            e0, e1 = values[(start, name, industry)], values[(end, name, industry)]
            ref_growth = ref1[industry] / ref0[industry] - 1
            national = e0 * overall
            mix = e0 * (ref_growth - overall)
            within = e1 - e0 * (1 + ref_growth)
            region_details.append({"case": case, "region": name, "start_year": start, "end_year": end,
                                   "benchmark": benchmark, "grouping": grouping, "industry": industry,
                                   "industry_label": labels[industry],
                                   "baseline_employees": e0, "end_employees": e1, "baseline_share_pct": 100 * e0 / base,
                                   "benchmark_industry_growth_pct": 100 * ref_growth,
                                   "national_growth_jobs": national, "industry_mix_jobs": mix, "within_industry_jobs": within,
                                   "national_growth_pp": 100 * national / base, "industry_mix_pp": 100 * mix / base,
                                   "within_industry_pp": 100 * within / base,
                                   "actual_growth_contribution_pp": 100 * (e1 - e0) / base})
        details += region_details
        national, mix, within = [math.fsum(r[c] for r in region_details)
                                  for c in ["national_growth_jobs", "industry_mix_jobs", "within_industry_jobs"]]
        residual = current - base - national - mix - within
        if abs(residual) > 0.00001:
            raise ValueError("Shift-share decomposition does not reconcile")
        summaries.append({"case": case, "region": name, "start_year": start, "end_year": end,
                          "benchmark": benchmark, "grouping": grouping,
                          "industry_count": len(industries), "inactive_industries": ";".join(inactive),
                          "baseline_employees": base, "end_employees": current,
                          "actual_growth_pct": 100 * (current / base - 1),
                          "national_growth_pp": 100 * national / base, "industry_mix_pp": 100 * mix / base,
                          "within_industry_pp": 100 * within / base, "reconciliation_residual_jobs": residual})
    return details, summaries


def earnings_analysis(rows: list[dict], prices: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    price = {r["period"]: r["cpih_index"] for r in prices}
    if "2019-04" not in price:
        raise ValueError("Missing April 2019 CPIH")
    prepared = []
    for row in rows:
        april = f"{row['year']}-04"
        if april not in price:
            raise ValueError("Missing matching April CPIH")
        value = row["median_gbp_per_hour"]
        prepared.append({**row, "cpih_april_index": price[april],
                         "median_in_april_2019_gbp": value * price["2019-04"] / price[april] if value is not None else None})
    comparisons = []
    for year in sorted({r["year"] for r in prepared}):
        for pattern in ["all", "full_time", "part_time"]:
            pair = [next(r for r in prepared if r["year"] == year and r["work_pattern"] == pattern and
                         r["industry"] == "ALL" and r["region"] == name) for name in FOCUS]
            a, b = pair
            if any(r["median_gbp_per_hour"] is None for r in pair):
                raise ValueError("Missing headline ASHE median")
            changes = []
            for current in pair:
                base = next(r for r in prepared if r["region"] == current["region"] and r["year"] == 2019 and
                            r["work_pattern"] == pattern and r["industry"] == "ALL")
                changes.append(100 * (current["median_in_april_2019_gbp"] / base["median_gbp_per_hour"] - 1))
            comparisons.append({"year": year, "vintage": a["vintage"], "work_pattern": pattern,
                                "north_west_gbp_hour": a["median_gbp_per_hour"], "west_midlands_gbp_hour": b["median_gbp_per_hour"],
                                "gap_gbp_hour": a["median_gbp_per_hour"] - b["median_gbp_per_hour"],
                                "gap_pct_of_west_midlands": 100 * (a["median_gbp_per_hour"] / b["median_gbp_per_hour"] - 1),
                                "north_west_median_cv_pct": a["median_cv_pct"], "west_midlands_median_cv_pct": b["median_cv_pct"],
                                "north_west_real_growth_since_2019_pct": changes[0], "west_midlands_real_growth_since_2019_pct": changes[1]})
    industry = []
    for sector in SECTORS:
        pair = [next(r for r in prepared if r["year"] == 2025 and r["work_pattern"] == "full_time" and
                     r["industry"] == sector and r["region"] == name) for name in FOCUS]
        a, b = pair
        usable = all(r["median_gbp_per_hour"] is not None and r["median_cv_pct"] is not None and r["median_cv_pct"] <= 5 for r in pair)
        industry.append({"year": 2025, "vintage": "revised", "sector": sector, "sector_label": SECTORS[sector][2],
                         "north_west_gbp_hour": a["median_gbp_per_hour"], "west_midlands_gbp_hour": b["median_gbp_per_hour"],
                         "north_west_cv_pct": a["median_cv_pct"], "west_midlands_cv_pct": b["median_cv_pct"],
                         "passes_cv_5pct_in_both": int(usable),
                         "gap_gbp_hour": a["median_gbp_per_hour"] - b["median_gbp_per_hour"] if usable else None})
    return prepared, comparisons, industry


def aps_tests(observations: list[dict], latest: list[dict]) -> list[dict]:
    result = []
    for row in latest:
        pair = [next(r for r in observations if r["period_end"] == row["period_end"] and
                     r["indicator"] == row["indicator"] and r["region"] == name)
                for name in [row["region_a"], row["region_b"]]]
        margins = [r["confidence_pp"] for r in pair]
        valid = all(v is not None and v > 0 for v in margins)
        se = math.hypot(*(v / 1.96 for v in margins)) if valid else None
        gap = row["gap_pp"]
        result.append({**row, "margin_a_pp": margins[0], "margin_b_pp": margins[1],
                       "approx_se_gap_pp": se,
                       "approx_ci_lower_pp": gap - 1.96 * se if se else None,
                       "approx_ci_upper_pp": gap + 1.96 * se if se else None,
                       "approx_p_two_sided": math.erfc(abs(gap / se) / math.sqrt(2)) if se else None,
                       "assumption": "zero covariance between regional estimates; rounded published confidence margins"})
    # Holm correction for the two pre-specified latest-period indicators.
    available = sorted([r for r in result if r["approx_p_two_sided"] is not None], key=lambda r: r["approx_p_two_sided"])
    previous = 0
    for rank, row in enumerate(available):
        previous = max(previous, min(1, (len(result) - rank) * row["approx_p_two_sided"]))
        row["holm_adjusted_p"] = previous
        row["reject_5pct_after_holm"] = int(previous < 0.05)
    for row in result:
        row.setdefault("holm_adjusted_p", None)
        row.setdefault("reject_5pct_after_holm", None)
    return result


def run(output_dir: Path | None = None) -> dict:
    destination = output_dir.resolve() if output_dir else ROOT / "output"
    aps = analyse.run(output_dir=str(destination) if output_dir else None)
    with (destination / "tables/observations.csv").open(encoding="utf-8") as stream:
        observations = list(csv.DictReader(stream))
    for row in observations:
        row["confidence_pp"] = float(row["confidence_pp"]) if row["confidence_pp"] else None
    tables, manifest = load_inputs(ROOT / "data/extended")
    paye_series, paye_summary = paye_analysis(tables["paye"])
    sectors, reconciliation = aggregate_bres(tables["bres"])
    divisions = [{**r, "sector": r["division"], "sector_label": r["division_label"]}
                 for r in tables["bres"] if sector_for(r["division"])]
    details, decompositions = [], []
    for specification in [(2019, 2024, "England", "sections"), (2018, 2024, "England", "sections"),
                          (2019, 2023, "England", "sections"), (2019, 2024, "Rest of England", "sections"),
                          (2019, 2024, "England", "broad"), (2019, 2024, "England", "divisions")]:
        detail, summary = shift_share(divisions if specification[3] == "divisions" else sectors, *specification)
        details += detail
        decompositions += summary
    gaps = []
    for case in dict.fromkeys(r["case"] for r in decompositions):
        a, b = [next(r for r in decompositions if r["case"] == case and r["region"] == name) for name in FOCUS]
        gaps.append({"case": case, "start_year": a["start_year"], "end_year": a["end_year"],
                     "benchmark": a["benchmark"], "grouping": a["grouping"], "industry_count": a["industry_count"],
                     "inactive_industries": a["inactive_industries"],
                     "growth_gap_pp": a["actual_growth_pct"] - b["actual_growth_pct"],
                     "industry_mix_gap_pp": a["industry_mix_pp"] - b["industry_mix_pp"],
                     "within_industry_gap_pp": a["within_industry_pp"] - b["within_industry_pp"]})
    sector_gaps = []
    for sector in SECTORS:
        a, b = [next(r for r in details if r["case"] == "2019-2024_england_sections" and
                     r["region"] == name and r["industry"] == sector) for name in FOCUS]
        sector_gaps.append({"sector": sector, "sector_label": SECTORS[sector][2],
                            "growth_gap_contribution_pp": a["actual_growth_contribution_pp"] - b["actual_growth_contribution_pp"],
                            "industry_mix_gap_pp": a["industry_mix_pp"] - b["industry_mix_pp"],
                            "within_industry_gap_pp": a["within_industry_pp"] - b["within_industry_pp"]})
    nested = []
    for row in sector_gaps:
        finer = [r for r in details if r["case"] == "2019-2024_england_divisions" and
                 sector_for(r["industry"]) == row["sector"]]
        mix, remainder = [math.fsum(r[field] * (1 if r["region"] == FOCUS[0] else -1) for r in finer)
                          for field in ["industry_mix_pp", "within_industry_pp"]]
        reassigned = mix - row["industry_mix_gap_pp"]
        if not math.isclose(row["within_industry_gap_pp"], reassigned + remainder, abs_tol=1e-9):
            raise ValueError("Nested industry decomposition does not reconcile")
        nested.append({"sector": row["sector"], "sector_label": row["sector_label"],
                       "section_mix_gap_pp": row["industry_mix_gap_pp"], "division_mix_gap_pp": mix,
                       "section_within_gap_pp": row["within_industry_gap_pp"],
                       "finer_composition_gap_pp": reassigned, "division_within_gap_pp": remainder})
    earnings, earnings_comparison, industry_pay = earnings_analysis(tables["ashe"], tables["cpih"])
    tests = aps_tests(observations, aps["latest_comparison"])
    outputs = {"paye_index": paye_series, "paye_summary": paye_summary, "bres_sectors": sectors,
               "bres_reconciliation": reconciliation, "shift_share_industries": details,
               "shift_share_gap": gaps, "sector_gap_contributions": sector_gaps,
               "within_section_composition": nested,
               "shift_share_summary": decompositions, "hourly_pay": earnings, "hourly_pay_comparison": earnings_comparison,
               "industry_pay_comparison": industry_pay, "aps_gap_tests": tests}
    for name, rows in outputs.items():
        analyse.write_csv(destination / f"tables/{name}.csv", rows)
    from reporting import charts, findings
    charts(destination / "figures", outputs)
    report_path = destination / "findings.md" if output_dir else ROOT / "documents/findings.md"
    report_path.write_text(findings(outputs, aps, manifest, bool(output_dir)), encoding="utf-8")
    result = {"aps_observations": aps["observations"], "source_rows": {k: len(v) for k, v in tables.items()},
              "aps_tests": tests, "paye_summary": paye_summary,
              "shift_share_summary": decompositions, "hourly_pay_comparison": earnings_comparison,
              "output_directory": str(destination)}
    (destination / "tables/research_summary.json").write_text(json.dumps(result | {"output_directory": "."}, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.output_dir)
        print(json.dumps({key: value for key, value in result.items() if key in {"aps_observations", "source_rows", "output_directory"}}, indent=2))
    except (ValueError, OSError, KeyError, StopIteration) as error:
        parser.exit(1, f"Research stopped: {error}\n")
