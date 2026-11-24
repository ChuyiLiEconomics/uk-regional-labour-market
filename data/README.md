# Data

The source is the [ONS Annual Population Survey on Nomis](https://www.nomisweb.co.uk/datasets/apsnew), dataset `NM_17_5`. Only public regional aggregates are included.

## Included snapshot

[`snapshot/nomis.csv`](snapshot/nomis.csv) contains the original response. [`snapshot/source.json`](snapshot/source.json) records the query, region definitions, retrieval time and SHA-256 hash. The default analysis verifies that hash before reading the data.

| Item | Value |
|---|---|
| Retrieved | 24 November 2026, 16:09 UTC |
| Dataset update recorded by Nomis | 20 October 2026, 07:00 |
| Survey-period ends | March 2015–June 2026 |
| Regions | North West (`E12000002`), West Midlands (`E12000005`) |
| Variables | Employment rate (`45`); economic inactivity rate (`111`), both aged 16–64 |
| Measures | Rate (`20599`); published approximate 95% confidence-interval half-width (`21003`) |
| Rows | 368 source measure rows; 184 cleaned observations |

The retrieval date, source update date and survey reference periods describe different events. A later API download may revise these estimates.

[Exact source query](https://www.nomisweb.co.uk/api/v01/dataset/NM_17_5.data.csv?geography=2013265922%2C2013265925&time=2015-01%2Clatest&variable=45%2C111&measures=20599%2C21003).

## Cleaned observations

[`output/tables/observations.csv`](../output/tables/observations.csv) has one row per period, region and indicator.

| Field | Meaning |
|---|---|
| `period_end` | End of the annual survey window, `YYYY-MM` |
| `period_label` | Full survey window as supplied by Nomis |
| `region`, `region_code` | Region name and ONS code |
| `indicator` | `employment` or `inactivity` |
| `rate_pct` | Percentage of the population aged 16–64 |
| `confidence_pp` | Published approximate 95% confidence-interval half-width, in percentage points |
| `rate_status`, `confidence_status` | Original Nomis observation-status codes |

Only status `A` with a finite numeric value is used. Other statuses and blank values become empty CSV cells (`NULL` in SQLite), never zero. The bundled snapshot has no excluded or missing measure cells. Rows with non-public confidentiality flags, mismatched source definitions or duplicate keys are rejected.

The comparison tables use `region_a` and `region_b` in the selected order. `gap_pp` is A minus B; baseline changes are latest minus baseline. Comparisons require valid rates in both regions in the same survey window. Confidence measures are retained for the regional level charts; they are not combined into confidence intervals for gaps or changes.

## Updating

`--fetch` saves each download and its metadata in a new directory under `data/local/`, leaving the bundled snapshot intact. `--snapshot` selects one of these directories. The analysis accepts two English statistical regions; Nomis IDs, ONS codes and geography types are checked against the source.

Source: Office for National Statistics via Nomis. Contains public sector information licensed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). See [Nomis copyright](https://www.nomisweb.co.uk/home/copyright.asp).
