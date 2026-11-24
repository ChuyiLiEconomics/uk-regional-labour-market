"""Reproducible descriptive analysis of two English regional labour markets."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import sqlite3
import sys
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
QUERY = {"geography": ",".join(REGIONS), "time": "2015-01,latest", "variable": ",".join(INDICATORS), "measures": "20599,21003"}
SOURCE_URL = API + ".data.csv?" + urlencode(QUERY)
METHODS_URL = "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/methodologies/annualpopulationsurveyapsqmi"


def download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "UKRegionalLabourMarketPortfolio/0.1 (public ONS data analysis)"})
    with urlopen(request, timeout=45) as response:
        data = response.read(5_000_001)
    if not data or len(data) > 5_000_000:
        raise ValueError("Empty or unexpectedly large official response")
    return data


def source_snapshot() -> Path:
    """Store new immutable bytes and provenance; never change previous snapshots."""
    metadata = json.loads(download(API + "/def.sdmx.json"))
    family = metadata["structure"]["keyfamilies"]["keyfamily"][0]
    if family["id"] != DATASET or "annual population survey" not in family["name"]["value"].lower():
        raise ValueError("Unexpected source dataset")
    geography = json.loads(download(API + "/geography/" + ",".join(REGIONS) + ".def.sdmx.json"))
    codes = geography["structure"]["codelists"]["codelist"][0]["code"]
    for code, (name, _) in REGIONS.items():
        match = next((c for c in codes if str(c["value"]) == code), None)
        if not match or match["description"]["value"] != name:
            raise ValueError("Official geography definition changed")
    raw = download(SOURCE_URL)
    observations, quality = clean_csv(raw)  # validate before registering a snapshot
    sha = hashlib.sha256(raw).hexdigest()
    fetched_at = datetime.now(timezone.utc).isoformat()
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + sha[:12]
    raw_dir = ROOT / "data/raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    csv_name = f"nomis_{snapshot_id}.csv"
    (raw_dir / csv_name).write_bytes(raw)
    provenance = {
        "dataset": DATASET, "dataset_title": family["name"]["value"],
        "source_url": SOURCE_URL, "query": QUERY, "retrieved_at_utc": fetched_at,
        "sha256": sha, "bytes": len(raw), "csv_file": csv_name,
        "raw_rows": quality["source_rows"], "clean_rows": len(observations),
        "period_end_min": min(o["period_end"] for o in observations),
        "period_end_max": max(o["period_end"] for o in observations),
        "source_dataset_metadata": metadata, "source_geography_metadata": geography,
        "data_attribution": "Source: Office for National Statistics via Nomis. Contains public sector information licensed under the Open Government Licence v3.0.",
        "copyright_url": "https://www.nomisweb.co.uk/home/copyright.asp",
    }
    path = raw_dir / f"source_{snapshot_id}.json"
    path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    (ROOT / "data/latest_snapshot.json").write_text(json.dumps({"manifest": path.name}, indent=2), encoding="utf-8")
    return path


def number(text: str, status: str, *, rate: bool) -> float | None:
    # Never turn suppressed, unavailable or flagged data into zero or a valid rate.
    if status != "A" or not text.strip():
        return None
    try:
        value = float(text)
    except ValueError as error:
        raise ValueError("Non-numeric normal observation") from error
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError("Rate/confidence measure outside its valid range")
    return value


def clean_csv(raw: bytes) -> tuple[list[dict], dict]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    required = {"DATE", "DATE_NAME", "GEOGRAPHY", "GEOGRAPHY_NAME", "GEOGRAPHY_CODE", "GEOGRAPHY_TYPE", "VARIABLE", "VARIABLE_NAME", "MEASURES", "OBS_VALUE", "OBS_STATUS", "OBS_CONF", "RECORD_COUNT"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Official CSV schema is missing required columns")
    grouped: dict[tuple, dict] = {}
    seen = set()
    source_rows = 0
    advertised_counts = set()
    excluded_values = 0
    for row in reader:
        source_rows += 1
        advertised_counts.add(int(row["RECORD_COUNT"]))
        geography, variable, measure = row["GEOGRAPHY"], row["VARIABLE"], row["MEASURES"]
        if geography not in REGIONS or variable not in INDICATORS or measure not in {"20599", "21003"}:
            raise ValueError("Unexpected geography, variable or measure")
        name, ons_code = REGIONS[geography]
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
        value = number(row["OBS_VALUE"], row["OBS_STATUS"], rate=measure == "20599")
        excluded_values += value is None
        item = grouped.setdefault(key, {
            "period_end": row["DATE"], "period_label": row["DATE_NAME"],
            "region": name, "region_code": ons_code, "indicator": indicator,
            "rate_pct": None, "confidence_pp": None, "rate_status": "missing", "confidence_status": "missing",
        })
        if item["period_label"] != row["DATE_NAME"]:
            raise ValueError("Inconsistent reference period labels")
        prefix = "rate" if measure == "20599" else "confidence"
        item["rate_pct" if prefix == "rate" else "confidence_pp"] = value
        item[prefix + "_status"] = row["OBS_STATUS"]
    if source_rows == 0 or advertised_counts != {source_rows}:
        raise ValueError("Empty, truncated or inconsistent source response")
    observations = sorted(grouped.values(), key=lambda r: (r["period_end"], r["indicator"], r["region"]))
    if {r["region"] for r in observations} != {r[0] for r in REGIONS.values()}:
        raise ValueError("Missing requested region")
    # Completeness includes explicitly missing/suppressed values, which remain NULL.
    periods = {r["period_end"] for r in observations}
    if len(observations) != len(periods) * len(REGIONS) * len(INDICATORS) or source_rows != len(observations) * 2:
        raise ValueError("Source cube is incomplete")
    return observations, {"source_rows": source_rows, "clean_rows": len(observations), "excluded_or_missing_values": excluded_values, "periods": len(periods)}


SCHEMA = """
CREATE TABLE IF NOT EXISTS regions(code TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS indicators(id TEXT PRIMARY KEY, label TEXT NOT NULL, age_group TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS observations(
  period_end TEXT NOT NULL, period_label TEXT NOT NULL,
  region_code TEXT NOT NULL REFERENCES regions(code),
  indicator TEXT NOT NULL REFERENCES indicators(id),
  rate_pct REAL CHECK(rate_pct BETWEEN 0 AND 100), confidence_pp REAL CHECK(confidence_pp BETWEEN 0 AND 100),
  rate_status TEXT NOT NULL, confidence_status TEXT NOT NULL,
  PRIMARY KEY(period_end,region_code,indicator));
"""


def load_database(connection: sqlite3.Connection, observations: list[dict]) -> None:
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(SCHEMA)
    with connection:
        connection.execute("DELETE FROM observations")
        connection.execute("DELETE FROM regions")
        connection.execute("DELETE FROM indicators")
        connection.executemany("INSERT INTO regions VALUES (?,?)", [(code, name) for name, code in REGIONS.values()])
        connection.executemany("INSERT INTO indicators VALUES (?,?,?)", [(key, label, "16-64") for key, label in [v for v in INDICATORS.values()]])
        connection.executemany("INSERT INTO observations VALUES (:period_end,:period_label,:region_code,:indicator,:rate_pct,:confidence_pp,:rate_status,:confidence_status)", observations)


def summaries(connection: sqlite3.Connection) -> list[dict]:
    connection.row_factory = sqlite3.Row
    sql = (ROOT / "code/sql/latest_comparison.sql").read_text(encoding="utf-8")
    return [dict(r) for r in connection.execute(sql)]


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("Cannot export an empty table")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def charts(observations: list[dict], output: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    colors = {"North West": "#254B75", "West Midlands": "#A34A28"}
    for indicator, title in [("employment", "Employment rate"), ("inactivity", "Economic inactivity rate")]:
        fig, ax = plt.subplots(figsize=(10, 5.6), layout="constrained")
        for region, color in colors.items():
            subset = [r for r in observations if r["indicator"] == indicator and r["region"] == region]
            xs = [datetime.strptime(r["period_end"], "%Y-%m") for r in subset]
            ys = [r["rate_pct"] if r["rate_pct"] is not None else float("nan") for r in subset]
            ax.plot(xs, ys, label=region, color=color, linewidth=2)
            lower = [r["rate_pct"] - r["confidence_pp"] if r["rate_pct"] is not None and r["confidence_pp"] is not None else float("nan") for r in subset]
            upper = [r["rate_pct"] + r["confidence_pp"] if r["rate_pct"] is not None and r["confidence_pp"] is not None else float("nan") for r in subset]
            ax.fill_between(xs, lower, upper, color=color, alpha=0.12, linewidth=0)
        ax.set_title(f"{title} in two English regions", loc="left", fontweight="bold", pad=14)
        ax.set_ylabel("Population aged 16-64 (%)")
        ax.set_xlabel("End of 12-month survey period")
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.grid(axis="y", color="#E5E7EB", linewidth=0.7)
        ax.legend(frameon=False, loc="best")
        fig.supxlabel("ONS Annual Population Survey via Nomis | Shading: published approximate 95% intervals.\nRolling annual periods overlap; descriptive comparisons only.", fontsize=9)
        fig.savefig(output / f"{indicator}.png", dpi=180)
        plt.close(fig)


def report(rows: list[dict], provenance: dict, quality: dict) -> str:
    lines = ["# Regional labour market findings", "", "This descriptive comparison covers North West and West Midlands, England, for people aged 16-64. It does not estimate policy effects or hiring demand.", "", "## Latest comparable observations", "", "| Indicator | Survey period | North West (%) | West Midlands (%) | NW minus WM (pp) |", "|---|---|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['indicator'].capitalize()} | {r['period_label']} | {r['north_west_pct']:.1f} | {r['west_midlands_pct']:.1f} | {r['gap_pp']:+.1f} |")
    lines += ["", "The gap is a percentage-point difference between point estimates, not a causal effect or a claim of statistical significance. SQL selects the latest period with a non-missing rate in both regions for each indicator.", "", "## Interpretation and limitations", "", "- Employment and inactivity are distinct measures. Inactivity is not unemployment; unemployment rates use a different denominator.", "- Adjacent observations are overlapping 12-month survey periods, not independent quarterly observations. The x-axis records the end of each period.", "- Published approximate confidence intervals describe sampling uncertainty. No independence assumption is used to calculate a confidence interval for the regional gap.", "- ONS warns that smaller achieved APS samples can increase volatility and non-response concerns. Regional rates should be considered alongside other labour market indicators.", "- These are regional population estimates, not city estimates, counts of vacancies, employer demand or sponsorship availability.", "- Historical estimates may be revised. The local snapshot and its hash identify the bytes used for this run.", "", "## Provenance and quality checks", "", f"- Source: ONS Annual Population Survey via Nomis, `{DATASET}`.", f"- Retrieved at UTC: `{provenance['retrieved_at_utc']}`.", f"- Survey period ends: `{provenance['period_end_min']}` to `{provenance['period_end_max']}`.", f"- Source rows: {quality['source_rows']}; cleaned observations: {quality['clean_rows']}; periods: {quality['periods']}.", f"- Missing or non-normal measure cells retained as NULL: {quality['excluded_or_missing_values']}.", f"- Snapshot SHA-256: `{provenance['sha256']}`.", "- Validated geography names, ONS codes and region types; indicator definitions; duplicate keys; record count; free-for-publication flags; numeric bounds; and rate/confidence cube completeness.", "", f"[Exact source query]({provenance['source_url']}) · [ONS methodology]({METHODS_URL}) · [Nomis copyright](https://www.nomisweb.co.uk/home/copyright.asp)", "", "Contains public sector information licensed under the Open Government Licence v3.0.", ""]
    return "\n".join(lines)


def run(fetch: bool, snapshot: str | None) -> dict:
    if fetch and snapshot:
        raise ValueError("Choose --fetch or --snapshot, not both")
    if fetch:
        path = source_snapshot()
    elif snapshot:
        path = (ROOT / "data/raw" / snapshot).resolve()
        if path.parent != (ROOT / "data/raw").resolve():
            raise ValueError("Snapshot must be a filename inside data/raw")
    else:
        pointer = ROOT / "data/latest_snapshot.json"
        if not pointer.exists():
            raise ValueError("No downloaded snapshot. Run with --fetch first.")
        filename = json.loads(pointer.read_text(encoding="utf-8"))["manifest"]
        path = (ROOT / "data/raw" / filename).resolve()
        if path.parent != (ROOT / "data/raw").resolve():
            raise ValueError("Invalid snapshot pointer")
    provenance = json.loads(path.read_text(encoding="utf-8"))
    raw_path = (ROOT / "data/raw" / provenance["csv_file"]).resolve()
    if raw_path.parent != (ROOT / "data/raw").resolve():
        raise ValueError("Invalid source filename")
    raw = raw_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != provenance["sha256"]:
        raise ValueError("Raw snapshot hash mismatch")
    observations, quality = clean_csv(raw)
    for directory in ["data/clean", "output/tables", "output/figures", "documents"]:
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    write_csv(ROOT / "data/clean/observations.csv", observations)
    with sqlite3.connect(ROOT / "data/clean/labour_market.sqlite") as connection:
        load_database(connection, observations)
        summary = summaries(connection)
    if len(summary) != 2:
        raise ValueError("No shared valid period for each indicator")
    write_csv(ROOT / "output/tables/latest_comparison.csv", summary)
    charts(observations, ROOT / "output/figures")
    (ROOT / "documents/findings.md").write_text(report(summary, provenance, quality), encoding="utf-8")
    audit = {**quality, "source_manifest": path.name, "source_sha256": provenance["sha256"], "analysis_generated_at_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version}
    (ROOT / "output/tables/quality_checks.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return {"observations": len(observations), "latest_comparison": summary, "quality": quality}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="Download a fresh immutable official snapshot")
    parser.add_argument("--snapshot", help="Reuse one named source_*.json file in data/raw")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.fetch, args.snapshot), indent=2))
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"Analysis stopped: {error}\n")
