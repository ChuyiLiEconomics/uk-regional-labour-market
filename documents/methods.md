# Methods

## Research question and scope

The main comparison is between England's North West and West Midlands. The question is how their labour markets have changed since 2019 and how much of their workplace employee job growth gap is associated with their initial industry mix.

In the baseline BRES data, manufacturing accounts for 9.2% of covered employee jobs in the North West and 11.6% in the West Midlands. These differing initial structures give industry composition a role to examine. The regions share a national statistical framework, but they are not a matched pair or a representative sample of English regions.

The common historical comparison is 2019–2024. Later PAYE and ASHE estimates provide an update under their own definitions. No treatment, policy effect or pandemic effect is identified. Neither region is designated a control group.

The principal outputs are the resident payroll count index, workplace employee job growth decomposition, and median hourly pay comparisons. Latest APS employment and inactivity rates provide the original resident-rate context. Historical windows are not searched to choose significant results.

## PAYE: changes in resident payroll counts

For each region r, let P(r,t) be the seasonally adjusted payrolled employee count in month t. The baseline is the arithmetic average of the 12 monthly counts in calendar 2019:

I(r,t) = 100 × P(r,t) / mean[P(r, Jan–Dec 2019)].

A complete 12-month baseline is required. England is the sum of the nine English regional counts before computing its index. Regional median wages are never summed or averaged to construct an England median.

The main endpoint is September 2026. October is flagged as an early estimate in the November 2026 release and is reported separately. September and older months can also be revised. Annual-average growth through 2024 and an alternative 2018 baseline are exported.

PAYE measures people paid through payroll, including paid leave and furlough, by their residence. It excludes self-employment and is not restricted to ages 16–64. The index describes changes in counts, without a working-age population denominator. No t-test treats the monthly sequence as independent observations.

[ONS / HMRC PAYE methods](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/methodologies/monthlyearningsandemploymentestimatesfrompayasyouearnrealtimeinformationpayertidatamethods).

## BRES: shift-share accounting

BRES observations are workplace-based employee jobs. The prepared input retains all published two-digit SIC 2007 divisions and the separate total. Divisions are summed into sections A–S for the main decomposition. Agriculture is retained; household and extraterritorial sections T–U are outside this specification.

Let e(r,i,0) and e(r,i,1) denote employee jobs in region r and industry i at the two annual reference dates. Let E(r,0) be the sum across covered industries at baseline. Let g(i) be industry i's growth in the benchmark and g be growth across all covered benchmark industries.

For each region and industry:

- Benchmark growth: N(r,i) = e(r,i,0) × g.
- Industry mix: M(r,i) = e(r,i,0) × [g(i) − g].
- Within-industry remainder: R(r,i) = e(r,i,1) − e(r,i,0) × [1 + g(i)].

The three terms sum exactly to e(r,i,1) − e(r,i,0), subject to floating-point precision. Using levels for the remainder accommodates an industry that has zero regional baseline jobs and positive jobs later. A zero benchmark industry baseline is rejected.

Sum each component over industries and divide by E(r,0), then multiply by 100 to express contributions in percentage points of regional growth. Subtract West Midlands contributions from North West contributions to decompose the regional growth gap. Both regions use the same benchmark, so the aggregate benchmark-growth component cancels in this gap.

The main benchmark is the sum of all nine English regions. Sensitivity cases use:

| Case | Baseline | Endpoint | Benchmark | Industry groups |
|---|---:|---:|---|---|
| Main | 2019 | 2024 | England | 19 SIC sections |
| Earlier baseline | 2018 | 2024 | England | 19 SIC sections |
| Earlier endpoint | 2019 | 2023 | England | 19 SIC sections |
| Exclude focal regions | 2019 | 2024 | Other seven English regions | 19 SIC sections |
| Coarser classification | 2019 | 2024 | England | A–F, G–I, J–N, O–S |
| Finer classification | 2019 | 2024 | England | 84 active two-digit divisions in A–S |

The remainder includes all differences within the chosen groups: worker and firm composition, finer industry mix, local conditions, measurement error and other influences. It is not an estimate of competitiveness or a policy effect. Changing the industry grouping changes the allocation between mix and remainder.

### Nested comparison: sections and divisions

The covered A–S input contains 85 two-digit divisions. Division 07 (mining of metal ores) has zero published employment in all nine English regions in both 2019 and 2024. It is excluded from growth-rate calculations, leaving 84 active divisions and exactly the same covered employment totals. An industry is omitted only if all regions have zero jobs at both endpoints; a zero benchmark baseline with positive employment at either endpoint remains an error. Published zero counts are subject to the source's rounding.

The division-level decomposition uses the same dates, benchmark and regional denominators as the 19-section comparison. For a section s, sum the division-level mix terms for divisions in s and subtract the section-level mix term:

F(r,s) = sum[M_division(r,i), i in s] − M_section(r,s).

Then R_section(r,s) = F(r,s) + sum[R_division(r,i), i in s]. The same identity holds after subtracting West Midlands contributions from North West contributions. `within_section_composition.csv` exports all 19 sections, with the original remainder, finer-composition term and remaining within-division term. All terms are in percentage points of total covered regional employment growth, rather than section-specific growth.

Finer composition can increase or decrease the mix contribution; it need not reduce the remainder. This is a comparison of accounting classifications, not a test of a mechanism. The remaining division-level term can still include finer industry structure and composition effects within divisions.

The denominator is the sum of published division counts in A–S. The separately published BRES total is retained for reconciliation, not used to rescale the component counts. Rounding can make the division sum differ from that total. The exact accounting identity does not eliminate sampling error, rounding or revisions. No confidence interval or significance label is attached to the decomposition.

[ONS BRES definitions and methods](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/methodologies/businessregisterandemploymentsurveybres).

### Annual path and timing of the growth gap

The annual path uses all available BRES years from 2018 to 2024 and the same summed A–S counts as the decomposition. `bres_growth_path.csv` contains regional counts, an index with 2019 = 100, cumulative growth and conventional year-on-year growth. The gap table begins at the 2019 baseline.

Let E(r,t) denote the covered regional job count and E(r,2019) its fixed baseline. The cumulative regional growth gap is:

D(t) = 100 × [E(NW,t)/E(NW,2019) − E(WM,t)/E(WM,2019)].

For each year after 2019, the annual contribution is D(t) − D(t−1). The industry-specific contribution is:

A(i,t) = 100 × {[e(NW,i,t) − e(NW,i,t−1)]/E(NW,2019) − [e(WM,i,t) − e(WM,i,t−1)]/E(WM,2019)}.

Summing A(i,t) over industries gives the annual gap contribution. Summing over 2020–2024 gives the endpoint growth gap. Summing one industry's annual contributions gives its contribution to the 2019–2024 gap. These identities are checked in the code. Annual contributions use fixed denominators; they are not differences of year-on-year growth rates, which use the preceding year's employment.

The 2018–2019 change is reported separately to explain why the earlier baseline matters. A 2018-based endpoint growth gap uses different denominators and is not obtained by simply adding an annual growth-rate difference to the 2019-based gap. Sensitivity concerns the size as well as the sign of the estimates. The annual data describe timing without identifying event or policy effects; survey variation and business reporting can also affect movements.

### Manufacturing profiles and regional context

`manufacturing_divisions.csv` retains all 24 manufacturing divisions (10–33) in both regions. It reports 2019 and 2024 counts, job changes, division growth rates, baseline shares of manufacturing, baseline shares of total covered jobs and contributions to regional growth. A division with no baseline jobs has no percentage growth rate; any new jobs still contribute to regional growth.

Manufacturing shares use the sum of divisions 10–33, while growth contributions use all covered A–S baseline jobs. Changes summed over manufacturing divisions reconcile to the section-C contribution. The background table illustrates food, chemicals, fabricated metals and motor vehicles; these divisions were chosen to describe industrial profiles, not ranked as the largest contributors.

Historical ONS industry and Census articles provide context only. Their dates, geographic coverage and workplace/residence definitions are kept separate from the BRES analysis. All project estimates concern the full North West and West Midlands statistical regions. City-region, metropolitan-county and combined-authority figures are not substituted for them.

## ASHE: hourly pay and inflation

The measure is median hourly pay excluding overtime from Table 5.6a. Table 5.6b supplies the corresponding coefficient of variation (CV). Separate estimates are retained for all, full-time and part-time employee jobs.

The regional headline is the row identified by its ONS region code. Within-industry comparisons use the SIC section rows. The table's separate “All Industries and Services” row is not substituted for the headline region row: their populations and estimates can differ.

Revised 2019, 2024 and 2025 values are included, alongside provisional 2026 estimates. Every estimate retains its source workbook, sheet and row, and the matching CV workbook. Suppression and missing-data markers remain blank numeric values, with the original marker retained.

For each year's April estimate W(r,y), inflation-adjusted pay in April 2019 prices is:

W_real(r,y) = W(r,y) × CPIH(April 2019) / CPIH(April y).

The deflator is the UK CPIH all-items index, series L522. Annual-average inflation is not substituted for the matching April index. This adjusts for changes in the national price level over time; it does not adjust for different regional price levels.

The within-industry pay table uses revised 2025 full-time medians. A comparison is shown when both regional medians and CVs are available and both CVs are at most 5%. The exported table retains every section and an explicit inclusion flag. This is a precision screen, not a test of a pay gap.

Medians are not additive. Industry medians and BRES employment shares are not combined to claim an industry-adjusted regional median or wage premium. Aggregate median changes do not follow the same individuals over time. No significance test is claimed for the ASHE comparisons.

[ONS ASHE dataset and quality tables](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/regionbyindustry2digitsicashetable5).

## APS: approximate latest-period tests

The latest common valid period for each of the two original indicators is selected before testing. The null hypothesis is equal regional population rates; the alternative is a non-zero difference.

Let mA and mB be the published approximate 95% confidence-interval half-widths. Reconstruct sA = mA / 1.96 and sB = mB / 1.96. Under a zero cross-region covariance assumption:

s_gap = sqrt(sA² + sB²),
z = (rateA − rateB) / s_gap.

The approximate two-sided p-value is 2 × [1 − Φ(|z|)]. The gap's approximate 95% interval is gap ± 1.96 × s_gap. Missing or non-positive confidence margins leave the test unavailable.

Raw p-values and Holm-adjusted p-values are both exported. The family contains the employment and inactivity comparisons, with a 5% family-wise threshold. Reported intervals are pointwise, not simultaneous Holm-adjusted intervals.

Nomis margins are approximate and rounded. The calculation does not recover the full complex survey design, regional covariance or possible non-sampling biases. It is not an ONS-provided significance result. Failure to reject equality does not establish equivalence. No time-change test or historical-window significance search is performed.

[Nomis confidence-interval methods](https://www.nomisweb.co.uk/articles/news/files/APS_publication_rules.pdf).
[UK government guidance on comparing estimates](https://www.gov.uk/government/publications/ethnicity-data-which-differences-in-ethnic-group-data-are-real/which-differences-in-ethnic-group-data-are-real#using-a-t-test).
[ONS APS quality update, September 2026](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/methodologies/annualpopulationsurveyqualityupdateseptember2026).

## Interpreting the sources together

APS measures residents aged 16–64, PAYE measures resident payrolled people of all ages, and BRES measures workplace jobs. ASHE adds a workplace earnings perspective under its survey eligibility rules. The same regional label does not make these populations interchangeable.

PAYE annual averages, BRES annual reference-date stocks and ASHE April estimates also differ in timing. Agreement is corroborating context; disagreement does not identify its cause. Explaining commuting, demographic composition or individual wage differences would require additional data and a separate design.
