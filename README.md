# UK Regional Labour Market Analysis

Employment and economic inactivity in England's North West and West Midlands, based on the ONS Annual Population Survey. The comparison covers people aged 16–64, using annual survey periods ending between March 2015 and June 2026.

## Results

For July 2025–June 2026, the latest period in this download:

| Indicator | North West | West Midlands | Difference |
|---|---:|---:|---:|
| Employment rate | 74.3% | 73.5% | +0.8 pp |
| Economic inactivity rate | 22.4% | 22.0% | +0.4 pp |

Differences are North West minus West Midlands, in percentage points. The charts show the full series, with the published approximate 95% confidence intervals shaded.

![Employment rates in the North West and West Midlands](output/figures/employment.png)

![Economic inactivity rates in the North West and West Midlands](output/figures/inactivity.png)

The estimates have sampling uncertainty. The regional differences have not been tested for statistical significance.

## Data and methods

Data come from the [ONS Annual Population Survey on Nomis](https://www.nomisweb.co.uk/datasets/apsnew), dataset `NM_17_5`. The download from 24 November 2026 contains 184 observations across 46 survey periods: two regions and two indicators for each period.

The Python script downloads the data, checks the region and indicator definitions, and saves a cleaned CSV and SQLite database. Missing or flagged values remain `NULL`. The SQL query compares the latest period with valid observations in both regions.

Each observation covers 12 months. Neighbouring periods overlap, so the lines should not be read as independent quarterly estimates. Employment and inactivity both refer to the population aged 16–64; inactivity is distinct from unemployment.

This is a descriptive comparison. It does not identify the causes of regional differences. ONS also advises caution when interpreting changes in APS estimates because of smaller sample sizes and increased volatility; see the [survey methodology](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/methodologies/annualpopulationsurveyapsqmi).

## Run

Requires Python 3.12 or newer. Tested with Python 3.14.4 and Matplotlib 3.10.9.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python code/python/analyse.py --fetch
```

After the first download, the saved data can be used offline:

```sh
python code/python/analyse.py
```

Run the tests with:

```sh
python -m unittest discover -s tests -v
```

On Windows, `py -3.14` can replace `python` when creating the environment.

Each download is saved in `data/raw/` with its query, retrieval time and SHA-256 hash. These local files are excluded from Git. A fresh download may contain revised estimates; reproducing an earlier run requires its saved snapshot. Use `--snapshot` followed by the filename of an existing `source_*.json` manifest to select one.

## Files

| File or folder | Contents |
|---|---|
| [code/python/analyse.py](code/python/analyse.py) | Download, cleaning, database loading and charts |
| [code/sql/latest_comparison.sql](code/sql/latest_comparison.sql) | Comparison of the latest common survey period |
| [output/figures/](output/figures/) | Employment and inactivity charts |
| [output/tables/latest_comparison.csv](output/tables/latest_comparison.csv) | Values used in the results table |
| [documents/findings.md](documents/findings.md) | Results, data checks and source details |
| [documents/verification.md](documents/verification.md) | Run and test records |
| [tests/test_integrity.py](tests/test_integrity.py) | Tests for missing data, source definitions and SQL comparisons |

## Credits

Source: Office for National Statistics via Nomis. Contains public sector information licensed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). See [Nomis copyright](https://www.nomisweb.co.uk/home/copyright.asp).

Code developed with AI assistance.
