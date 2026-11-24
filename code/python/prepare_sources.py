"""Prepare public research inputs from pinned ONS and Nomis downloads."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "data/extended"
REGIONS = {f"E1200000{i}": name for i, name in enumerate([
    "North East", "North West", "Yorkshire and The Humber", "East Midlands",
    "West Midlands", "East", "London", "South East", "South West"], start=1)}
FOCUS = {"E12000002": "North West", "E12000005": "West Midlands"}
YEARS = {2019: "revised", 2024: "revised", 2025: "revised", 2026: "provisional"}


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def numeric(value):
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    text = str(value).strip()
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return float(text)
    return None


def clean_text(value) -> str:
    return str(value).strip().lstrip("'").strip()


def bres_rows(content: bytes) -> list[dict]:
    source = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    if not source or {int(r["RECORD_COUNT"]) for r in source} != {len(source)}:
        raise ValueError("BRES response is empty or incomplete")
    result, keys = [], set()
    for number, row in enumerate(source, start=2):
        code = row["GEOGRAPHY_CODE"]
        division = row["INDUSTRY_CODE"] if row["INDUSTRY_NAME"] != "Total" else "TOTAL"
        key = (row["DATE"], code, division)
        if key in keys:
            raise ValueError("Duplicate BRES observation")
        keys.add(key)
        if (code not in REGIONS or row["GEOGRAPHY_NAME"] != REGIONS[code] or
                row["GEOGRAPHY_TYPE"] != "regions" or row["EMPLOYMENT_STATUS_NAME"] != "Employees" or
                row["MEASURE_NAME"] != "Count" or row["MEASURES"] != "20100" or row["OBS_CONF"] != "F"):
            raise ValueError("BRES source definitions or publication flags changed")
        if division != "TOTAL" and (row["INDUSTRY_TYPE"] != "SIC 2007 division (2 digit)" or not re.fullmatch(r"\d{2}", division)):
            raise ValueError("Unexpected BRES industry classification")
        value = numeric(row["OBS_VALUE"]) if row["OBS_STATUS"] == "A" else None
        if value is not None and value < 0:
            raise ValueError("Negative employee count")
        result.append({"year": int(row["DATE"]), "region": REGIONS[code], "region_code": code,
                       "division": division, "division_label": row["INDUSTRY_NAME"], "employees": value,
                       "source_status": row["OBS_STATUS"], "source_row": number})
    expected_years = set(range(2018, 2025))
    if {r["year"] for r in result} != expected_years:
        raise ValueError("BRES pinned year coverage changed")
    groups = {(r["year"], r["region_code"]) for r in result}
    if len(groups) != len(expected_years) * len(REGIONS):
        raise ValueError("Missing BRES region-year")
    categories = {r["division"] for r in result}
    if len(result) != len(groups) * len(categories):
        raise ValueError("Missing BRES industry cell")
    return result


def rti_rows(filename: Path) -> list[dict]:
    import pandas as pd
    with pd.ExcelFile(filename) as workbook:
        frame = pd.read_excel(workbook, sheet_name="7. Employees (NUTS1)", header=None).fillna("")
        if frame.iloc[0, 0] != "7. Payrolled employees from PAYE RTI" or frame.iloc[1, 0] != "All industries, seasonally adjusted":
            raise ValueError("PAYE table definition changed")
        if frame.iloc[3, 1] != "Payrolled employees":
            raise ValueError("PAYE units changed")
        columns = {}
        for column in range(1, 10):
            name = clean_text(frame.iloc[6, column])
            expected = REGIONS[f"E1200000{column}"]
            if name != expected:
                raise ValueError("PAYE region order changed")
            columns[column] = (f"E1200000{column}", name)
        dates = []
        for position in range(7, len(frame)):
            try:
                period = datetime.strptime(clean_text(frame.iloc[position, 0]), "%B %Y").strftime("%Y-%m")
            except ValueError:
                continue
            dates.append((position, period))
        if len({period for _, period in dates}) != len(dates):
            raise ValueError("Duplicate PAYE month")
        latest = max(period for _, period in dates)
        if latest != "2026-10":
            raise ValueError("Pinned PAYE reference month changed")
        result = []
        for position, period in dates:
            for column, (code, name) in columns.items():
                value = numeric(frame.iloc[position, column])
                if value is None or value <= 0:
                    raise ValueError("PAYE count is missing or non-positive")
                result.append({"period": period, "region": name, "region_code": code,
                               "payrolled_employees": value, "is_early": int(period == latest),
                               "source_sheet": "7. Employees (NUTS1)",
                               "source_cell": f"{chr(65 + column)}{position + 1}"})
        return result


def ashe_rows(filename: Path, year: int) -> list[dict]:
    import pandas as pd
    result = []
    with zipfile.ZipFile(filename) as archive:
        names = {}
        for kind in ["a", "b"]:
            matches = [n for n in archive.namelist() if re.search(r"5\.6" + kind + r"\s", n)]
            if len(matches) != 1:
                raise ValueError("ASHE hourly-pay workbook is missing or ambiguous")
            names[kind] = matches[0]
        with pd.ExcelFile(io.BytesIO(archive.read(names["a"]))) as estimates, pd.ExcelFile(io.BytesIO(archive.read(names["b"]))) as cvs:
            for sheet, pattern in [("All", "all"), ("Full-Time", "full_time"), ("Part-Time", "part_time")]:
                frame = pd.read_excel(estimates, sheet_name=sheet, header=None).fillna("")
                quality = pd.read_excel(cvs, sheet_name=sheet, header=None).fillna("")
                if "Hourly pay - Excluding overtime" not in str(frame.iloc[0, 0]) or str(year) not in str(frame.iloc[0, 0]):
                    raise ValueError("ASHE measure/year definition changed")
                if list(frame.iloc[4, :4]) != ["Description", "Code", "(thousand)", "Median"]:
                    raise ValueError("ASHE source columns changed")
                if frame.shape != quality.shape:
                    raise ValueError("ASHE estimates and CVs are not aligned")
                seen = set()
                for position in range(5, len(frame)):
                    description = clean_text(frame.iloc[position, 0])
                    code = clean_text(frame.iloc[position, 1])
                    region_code = code if code in FOCUS else None
                    industry = "ALL" if region_code else None
                    for focus_code, region_name in FOCUS.items():
                        if description.upper().startswith(region_name.upper() + ",") and re.fullmatch("[A-S]", code):
                            region_code, industry = focus_code, code
                    if region_code is None:
                        continue
                    if (description, code) != (clean_text(quality.iloc[position, 0]), clean_text(quality.iloc[position, 1])):
                        raise ValueError("ASHE CV row does not match estimate row")
                    key = (region_code, industry)
                    if key in seen:
                        raise ValueError("Duplicate ASHE regional industry")
                    seen.add(key)
                    median, cv = numeric(frame.iloc[position, 3]), numeric(quality.iloc[position, 3])
                    if median is not None and median <= 0 or cv is not None and cv < 0:
                        raise ValueError("Invalid ASHE earnings or CV")
                    result.append({"year": year, "vintage": YEARS[year], "region": FOCUS[region_code],
                                   "region_code": region_code, "work_pattern": pattern, "industry": industry,
                                   "industry_label": description, "median_gbp_per_hour": median, "median_cv_pct": cv,
                                   "median_source_value": str(frame.iloc[position, 3]),
                                   "cv_source_value": str(quality.iloc[position, 3]),
                                   "p10_gbp_per_hour": numeric(frame.iloc[position, 7]),
                                   "p90_gbp_per_hour": numeric(frame.iloc[position, 16]),
                                   "source_workbook": names["a"], "cv_workbook": names["b"],
                                   "source_sheet": sheet, "source_row": position + 1})
                if len(seen) != len(FOCUS) * 20:
                    raise ValueError("ASHE region/industry coverage changed")
    return result


def cpih_rows(content: bytes) -> list[dict]:
    rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
    if ["CDID", "L522"] not in rows or ["Unit", "Index, base year = 100"] not in rows:
        raise ValueError("CPIH series definition changed")
    result = []
    for number, row in enumerate(rows, start=1):
        if not row or not re.fullmatch(r"\d{4} [A-Z]{3}", row[0]):
            continue
        period = datetime.strptime(row[0], "%Y %b").strftime("%Y-%m")
        if period < "2018-01":
            continue
        value = numeric(row[1])
        if value is None or value <= 0:
            raise ValueError("Missing CPIH index")
        result.append({"period": period, "cpih_index": value, "source_row": number})
    if not result or len({r["period"] for r in result}) != len(result):
        raise ValueError("Empty or duplicate CPIH months")
    return result


def write_csv(path: Path, rows: list[dict]) -> dict:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return {"sha256": digest(path.read_bytes()), "rows": len(rows)}


def prepare(source_dir: Path, fetch: bool = False) -> dict:
    manifest = json.loads((DESTINATION / "sources.json").read_text(encoding="utf-8"))
    source_dir.mkdir(parents=True, exist_ok=True)
    for name, item in manifest["downloads"].items():
        target = source_dir / name
        if fetch and not target.exists():
            with urlopen(Request(item["source_url"], headers={"User-Agent": "UKRegionalLabourMarketAnalysis/2.0"}), timeout=60) as response:
                content = response.read(50_000_001)
            if not content or len(content) > 50_000_000 or digest(content) != item["sha256"]:
                raise ValueError(f"Official file {name} no longer matches this vintage; use the included prepared inputs")
            target.write_bytes(content)
        if digest(target.read_bytes()) != item["sha256"]:
            raise ValueError(f"Original source hash mismatch: {name}")
    tables = {
        "bres.csv": bres_rows((source_dir / "bres.csv").read_bytes()),
        "paye.csv": rti_rows(source_dir / "rti.xlsx"),
        "ashe.csv": [row for year in YEARS for row in ashe_rows(source_dir / f"ashe{year}.zip", year)],
        "cpih.csv": cpih_rows((source_dir / "cpih.csv").read_bytes()),
    }
    manifest["prepared_inputs"] = {name: write_csv(DESTINATION / name, rows) for name, rows in tables.items()}
    (DESTINATION / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest["prepared_inputs"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data/local/extension")
    parser.add_argument("--fetch", action="store_true", help="Download missing pinned original files")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.source_dir, args.fetch), indent=2))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Source preparation stopped: {error}\n")
