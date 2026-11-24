# Regional labour market findings

This descriptive comparison covers North West and West Midlands, England, for people aged 16-64. It does not estimate policy effects or hiring demand.

## Latest comparable observations

| Indicator | Survey period | North West (%) | West Midlands (%) | NW minus WM (pp) |
|---|---|---:|---:|---:|
| Employment | Jul 2025-Jun 2026 | 74.3 | 73.5 | +0.8 |
| Inactivity | Jul 2025-Jun 2026 | 22.4 | 22.0 | +0.4 |

The gap is a percentage-point difference between point estimates, not a causal effect or a claim of statistical significance. SQL selects the latest period with a non-missing rate in both regions for each indicator.

## Interpretation and limitations

- Employment and inactivity are distinct measures. Inactivity is not unemployment; unemployment rates use a different denominator.
- Adjacent observations are overlapping 12-month survey periods, not independent quarterly observations. The x-axis records the end of each period.
- Published approximate confidence intervals describe sampling uncertainty. No independence assumption is used to calculate a confidence interval for the regional gap.
- ONS warns that smaller achieved APS samples can increase volatility and non-response concerns. Regional rates should be considered alongside other labour market indicators.
- These are regional population estimates, not city estimates, counts of vacancies, employer demand or sponsorship availability.
- Historical estimates may be revised. The local snapshot and its hash identify the bytes used for this run.

## Provenance and quality checks

- Source: ONS Annual Population Survey via Nomis, `NM_17_5`.
- Retrieved at UTC: `2026-11-24T16:09:41.732023+00:00`.
- Survey period ends: `2015-03` to `2026-06`.
- Source rows: 368; cleaned observations: 184; periods: 46.
- Missing or non-normal measure cells retained as NULL: 0.
- Snapshot SHA-256: `910ccddb33990b3e3b212a05b3ec5f9700086babd51592a7af195ce315ec1b03`.
- Validated geography names, ONS codes and region types; indicator definitions; duplicate keys; record count; free-for-publication flags; numeric bounds; and rate/confidence cube completeness.

[Exact source query](https://www.nomisweb.co.uk/api/v01/dataset/NM_17_5.data.csv?geography=2013265922%2C2013265925&time=2015-01%2Clatest&variable=45%2C111&measures=20599%2C21003) · [ONS methodology](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/methodologies/annualpopulationsurveyapsqmi) · [Nomis copyright](https://www.nomisweb.co.uk/home/copyright.asp)

Contains public sector information licensed under the Open Government Licence v3.0.
