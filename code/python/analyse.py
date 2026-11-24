"""Compare two English regional labour markets using ONS APS estimates."""
from __future__ import annotations

import argparse
import csv
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
DATASET = "NM_17_5"
API = f"https://www.nomisweb.co.uk/api/v01/dataset/{DATASET}"
REGIONS = {
    "2013265922": ("North West", "E12000002"),
    "2013265925": ("West Midlands", "E12000005"),
}
INDICATORS = {
    "45": ("employment", "Employment rate - aged 16-64"),
    "111": ("inactivity", "% who are economically inactive - aged 16-64"),
}
LABELS = {"employment": "Employment rate", "inactivity": "Economic inactivity rate"}
METHODS_URL = "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/methodologies/annualpopulationsurveyapsqmi"
FORMAT = "uk-regional-labour-market-snapshot-v1"


def download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "UKRegionalLabourMarketAnalysis/1.0"})
    with urlopen(request, timeout=45) as response:
        data = response.read(5_000_001)
    if not data or len(data) > 5_000_000:
        raise ValueError("Empty or unexpectedly large official response")
    return data


def validate_regions(regions: dict) -> None:
    if len(regions) != 2:
        raise ValueError("Select exactly two distinct English regions")
    ons_codes = []
    for code, details in regions.items():
        if not re.fullmatch(r"\d{10}", code) or not isinstance(details, (list, tuple)) or len(details) != 2:
            raise ValueError("Invalid region definition")
        name, ons_code = details
        if not name or not re.fullmatch(r"E1200000[1-9]", ons_code):
            raise ValueError("Select English statistical regions, not cities or countries")
        ons_codes.append(ons_code)
    if len(set(ons_codes)) != 2:
        raise ValueError("Regions must have different ONS codes")


def number(text: str, status: str) -> float | None:
    if status != "A" or not text.strip():
        return None
    try:
        value = float(text)
    except ValueError as error:
        raise ValueError("Non-numeric normal observation") from error
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError("Rate/confidence measure outside its valid range")
    return value


def clean_csv(raw: bytes, regions: dict | None = None) -> tuple[list[dict], dict]:
    regions = REGIONS if regions is None else regions
    validate_regions(regions)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    required = {"DATE", "DATE_NAME", "GEOGRAPHY", "GEOGRAPHY_NAME", "GEOGRAPHY_CODE", "GEOGRAPHY_TYPE",
                "VARIABLE", "VARIABLE_NAME", "MEASURES", "OBS_VALUE", "OBS_STATUS", "OBS_CONF", "RECORD_COUNT"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Official CSV schema is missing required columns")
    grouped, seen, advertised_counts = {}, set(), set()
    source_rows = excluded_values = 0
    for row in reader:
        source_rows += 1
        advertised_counts.add(int(row["RECORD_COUNT"]))
        geography, variable, measure = row["GEOGRAPHY"], row["VARIABLE"], row["MEASURES"]
        if geography not in regions or variable not in INDICATORS or measure not in {"20599", "21003"}:
            raise ValueError("Unexpected geography, variable or measure")
        name, ons_code = regions[geography]
        if (row["GEOGRAPHY_NAME"], row["GEOGRAPHY_CODE"], row["GEOGRAPHY_TYPE"]) != (name, ons_code, "regions"):
            raise ValueError("Geography code/name/type mismatch")
        indicator, variable_name = INDICATORS[variable]
        if row["VARIABLE_NAME"] != variable_name:
            raise ValueError("Indicator definition mismatch")
        if row["OBS_CONF"] != "F":
            raise ValueError("Observation not marked free for publication")
        datetime.strptime(row["DATE"], "%Y-%m")
        key = (row["DATE"], geography, variable)
        full_key = (*key, measure)
        if full_key in seen:
            raise ValueError("Duplicate observation key")
        seen.add(full_key)
        value = number(row["OBS_VALUE"], row["OBS_STATUS"])
        excluded_values += value is None
        item = grouped.setdefault(key, {
            "period_end": row["DATE"], "period_label": row["DATE_NAME"], "region": name,
            "region_code": ons_code, "indicator": indicator, "rate_pct": None, "confidence_pp": None,
            "rate_status": "missing", "confidence_status": "missing",
        })
        if item["period_label"] != row["DATE_NAME"]:
            raise ValueError("Inconsistent reference period labels")
        prefix = "rate" if measure == "20599" else "confidence"
        item["rate_pct" if prefix == "rate" else "confidence_pp"] = value
        item[prefix + "_status"] = row["OBS_STATUS"]
    if source_rows == 0 or advertised_counts != {source_rows}:
        raise ValueError("Empty, truncated or inconsistent source response")
    observations = sorted(grouped.values(), key=lambda r: (r["period_end"], r["indicator"], r["region"]))
    periods = {r["period_end"] for r in observations}
    if len(observations) != len(periods) * len(regions) * len(INDICATORS) or source_rows != len(observations) * 2:
        raise ValueError("Source cube is incomplete")
    return observations, {
        "source_rows": source_rows, "clean_rows": len(observations),
        "excluded_or_missing_values": excluded_values, "periods": len(periods),
    }


def load_snapshot(directory: Path) -> tuple[list[dict], dict, dict, dict]:
    directory = directory.resolve()
    manifest = json.loads((directory / "source.json").read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT or manifest.get("dataset") != DATASET:
        raise ValueError("Unrecognised snapshot format")
    raw_path = (directory / manifest["raw_file"]).resolve()
    if raw_path.parent != directory:
        raise ValueError("Snapshot file must remain inside its directory")
    raw = raw_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["sha256"]:
        raise ValueError("Raw snapshot hash mismatch")
    regions = manifest["regions"]
    observations, quality = clean_csv(raw, regions)
    if any(quality[key] != manifest[key] for key in ["source_rows", "clean_rows"]):
        raise ValueError("Snapshot row counts do not match metadata")
    return observations, regions, manifest, quality


def fetch_snapshot(region_ids: list[str], start: str) -> Path:
    if len(region_ids) != 2 or len(set(region_ids)) != 2 or not all(re.fullmatch(r"\d{10}", x) for x in region_ids):
        raise ValueError("Select exactly two distinct Nomis region IDs")
    datetime.strptime(start, "%Y-%m")
    dataset_metadata = json.loads(download(API + "/def.sdmx.json"))
    family = dataset_metadata["structure"]["keyfamilies"]["keyfamily"][0]
    if family["id"] != DATASET or "annual population survey" not in family["name"]["value"].lower():
        raise ValueError("Unexpected source dataset")
    metadata = json.loads(download(API + "/geography/" + ",".join(region_ids) + ".def.sdmx.json"))
    codes = metadata["structure"]["codelists"]["codelist"][0]["code"]
    regions = {}
    for region_id in region_ids:
        item = next((c for c in codes if str(c["value"]) == region_id), None)
        if not item:
            raise ValueError("Requested geography not found")
        annotations = {a["annotationtitle"]: a["annotationtext"] for a in item.get("annotations", {}).get("annotation", [])}
        if annotations.get("TypeName") != "regions":
            raise ValueError("Requested geography is not a statistical region")
        regions[region_id] = [item["description"]["value"], str(annotations.get("GeogCode", ""))]
    validate_regions(regions)
    query = {"geography": ",".join(region_ids), "time": f"{start},latest",
             "variable": ",".join(INDICATORS), "measures": "20599,21003"}
    url = API + ".data.csv?" + urlencode(query)
    raw = download(url)
    observations, quality = clean_csv(raw, regions)
    source_annotations = {a["annotationtitle"]: a["annotationtext"] for a in family.get("annotations", {}).get("annotation", [])}
    now = datetime.now(timezone.utc)
    sha = hashlib.sha256(raw).hexdigest()
    destination = ROOT / "data/local" / (now.strftime("%Y%m%dT%H%M%S%fZ") + "_" + sha[:12])
    destination.mkdir(parents=True)
    manifest = {
        "format": FORMAT, "dataset": DATASET, "raw_file": "nomis.csv", "sha256": sha,
        "retrieved_at_utc": now.isoformat(), "source_last_updated": source_annotations.get("LastUpdated"),
        "source_url": url, "query": query, "regions": regions,
        "source_rows": quality["source_rows"], "clean_rows": len(observations),
        "period_end_min": min(r["period_end"] for r in observations),
        "period_end_max": max(r["period_end"] for r in observations),
        "attribution": "Source: Office for National Statistics via Nomis. Contains public sector information licensed under the Open Government Licence v3.0.",
        "copyright_url": "https://www.nomisweb.co.uk/home/copyright.asp",
    }
    (destination / "nomis.csv").write_bytes(raw)
    (destination / "source.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return destination


SCHEMA = """
CREATE TABLE regions(code TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE indicators(id TEXT PRIMARY KEY, label TEXT NOT NULL, age_group TEXT NOT NULL);
CREATE TABLE observations(
    period_end TEXT NOT NULL, period_label TEXT NOT NULL,
    region_code TEXT NOT NULL REFERENCES regions(code),
    indicator TEXT NOT NULL REFERENCES indicators(id),
    rate_pct REAL CHECK(rate_pct BETWEEN 0 AND 100),
    confidence_pp REAL CHECK(confidence_pp BETWEEN 0 AND 100),
    rate_status TEXT NOT NULL, confidence_status TEXT NOT NULL,
    PRIMARY KEY(period_end, region_code, indicator));
"""


def load_database(connection: sqlite3.Connection, observations: list[dict], regions: dict | None = None) -> None:
    regions = REGIONS if regions is None else regions
    validate_regions(regions)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(SCHEMA)
    with connection:
        connection.executemany("INSERT INTO regions VALUES (?,?)", [(code, name) for name, code in regions.values()])
        connection.executemany("INSERT INTO indicators VALUES (?,?,?)", [(key, label, "16-64") for key, label in INDICATORS.values()])
        connection.executemany(
            "INSERT INTO observations VALUES (:period_end,:period_label,:region_code,:indicator,:rate_pct,:confidence_pp,:rate_status,:confidence_status)",
            observations,
        )


def summaries(connection: sqlite3.Connection, regions: dict | None = None) -> tuple[list[dict], list[dict]]:
    regions = REGIONS if regions is None else regions
    ons_codes = [details[1] for details in regions.values()]
    connection.row_factory = sqlite3.Row
    period_sql = (ROOT / "code/sql/period_comparisons.sql").read_text(encoding="utf-8")
    connection.execute("DROP TABLE IF EXISTS temp.period_comparisons")
    connection.execute("CREATE TEMP TABLE period_comparisons AS " + period_sql,
                       {"region_a": ons_codes[0], "region_b": ons_codes[1]})
    periods = [dict(r) for r in connection.execute("SELECT * FROM period_comparisons ORDER BY indicator,period_end")]
    latest_sql = (ROOT / "code/sql/latest_comparison.sql").read_text(encoding="utf-8")
    latest = [dict(r) for r in connection.execute(latest_sql)]
    return periods, latest


def baseline_changes(periods: list[dict], latest: list[dict], baseline: str) -> list[dict]:
    changes = []
    for current in latest:
        previous = next((r for r in periods if r["indicator"] == current["indicator"] and r["period_end"] == baseline), None)
        changes.append({
            "indicator": current["indicator"], "region_a": current["region_a"], "region_b": current["region_b"],
            "baseline_period_end": baseline, "baseline_period_label": previous["period_label"] if previous else "",
            "latest_period_end": current["period_end"], "latest_period_label": current["period_label"],
            "baseline_region_a_pct": previous["region_a_pct"] if previous else None,
            "baseline_region_b_pct": previous["region_b_pct"] if previous else None,
            "latest_region_a_pct": current["region_a_pct"], "latest_region_b_pct": current["region_b_pct"],
            "change_region_a_pp": round(current["region_a_pct"] - previous["region_a_pct"], 2) if previous else None,
            "change_region_b_pp": round(current["region_b_pct"] - previous["region_b_pct"], 2) if previous else None,
            "baseline_gap_pp": previous["gap_pp"] if previous else None, "latest_gap_pp": current["gap_pp"],
            "change_in_gap_pp": round(current["gap_pp"] - previous["gap_pp"], 2) if previous else None,
        })
    return changes


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("Cannot export an empty table")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def charts(observations: list[dict], regions: dict, periods: list[dict], destination: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    names = [v[0] for v in regions.values()]
    colors = ["#254B75", "#A34A28"]
    for indicator, title in LABELS.items():
        fig, ax = plt.subplots(figsize=(10, 5.5))
        fig.subplots_adjust(left=0.11, right=0.97, bottom=0.20, top=0.88)
        for name, color in zip(names, colors):
            selected = [r for r in observations if r["indicator"] == indicator and r["region"] == name]
            dates = [datetime.strptime(r["period_end"], "%Y-%m") for r in selected]
            values = [r["rate_pct"] if r["rate_pct"] is not None else float("nan") for r in selected]
            ax.plot(dates, values, color=color, linewidth=2, label=name)
            lower = [r["rate_pct"] - r["confidence_pp"] if r["rate_pct"] is not None and r["confidence_pp"] is not None else float("nan") for r in selected]
            upper = [r["rate_pct"] + r["confidence_pp"] if r["rate_pct"] is not None and r["confidence_pp"] is not None else float("nan") for r in selected]
            ax.fill_between(dates, lower, upper, color=color, alpha=0.12, linewidth=0)
        ax.set_title(title, loc="left", fontweight="bold", fontsize=16, pad=14)
        ax.set_ylabel("People aged 16-64 (%)")
        ax.set_xlabel("End of 12-month survey period")
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.grid(axis="y", color="#E5E7EB")
        ax.legend(frameon=False, loc="best")
        fig.text(0.11, 0.045, "Source: ONS Annual Population Survey via Nomis.\nShading: published approximate 95% confidence intervals. Adjacent annual periods overlap.", fontsize=9)
        fig.savefig(destination / f"{indicator}.png", dpi=180)
        plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    fig.subplots_adjust(left=0.12, right=0.97, bottom=0.19, top=0.87, hspace=0.30)
    fig.suptitle("Regional differences", x=0.12, ha="left", fontsize=17, fontweight="bold")
    for ax, (indicator, label) in zip(axes, LABELS.items()):
        selected = [r for r in periods if r["indicator"] == indicator]
        ax.plot([datetime.strptime(r["period_end"], "%Y-%m") for r in selected],
                [r["gap_pp"] for r in selected], color="#563A77", linewidth=2)
        ax.axhline(0, color="#777777", linewidth=1, linestyle="--")
        ax.set_title(label, loc="left", fontsize=11)
        ax.set_ylabel("Percentage points")
        ax.grid(axis="y", color="#E5E7EB")
    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[-1].set_xlabel("End of 12-month survey period")
    fig.text(0.12, 0.05, f"Difference: {names[0]} minus {names[1]}.\nSource: ONS APS via Nomis. Overlapping annual estimates; differences are not significance tests.", fontsize=9)
    fig.savefig(destination / "regional_gaps.png", dpi=180)
    plt.close(fig)


def relative(value: float) -> str:
    if value == 0:
        return "was unchanged"
    return f"{'rose' if value > 0 else 'fell'} by {abs(value):.1f} percentage points"


def report(periods: list[dict], latest: list[dict], changes: list[dict], manifest: dict, quality: dict) -> str:
    names = [v[0] for v in manifest["regions"].values()]
    a, b = names
    lines = ["# Regional labour market comparisons", "",
             f"Employment and economic inactivity in {a} and {b}, for people aged 16–64. "
             "The analysis compares the latest annual estimates with a fixed baseline and follows the regional gap through the full series.", "",
             "## Latest estimates", "",
             "| Indicator | Survey period | " + a + " (%) | " + b + " (%) | Difference (pp) |",
             "|---|---|---:|---:|---:|"]
    for row in latest:
        lines.append(f"| {LABELS[row['indicator']]} | {row['period_label']} | {row['region_a_pct']:.1f} | {row['region_b_pct']:.1f} | {row['gap_pp']:+.1f} |")
    lines += ["", f"Differences throughout this report are {a} minus {b}.", "", "## Comparison with the baseline", ""]
    for change in changes:
        if change["change_region_a_pp"] is None:
            lines.append(f"{LABELS[change['indicator']]}: no common valid observation is available for baseline {change['baseline_period_end']}. No earlier period has been substituted.")
        else:
            lines.append(f"Between {change['baseline_period_label']} and {change['latest_period_label']}, "
                         f"the {LABELS[change['indicator']].lower()} in {a} {relative(change['change_region_a_pp'])}; "
                         f"in {b} it {relative(change['change_region_b_pp'])}. "
                         f"The regional gap changed from {change['baseline_gap_pp']:+.1f} to {change['latest_gap_pp']:+.1f} percentage points.")
        lines.append("")
    lines += ["## How the gap changed", ""]
    for indicator, label in LABELS.items():
        selected = [r for r in periods if r["indicator"] == indicator]
        low = min(selected, key=lambda r: r["gap_pp"])
        high = max(selected, key=lambda r: r["gap_pp"])
        lines += [f"The {label.lower()} gap ranged from {low['gap_pp']:+.1f} percentage points "
                  f"(first reached in {low['period_label']}) to {high['gap_pp']:+.1f} "
                  f"(first reached in {high['period_label']}).", ""]
    lines += ["![Regional differences](../output/figures/regional_gaps.png)", "",
              "A latest-period ranking can therefore hide earlier reversals. The gap chart records the direction and scale "
              "of those differences; it does not establish that any reversal is statistically significant.", "",
              "## Scope and interpretation", "",
              "The two regions form a descriptive case study, not a matched treatment and control group. Calendar 2019 is "
              "the default pre-pandemic reference period; a different baseline can be selected explicitly. A baseline is "
              "a comparison point, not an estimated counterfactual.", "",
              "Each estimate covers 12 months and neighbouring windows overlap. The published approximate confidence "
              "intervals describe uncertainty around each regional rate. No independence assumption is used to construct "
              "an interval for the difference or its change over time.", "",
              "ONS advises additional caution with APS changes because of response rates, weighting and increased "
              "volatility. These series alone cannot distinguish changes within population groups from changes in age "
              "or other population composition. Age-specific estimates, reasons for inactivity and administrative "
              "employment data would be needed to examine those explanations.", "",
              "## Data", "",
              f"- ONS Annual Population Survey via Nomis, dataset {DATASET}.",
              f"- Downloaded: {manifest['retrieved_at_utc']}.",
              f"- Source dataset update recorded by Nomis: {manifest.get('source_last_updated', 'not recorded')}.",
              f"- Period ends: {manifest['period_end_min']} to {manifest['period_end_max']}.",
              f"- {quality['source_rows']} source measure rows; {quality['clean_rows']} observations; {quality['periods']} survey periods.",
              f"- Missing or non-normal measure cells retained as NULL: {quality['excluded_or_missing_values']}.", "",
              f"[Source query]({manifest['source_url']}) · [ONS methodology]({METHODS_URL})", "",
              "The original public aggregate download and metadata are included in data/snapshot. The cleaned full "
              "series, all common-period comparisons and baseline changes are available under output/tables.", ""]
    return "\n".join(lines)


def run(fetch: bool = False, snapshot: str | None = None, region_ids: list[str] | None = None,
        start: str = "2015-01", baseline: str = "2019-12", output_dir: str | None = None) -> dict:
    datetime.strptime(baseline, "%Y-%m")
    if fetch and snapshot:
        raise ValueError("Choose --fetch or --snapshot, not both")
    if region_ids and not fetch:
        raise ValueError("--regions requires --fetch; saved snapshots retain their own region definitions")
    snapshot_path = fetch_snapshot(region_ids or list(REGIONS), start) if fetch else Path(snapshot or ROOT / "data/snapshot")
    observations, regions, manifest, quality = load_snapshot(snapshot_path)
    with closing(sqlite3.connect(":memory:")) as connection:
        load_database(connection, observations, regions)
        periods, latest = summaries(connection, regions)
    if len(latest) != len(INDICATORS):
        raise ValueError("No shared valid period for each indicator")
    changes = baseline_changes(periods, latest, baseline)
    destination = Path(output_dir).resolve() if output_dir else ROOT / ("output/local" if fetch or snapshot else "output")
    for folder in ["tables", "figures"]:
        (destination / folder).mkdir(parents=True, exist_ok=True)
    write_csv(destination / "tables/observations.csv", observations)
    write_csv(destination / "tables/period_comparisons.csv", periods)
    write_csv(destination / "tables/latest_comparison.csv", latest)
    write_csv(destination / "tables/baseline_changes.csv", changes)
    charts(observations, regions, periods, destination / "figures")
    text = report(periods, latest, changes, manifest, quality)
    if destination == ROOT / "output":
        report_path = ROOT / "documents/findings.md"
    else:
        report_path = destination / "findings.md"
        text = text.replace("../output/figures/", "figures/")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(text, encoding="utf-8")
    return {"observations": len(observations), "regions": [v[0] for v in regions.values()],
            "latest_comparison": latest, "baseline_changes": changes, "quality": quality,
            "output_directory": str(destination), "snapshot_directory": str(snapshot_path.resolve())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="Download current official estimates into data/local")
    parser.add_argument("--snapshot", help="Directory containing nomis.csv and source.json")
    parser.add_argument("--regions", nargs=2, metavar=("REGION_A", "REGION_B"), help="Two Nomis English-region IDs; requires --fetch")
    parser.add_argument("--start", default="2015-01", help="First survey-period end to request with --fetch")
    parser.add_argument("--baseline", default="2019-12", help="Exact survey-period end used as baseline")
    parser.add_argument("--output-dir", help="Directory for generated tables, figures and findings")
    args = parser.parse_args()
    try:
        result = run(args.fetch, args.snapshot, args.regions, args.start, args.baseline, args.output_dir)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"Analysis stopped: {error}\n")
