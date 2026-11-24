# Verification on 24 November 2026

The local version was run with Python 3.14.4, SQLite 3.50.4 and Matplotlib 3.10.9.

## Executed checks

- `python code/python/analyse.py --fetch`: succeeded with official Nomis data. 368 source measure rows became 184 region-indicator-period observations across 46 survey periods.
- `python code/python/analyse.py`: offline rerun succeeded with the recorded snapshot hash and the same comparison values.
- `python -m unittest discover -s tests -v`: 8 tests passed. The tests cover missing and suppressed values, incorrect geography and indicator definitions, duplicate keys, truncated downloads, publication flags, invalid numbers, and common-period SQL comparisons. Test fixtures are synthetic and are not used as project findings.
- Both generated PNG charts and the findings report were inspected.
- On 24 November 2026, the author ran the cached-data pipeline and supplied matching results: 184 observations, 368 source rows, 46 periods, employment rates of 74.3% and 73.5%, and inactivity rates of 22.4% and 22.0%.

## Remaining review

The author has reproduced the cached-data analysis and reviewed the treatment of missing values and common-period comparisons. A fuller walkthrough remains available in `notes/learning-guide.md`. This is an AI-assisted portfolio project, not evidence of prior independent professional delivery.

The tests establish specific data-processing safeguards. They do not independently validate ONS estimates, test causality or establish statistical significance of regional differences.
