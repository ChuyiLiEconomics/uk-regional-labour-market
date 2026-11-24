# UK Regional Labour Market Analysis

A reproducible Python and SQL comparison of employment and economic inactivity in North West and West Midlands, England, using the ONS Annual Population Survey through Nomis.

**Author:** Chuyi Li, Economics PhD candidate. [GitHub profile](https://github.com/ChuyiLiEconomics).

The initial pipeline and eight data-integrity tests have run successfully. The author reproduced the cached-data analysis on 24 November 2026 and obtained the same observation counts and comparison values.

The project asks how two regional labour markets differ over time. It demonstrates official API data retrieval, validation, missing-data handling, SQLite joins and aggregation, time-series charts, and clear reporting of limitations. It does not measure vacancies or estimate causal policy effects.

## Outputs

![Regional employment rates](output/figures/employment.png)

![Regional inactivity rates](output/figures/inactivity.png)

See [generated findings and limitations](documents/findings.md), [latest comparison](output/tables/latest_comparison.csv) and [SQL query](code/sql/latest_comparison.sql).

## Run the analysis

Requires Python 3.12 or newer. The initial run was verified with Python 3.14 and Matplotlib 3.10.9. SQLite, CSV parsing, HTTP requests and tests use the Python standard library.

```sh
python -m venv .venv
# Activate .venv using the command appropriate for your operating system.
python -m pip install -r requirements.txt
python code/python/analyse.py --fetch
python -m unittest discover -s tests -v
```

On Windows, `py -3.14` can replace `python` if that is how Python is installed. Activate a PowerShell virtual environment with `.\.venv\Scripts\Activate.ps1`.

After downloading data, rerun offline with:

```sh
python code/python/analyse.py
```

To reproduce a named local snapshot:

```sh
python code/python/analyse.py --snapshot source_TIMESTAMP_HASH.json
```

Use an actual manifest filename from `data/raw`. Raw downloads are excluded from Git by default; a fresh clone downloads its own official snapshot, which may include later revisions. Exact historical reproduction requires retaining the named local raw snapshot and matching SHA-256 hash.

## Data and interpretation

- Source: [ONS Annual Population Survey on Nomis](https://www.nomisweb.co.uk/datasets/apsnew), API dataset `NM_17_5`.
- Regions: North West (`E12000002`), West Midlands (`E12000005`), checked against official metadata and every returned row.
- Indicators: employment rate and economic inactivity rate, both aged 16-64.
- Query: survey-period ends from January 2015 to the latest available period. The first returned annual window may begin in 2014; see the generated report for exact coverage.
- Adjacent observations are overlapping 12-month windows. They are not independent quarterly measurements.
- Shading shows the published approximate 95% confidence intervals. Regional point-estimate differences are not tested for significance.
- ONS warns about increased APS volatility and sampling limitations. Read the [ONS methodology](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/methodologies/annualpopulationsurveyapsqmi).

Contains public sector information licensed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Source: Office for National Statistics via Nomis. See [Nomis copyright](https://www.nomisweb.co.uk/home/copyright.asp). The data licence does not imply ONS endorsement. A software licence has not yet been selected.

## Project structure

```text
uk-regional-labour-market/
├── CLAUDE.md              # Project research and reproducibility rules
├── README.md              # Project overview and run instructions
├── requirements.txt
├── code/
│   ├── R/                 # Reserved
│   ├── python/            # Official-data analysis pipeline
│   ├── sql/               # Latest common-period comparison
│   └── stata/             # Reserved
├── data/
│   ├── raw/               # Immutable official snapshots; ignored by Git
│   └── clean/             # Derived CSV and SQLite database; ignored by Git
├── output/
│   ├── tables/            # Generated comparisons and quality checks
│   └── figures/           # Generated PNG charts
├── documents/             # Generated findings and methodology notes
├── decks/                 # Reserved; no presentation yet
├── notes/                 # Learning guide and analytical questions
├── progress_logs/         # Project progress and actual verification
└── tests/                 # Data integrity and SQL behaviour tests
```

## Authorship and development

Developed with AI coding assistance. Data sources, processing decisions and executed checks are documented in this repository. This is a portfolio study rather than commissioned professional work.

The next extension will be selected around a specific analytical question, with its data definitions and verification recorded alongside the results.
