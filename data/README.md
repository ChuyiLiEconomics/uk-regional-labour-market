# Data and provenance

All inputs are public regional aggregates from ONS, HMRC or Nomis. The snapshot was assembled on 24 November 2026. Reference periods, source release dates and retrieval times are recorded separately.

## Included inputs

| File | Rows | Units and coverage |
|---|---:|---|
| [snapshot/nomis.csv](snapshot/nomis.csv) | 368 source measure rows | Original APS rates and confidence margins for two regions and two indicators |
| [extended/bres.csv](extended/bres.csv) | 5,607 | Employee job counts, nine English regions, 88 two-digit SIC divisions plus the total, 2018–2024 |
| [extended/paye.csv](extended/paye.csv) | 1,332 | Monthly seasonally adjusted payrolled people, nine English regions, July 2014–October 2026 |
| [extended/ashe.csv](extended/ashe.csv) | 480 | Hourly pay excluding overtime and quality measures, two regions, three work patterns, total plus 19 sections, four years |
| [extended/cpih.csv](extended/cpih.csv) | 106 | UK CPIH all-items monthly index, 2015=100, January 2018–October 2026 |

The original APS download is included unchanged. The other inputs are extracts from pinned source files. Their hashes, URLs, retrieval times and source vintage information are in [extended/sources.json](extended/sources.json). Every prepared CSV has a recorded hash and row count.

Original Excel archives are not needed for an offline analysis. They can be retrieved to rebuild the extracts with the preparation script. If a source no longer matches the pinned hash, preparation stops rather than relabelling revised observations as the old vintage.

## Source versions

| Source | Version used |
|---|---|
| APS, Nomis NM_17_5 | Source updated 20 October 2026; annual window ends through June 2026 |
| PAYE RTI | ONS release 17 November 2026; October is an early estimate |
| BRES, Nomis NM_189_1 | API source updated 28 October 2025; 2024 provisional observations are the latest available in this response |
| ASHE Table 5.6a/b | Revised 2019, 2024 and 2025 archives; provisional 2026 archive |
| CPIH, L522 / MM23 | ONS release 18 November 2026 |

Publication-calendar entries are not used to assume a new year is present in a dataset. The BRES year range is checked against the actual API response.

## Field definitions

### APS

The source query and SHA-256 hash are in [snapshot/source.json](snapshot/source.json). Variables are employment rate (45) and economic inactivity rate (111), both for residents aged 16–64. Measures are rate (20599) and the published approximate 95% confidence-interval half-width (21003).

The cleaned [observations.csv](../output/tables/observations.csv) has one row per annual period, region and indicator:

- `period_end`: end of the 12-month survey window, YYYY-MM.
- `period_label`: full window supplied by Nomis.
- `region`, `region_code`: name and ONS code.
- `rate_pct`: percentage of residents aged 16–64.
- `confidence_pp`: confidence-interval half-width in percentage points.
- `rate_status`, `confidence_status`: original source status codes.

Only status A with a finite numeric value is used. Other statuses and blank values remain missing. Non-public observations, definition mismatches and duplicate keys are rejected. The included snapshot has no excluded or missing measure cells. Adjacent annual windows overlap.

### BRES

`year` is the annual survey reference year. `division` is a two-digit SIC 2007 code or TOTAL. `employees` is the published count of employee jobs, with the source status and original CSV row retained. It is not a count of unique resident workers.

The analysis sums divisions into sections A–S. T–U observations and the official total are retained in the input, but are outside the decomposition denominator. The [reconciliation export](../output/tables/bres_reconciliation.csv) shows the industry sum, the separately published total and their difference. Source rounding is preserved.

The annual path uses the same counts, with fixed 2019 regional denominators for additive growth-gap contributions. [Manufacturing divisions](../output/tables/manufacturing_divisions.csv) retain endpoint counts and distinguish shares of manufacturing from shares of all covered jobs. No additional employment dataset is introduced for these outputs.

Historical context comes from ONS articles on [2015 industrial geography](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/articles/thespatialdistributionofindustriesingreatbritain/2015), published 28 March 2017, and [2011–2021 Census industry changes](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/articles/howindustrieshavechangedatalocallevelbetweencensuses/2022-12-08), published 8 December 2022. These pages were consulted on 24 November 2026; they do not change the vintage of the included numerical inputs.

### PAYE RTI

`period` is the month, YYYY-MM. `payrolled_employees` counts people paid through payroll, allocated by residence. `is_early` is 1 for October 2026 and 0 for older months. `source_sheet` and `source_cell` identify the source value.

The nine regional columns are checked by name and order. Counts are kept in people, not thousands. The data are seasonally adjusted. England counts in the output are calculated by summing the nine regions.

### ASHE

`year` identifies the April survey estimate. `vintage` distinguishes revised and provisional data. `work_pattern` is all, full_time or part_time. `industry` is ALL for the headline regional row or a SIC section A–S.

`median_gbp_per_hour` is median hourly pay excluding overtime. `median_cv_pct` is its coefficient of variation expressed as a percentage, not a confidence-interval half-width. The 10th and 90th percentiles are retained as `p10_gbp_per_hour` and `p90_gbp_per_hour`.

Original median and CV cell contents are retained as text alongside their parsed values. Source workbook, CV workbook, sheet and one-based row are recorded. Matching estimate/CV rows are checked by description and code. Leading apostrophes in newer spreadsheet codes are removed as formatting characters.

Source markers such as x (unreliable), .. (disclosive), : (not applicable) and - (nil or negligible) remain blank in numeric fields. They are not converted into measured zeros. The original median and CV markers remain visible in the extract.

The headline uses the row carrying the region's ONS code, rather than the separate “All Industries and Services” row. ASHE indicative job counts are not used as employment totals or decomposition weights.

### CPIH

`period` is the month, YYYY-MM. `cpih_index` is the UK all-items index, series L522, with 2015=100. The source CSV row is retained. April pay is deflated using the corresponding April index.

## Outputs and interpretation

Regional gaps are North West minus West Midlands. Growth contributions are expressed in percentage points of the relevant region's baseline jobs. Pay gaps in pounds per hour and percent are labelled separately.

Missing values remain empty CSV cells or NULL in the APS SQLite analysis. No unpublished individual-level records are included. The [methods](../documents/methods.md) explain the test assumptions, shift-share identity, precision filter and sensitivity cases.

Source: Office for National Statistics and HMRC via ONS and Nomis. Contains public sector information licensed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). See [Nomis copyright](https://www.nomisweb.co.uk/home/copyright.asp).
