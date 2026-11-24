"""Figures and findings for the regional labour-market comparison."""
from datetime import datetime
import math

COLORS = {"North West": "#254B75", "West Midlands": "#A34A28", "England": "#777777"}
PATTERNS = {"all": "All employees", "full_time": "Full-time", "part_time": "Part-time"}


def charts(destination, tables):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import MaxNLocator
    import numpy as np

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "svg.hashsalt": "uk-regional-labour-market"})
    def save(fig, filename):
        fig.savefig(destination / (filename + ".png"), dpi=220)
        fig.savefig(destination / (filename + ".svg"), metadata={"Date": None})
        plt.close(fig)
    def footer(fig, text):
        fig.text(0.11, 0.035, text, fontsize=8.5, va="bottom")

    fig, ax = plt.subplots(figsize=(10, 5.8))
    fig.subplots_adjust(left=0.11, right=0.97, top=0.86, bottom=0.23)
    for name in ["England", "North West", "West Midlands"]:
        rows = [r for r in tables["paye_index"] if r["region"] == name and r["period"] >= "2018-01"]
        main = [r for r in rows if str(r["is_early"]) == "0"]
        early = [r for r in rows if str(r["is_early"]) == "1"]
        ax.plot([datetime.strptime(r["period"], "%Y-%m") for r in main], [r["index_2019_100"] for r in main],
                color=COLORS[name], label=name, linewidth=2 if name != "England" else 1.5)
        if early:
            segment = main[-1:] + early
            ax.plot([datetime.strptime(r["period"], "%Y-%m") for r in segment], [r["index_2019_100"] for r in segment],
                    color=COLORS[name], linestyle=":")
            ax.scatter([datetime.strptime(r["period"], "%Y-%m") for r in early], [r["index_2019_100"] for r in early],
                       edgecolors=COLORS[name], facecolors="white", s=18, zorder=3)
    ax.axhline(100, color="#BBBBBB", linewidth=1)
    ax.set_title("Payrolled employees", loc="left", fontsize=17, fontweight="bold", pad=18)
    ax.set_ylabel("Index (2019 calendar-year average = 100)")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", color="#E5E7EB")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    footer(fig, "Source: HMRC / ONS PAYE RTI, November 2026 vintage. Residence-based, seasonally adjusted.\n"
                f"Solid lines end in {month_label(main[-1]['period'])}. Open markers: early estimates. England sums nine regions.")
    save(fig, "paye_recovery")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.8))
    fig.subplots_adjust(left=0.09, right=0.98, top=0.83, bottom=0.24, wspace=0.30)
    x = np.arange(3)
    latest = [next(r for r in tables["hourly_pay_comparison"] if r["year"] == max(v["year"] for v in tables["hourly_pay_comparison"]) and r["work_pattern"] == p)
              for p in PATTERNS]
    for index, (name, prefix) in enumerate([("North West", "north_west"), ("West Midlands", "west_midlands")]):
        offset = (index - 0.5) * 0.35
        axes[0].bar(x + offset, [r[prefix + "_gbp_hour"] for r in latest], width=0.34, color=COLORS[name], label=name)
        axes[1].bar(x + offset, [r[prefix + "_real_growth_since_2019_pct"] for r in latest], width=0.34, color=COLORS[name])
    for ax in axes:
        ax.set_xticks(x, ["All", "Full-time", "Part-time"])
        ax.grid(axis="y", color="#E5E7EB")
        ax.set_axisbelow(True)
        ax.yaxis.set_major_locator(MaxNLocator(5))
    axes[0].set_title(f"Median hourly pay, April {latest[0]['year']}", loc="left", fontsize=12, fontweight="bold", pad=15)
    axes[0].set_ylabel("GBP per hour, excluding overtime")
    axes[0].legend(frameon=False, fontsize=9)
    axes[1].set_title("Real change from April 2019", loc="left", fontsize=12, fontweight="bold", pad=15)
    axes[1].set_ylabel("Change (%)")
    footer(fig, f"Source: ONS ASHE Table 5.6a, 2019 revised and {latest[0]['year']} {latest[0]['vintage']}. Workplace-based jobs.\n"
                "Real change uses the UK CPIH index for the matching April. It does not adjust for regional price levels.")
    save(fig, "hourly_pay")

    main = [next(r for r in tables["shift_share_summary"] if r["case"] == "2019-2024_england_sections" and r["region"] == n)
            for n in ["North West", "West Midlands"]]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    fig.subplots_adjust(left=0.11, right=0.97, top=0.86, bottom=0.24)
    labels = ["England growth", "Industry mix", "Within-industry\nremainder", "Actual growth"]
    fields = ["national_growth_pp", "industry_mix_pp", "within_industry_pp", "actual_growth_pct"]
    x = np.arange(4)
    for index, row in enumerate(main):
        positions = x + (index - 0.5) * 0.36
        values = [row[k] for k in fields]
        ax.bar(positions, values, width=0.35, color=COLORS[row["region"]], label=row["region"])
        for position, value in zip(positions, values):
            ax.annotate(f"{value:+.2f}", (position, value), xytext=(0, 4 if value >= 0 else -13),
                        textcoords="offset points", ha="center", fontsize=9)
    ax.axhline(0, color="#777777", linewidth=1)
    ax.set_xticks(x, labels)
    ax.margins(y=0.22)
    ax.set_ylabel("Contribution to growth (percentage points)")
    ax.set_title("Employee job growth, 2019–2024", loc="left", fontsize=17, fontweight="bold", pad=18)
    ax.legend(frameon=False, ncol=2, loc="upper right")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    footer(fig, "Source: ONS BRES via Nomis. Workplace-based jobs in SIC 2007 sections A–S; rounded source counts.\n"
                "The first three components sum to actual growth. The decomposition is an accounting exercise.")
    save(fig, "shift_share")

    selected = sorted(tables["sector_gap_contributions"], key=lambda r: r["growth_gap_contribution_pp"])
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.subplots_adjust(left=0.30, right=0.96, top=0.88, bottom=0.17)
    values = [r["growth_gap_contribution_pp"] for r in selected]
    ax.barh([r["sector_label"] for r in selected], values,
            color=["#254B75" if v >= 0 else "#A34A28" for v in values], height=0.7)
    ax.axvline(0, color="#777777", linewidth=1)
    ax.set_xlabel("Contribution to North West minus West Midlands growth gap (pp)")
    ax.grid(axis="x", color="#E5E7EB")
    ax.set_axisbelow(True)
    fig.suptitle("Which industries contributed to the growth gap?", x=0.08, ha="left", fontsize=16, fontweight="bold")
    fig.text(0.08, 0.04, f"Source: ONS BRES via Nomis, 2019–2024. Contributions sum to {math.fsum(values):.2f} percentage points.\n"
             "Each region uses its own 2019 employment denominator. These contributions are descriptive.", fontsize=8.5)
    save(fig, "sector_contributions")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.8))
    fig.subplots_adjust(left=0.09, right=0.98, top=0.84, bottom=0.24, wspace=0.28)
    for name in ["North West", "West Midlands"]:
        rows = [r for r in tables['bres_growth_path'] if r['region'] == name]
        axes[0].plot([r['year'] for r in rows], [r['index_baseline_100'] for r in rows],
                     color=COLORS[name], marker='o', markersize=4, linewidth=2, label=name)
    axes[0].axhline(100, color='#BBBBBB', linewidth=1)
    axes[0].set_title('Workplace employee jobs', loc='left', fontsize=12, fontweight='bold', pad=14)
    axes[0].set_ylabel('Index (2019 = 100)')
    axes[0].legend(frameon=False, fontsize=9, loc='upper left')
    gaps = tables['bres_annual_gaps']
    changes = [r for r in gaps if r['annual_gap_contribution_pp'] is not None]
    axes[1].bar([r['year'] for r in changes], [r['annual_gap_contribution_pp'] for r in changes],
                color='#BAC5D1', width=0.55, label='Annual contribution')
    axes[1].plot([r['year'] for r in gaps], [r['growth_gap_pp'] for r in gaps],
                 color='#254B75', marker='o', markersize=4, linewidth=2, label='Cumulative gap')
    axes[1].axhline(0, color='#777777', linewidth=1)
    axes[1].set_title('North West minus West Midlands', loc='left', fontsize=12, fontweight='bold', pad=14)
    axes[1].set_ylabel('Growth gap / contribution (pp)')
    axes[1].legend(frameon=False, fontsize=9, loc='upper left')
    for ax in axes:
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
        ax.grid(axis='y', color='#E5E7EB')
        ax.set_axisbelow(True)
        ax.margins(y=0.25)
    footer(fig, 'Source: ONS BRES via Nomis; sums of SIC sections A–S, with rounded source counts.\n'
                'Annual contributions use fixed 2019 regional denominators and sum to the cumulative growth gap.')
    save(fig, 'bres_timing')


def signed(value):
    return f"{0.0 if abs(value) < 0.005 else value:+.2f}"


def month_label(period):
    return datetime.strptime(period, "%Y-%m").strftime("%B %Y")


def aps_conclusion(rows):
    available = [r for r in rows if r["reject_5pct_after_holm"] is not None]
    rejected = [r["indicator"] for r in available if r["reject_5pct_after_holm"]]
    if not available:
        return "The available confidence margins do not support either approximate test."
    if rejected:
        text = "Equality is rejected at 5% after Holm adjustment for: " + ", ".join(rejected) + "."
    else:
        text = "None of the available comparisons rejects equal regional rates at 5% after Holm adjustment."
    if len(available) < len(rows):
        text += " At least one comparison is unavailable."
    return text


def case_label(row):
    grouping = {"sections": "19 sections", "broad": "4 broad groups", "divisions": f"{row['industry_count']} active divisions"}[row["grouping"]]
    benchmark = "England" if row["benchmark"] == "England" else "Other seven English regions"
    return f"{row['start_year']}–{row['end_year']}; {benchmark}; {grouping}"


def sensitivity_conclusion(rows):
    values = [r["growth_gap_pp"] for r in rows]
    direction = ("positive in every case" if all(v > 0 for v in values) else
                 "negative in every case" if all(v < 0 for v in values) else "not of the same strict sign in every case")
    return (f"The North West minus West Midlands growth gap is {direction}, ranging from "
            f"{min(values):+.2f} to {max(values):+.2f} percentage points. "
            "Classification changes the split between composition and the remainder without changing covered job growth.")


def timing_summary(rows):
    end = rows[-1]
    earlier = rows[-3] if len(rows) >= 3 else rows[0]
    changes = [r['annual_gap_contribution_pp'] for r in rows if r['annual_gap_contribution_pp'] is not None]
    path = ('The annual contributions include both widening and narrowing of the gap. '
            if any(v > 0 for v in changes) and any(v < 0 for v in changes) else '')
    return (path + f"From {earlier['year']} to {end['year']}, the cumulative gap moved from "
            f"{signed(earlier['growth_gap_pp'])} to {signed(end['growth_gap_pp'])} percentage points, "
            f"a change of {signed(end['growth_gap_pp'] - earlier['growth_gap_pp'])} points. "
            "The endpoint comparison therefore needs to be read alongside the annual path.")


def section_pair(tables, sector):
    return [next(r for r in tables['shift_share_industries'] if r['case'] == '2019-2024_england_sections' and
                 r['region'] == name and r['industry'] == sector) for name in ['North West', 'West Midlands']]


def regional_context(tables):
    spatial = 'https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/articles/thespatialdistributionofindustriesingreatbritain/2015'
    census = 'https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/articles/howindustrieshavechangedatalocallevelbetweencensuses/2022-12-08'
    lines = ['### Regional background', '',
             f'[ONS analysis of 2015 employee jobs]({spatial}), published in 2017, identified the West Midlands as a '
             'centre of motor-vehicle manufacturing and chemical-manufacturing concentrations in parts of the North West. '
             'These are historical features, rather than explanations of the subsequent employment changes.', '',
             'The project’s own 2019 BRES baseline shows how the regions differ within manufacturing:', '',
             '| Division | NW jobs | NW share of manufacturing (%) | WM jobs | WM share of manufacturing (%) |',
             '|---|---:|---:|---:|---:|']
    for division, label in [('10', 'Food products'), ('20', 'Chemicals'), ('25', 'Fabricated metals'), ('29', 'Motor vehicles')]:
        a, b = [next(r for r in tables['manufacturing_divisions'] if r['division'] == division and r['region'] == name)
                for name in ['North West', 'West Midlands']]
        lines.append(f"| {division}: {label} | {a['baseline_employees']:,.0f} | {a['baseline_share_of_manufacturing_pct']:.1f} | "
                     f"{b['baseline_employees']:,.0f} | {b['baseline_share_of_manufacturing_pct']:.1f} |")
    lines += ['', 'These four divisions illustrate the regional profiles; they were not selected as the largest contributors '
              'to the growth gap. Shares use manufacturing employment as their denominator, rather than all regional jobs. '
              'The different mixes motivate checking the section-level decomposition against two-digit industries.', '',
              f'[ONS Census analysis published in 2022]({census}) also documented growth in transport and warehousing '
              'employment among Midlands residents over 2011–2021. This provides background for examining transport as a '
              'counterweight to manufacturing in the present comparison. Census resident employment and BRES workplace jobs '
              'have different populations and periods; their changes are not combined.', '',
              'The case therefore compares regions with substantial manufacturing employment but different industrial profiles. '
              'It allows industry composition and within-industry changes to be examined under common national definitions. '
              'It does not establish why a particular factory, firm or worker changed employment. All results refer to the full '
              'North West and West Midlands statistical regions, rather than individual cities or combined-authority areas.', '']
    return lines


def industry_discussion(tables, table_prefix):
    lines = ['The three sections with the largest absolute contributions to the growth gap are:', '',
             '| Section | NW jobs, 2019 → 2024 | NW change (%) | WM jobs, 2019 → 2024 | WM change (%) | Gap contribution (pp) |',
             '|---|---:|---:|---:|---:|---:|']
    for row in sorted(tables['sector_gap_contributions'], key=lambda r: abs(r['growth_gap_contribution_pp']), reverse=True)[:3]:
        a, b = section_pair(tables, row['sector'])
        rates = [100 * (r['end_employees'] / r['baseline_employees'] - 1) if r['baseline_employees'] > 0 else None for r in [a, b]]
        formatted = [signed(v) if v is not None else 'Unavailable' for v in rates]
        lines.append(f"| {row['sector_label']} | {a['baseline_employees']:,.0f} → {a['end_employees']:,.0f} | {formatted[0]} | "
                     f"{b['baseline_employees']:,.0f} → {b['end_employees']:,.0f} | {formatted[1]} | {signed(row['growth_gap_contribution_pp'])} |")
    a, b = section_pair(tables, 'C')
    if all(r['end_employees'] < r['baseline_employees'] for r in [a, b]):
        lines += ['', 'Manufacturing employment fell in both regions. Its contribution to the regional growth gap therefore '
                  'compares job losses, scaled by each region’s total 2019 employment. A positive gap contribution does not '
                  'mean manufacturing created jobs in the North West.']
    lines += ['', 'The job changes and sector growth rates answer different questions from the contribution column: '
              'the latter uses all covered regional baseline jobs as its denominator. The transport and retail comparisons '
              'show why a manufacturing-only account would miss changes elsewhere in the regional economy.', '',
              f'[All manufacturing divisions, including endpoint changes]({table_prefix}manufacturing_divisions.csv)', '']
    return lines


def annual_discussion(tables, image_prefix, table_prefix):
    gaps = tables['bres_annual_gaps']
    lines = ['### When did the gap emerge?', '', f'![Annual workplace job growth and contributions]({image_prefix}bres_timing.png)', '',
             '| Year | NW growth from 2019 (%) | WM growth from 2019 (%) | Cumulative gap (pp) | Annual contribution to gap (pp) |',
             '|---|---:|---:|---:|---:|']
    for r in gaps:
        annual = signed(r['annual_gap_contribution_pp']) if r['annual_gap_contribution_pp'] is not None else 'Baseline'
        lines.append(f"| {r['year']} | {signed(r['north_west_growth_pct'])} | {signed(r['west_midlands_growth_pct'])} | "
                     f"{signed(r['growth_gap_pp'])} | {annual} |")
    lines += ['', timing_summary(gaps), '', 'Each annual contribution is the difference between the two regions’ job '
              'changes divided by their respective fixed 2019 employment totals. Contributions add to the endpoint gap. '
              'They are not differences between conventional year-on-year percentage growth rates.', '',
              '| Interval | Largest absolute industry contributions to the annual gap (pp) |', '|---|---|']
    for year in [r['year'] for r in gaps[1:]]:
        selected = sorted([r for r in tables['bres_annual_sector_contributions'] if r['end_year'] == year],
                          key=lambda r: abs(r['growth_gap_contribution_pp']), reverse=True)[:2]
        descriptions = '; '.join(f"{r['sector_label']} {signed(r['growth_gap_contribution_pp'])}" for r in selected)
        lines.append(f'| {year - 1}–{year} | {descriptions} |')
    pre = [r for r in tables['bres_growth_path'] if r['year'] == gaps[0]['year']]
    lines += ['', f"Before the main window, 2018–2019 job growth was {signed(pre[0]['year_on_year_pct'])}% in the North West "
              f"and {signed(pre[1]['year_on_year_pct'])}% in the West Midlands. An earlier baseline includes that difference "
              'and uses different denominators. Ending in 2023 instead of 2024 also omits the final year’s contribution. '
              'The sensitivity results consequently describe both a stable endpoint sign and a materially changing magnitude.', '',
              'Annual BRES movements can reflect survey variation, business reporting and classification changes as well as '
              'economic changes. These estimates locate changes in the published series; they cannot attribute them to the '
              'pandemic, Brexit, factory closures or particular policies.', '',
              f'[Annual regional series]({table_prefix}bres_growth_path.csv) · '
              f'[All annual industry contributions]({table_prefix}bres_annual_sector_contributions.csv)', '']
    return lines


def findings(tables, aps, manifest, local=False):
    image_prefix = "figures/" if local else "../output/figures/"
    table_prefix = "tables/" if local else "../output/tables/"
    main_case = "2019-2024_england_sections"
    fine_case = "2019-2024_england_divisions"
    main = {r["region"]: r for r in tables["shift_share_summary"] if r["case"] == main_case}
    gap = next(r for r in tables["shift_share_gap"] if r["case"] == main_case)
    fine = next(r for r in tables["shift_share_gap"] if r["case"] == fine_case)
    paye = {r["region"]: r for r in tables["paye_summary"] if r["baseline_year"] == 2019 and r["estimate_status"] == "latest_non_early"}
    early = {r["region"]: r for r in tables["paye_summary"] if r["baseline_year"] == 2019 and r["estimate_status"] == "early_estimate"}
    pay_year = max(r["year"] for r in tables["hourly_pay_comparison"])
    latest_pay = [r for r in tables["hourly_pay_comparison"] if r["year"] == pay_year]
    all_pay = next(r for r in latest_pay if r["work_pattern"] == "all")
    revised = max((r for r in tables["hourly_pay_comparison"] if r["vintage"] == "revised" and r["work_pattern"] == "all"), key=lambda r: r["year"])
    payroll_gap_2024 = paye['North West']['growth_to_2024_average_pct'] - paye['West Midlands']['growth_to_2024_average_pct']
    manufacturing = {r["region"]: r["baseline_share_pct"] for r in tables["shift_share_industries"]
                     if r["case"] == main_case and r["industry"] == "C"}
    lines = ["# Employment, pay and industrial change in two English regions", "",
             "## Question and comparison", "",
             "How much of the North West–West Midlands employee job growth gap is associated with their initial industry structure? "
             "The two regions provide a case study of employment differences within the same national statistical framework. "
             f"Manufacturing accounted for {manufacturing['North West']:.1f}% of covered employee jobs in the North West "
             f"and {manufacturing['West Midlands']:.1f}% in the West Midlands in 2019. "
             "This difference gives industry composition a concrete role to examine. Neither region is a control group, "
             "and the comparison does not represent all regional disparities.", "",
             *regional_context(tables),
             "## Results", "",
             f"Between 2019 and 2024, covered BRES employee jobs grew by {main['North West']['actual_growth_pct']:.2f}% "
             f"in the North West and {main['West Midlands']['actual_growth_pct']:.2f}% in the West Midlands: "
             f"a gap of {gap['growth_gap_pp']:+.2f} percentage points. "
             f"At the section level, the industry-mix contribution is {gap['industry_mix_gap_pp']:+.2f} points "
             f"and the within-section remainder {gap['within_industry_gap_pp']:+.2f} points.", "",
             f"Using {fine['industry_count']} active two-digit divisions changes those contributions to "
             f"{fine['industry_mix_gap_pp']:+.2f} and {fine['within_industry_gap_pp']:+.2f} points. "
             "The overall growth gap is unchanged; the interpretation of its components depends on industry detail.", "",
             "## 1. Resident employment and sampling uncertainty", "",
             "The APS measures employment and inactivity rates among residents aged 16–64. "
             "Each row uses its latest common valid annual window.", "",
             "| Indicator | Window | North West (%) | West Midlands (%) | Gap (pp) | Approx. 95% interval | Raw p | Holm p |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in tables["aps_gap_tests"]:
        interval = f"[{row['approx_ci_lower_pp']:.2f}, {row['approx_ci_upper_pp']:.2f}]" if row["approx_ci_lower_pp"] is not None else "Unavailable"
        raw_p = f"{row['approx_p_two_sided']:.3f}" if row["approx_p_two_sided"] is not None else "Unavailable"
        adj_p = f"{row['holm_adjusted_p']:.3f}" if row["holm_adjusted_p"] is not None else "Unavailable"
        lines.append(f"| {row['indicator'].capitalize()} | {row['period_label']} | {row['region_a_pct']:.1f} | {row['region_b_pct']:.1f} | {row['gap_pp']:+.1f} | {interval} | {raw_p} | {adj_p} |")
    lines += ["", aps_conclusion(tables["aps_gap_tests"]), "",
              "The approximation reconstructs standard errors from rounded Nomis margins and assumes zero cross-region "
              "covariance. It is not a full survey-design test. Intervals are pointwise; Holm adjustment covers the two "
              "latest-period tests. Failure to reject equality does not establish equivalence.", ""]
    for row in aps["baseline_changes"]:
        lines += [f"From {row['baseline_period_label']} to {row['latest_period_label']}, {row['indicator']} changed by "
                  f"{row['change_region_a_pp']:+.1f} percentage points in the North West and {row['change_region_b_pp']:+.1f} "
                  "in the West Midlands. These time changes are descriptive; their covariance is unavailable.", ""]
    lines += ["## 2. Monthly payrolled employment", "", f"![Payrolled employment]({image_prefix}paye_recovery.png)", "",
              f"| Region | {month_label(paye['North West']['period'])} employees | Change from 2019 average (%) | Annual change (%) | 2019–2024 annual-average growth (%) |",
              "|---|---:|---:|---:|---:|"]
    for name, row in paye.items():
        lines.append(f"| {name} | {row['payrolled_employees']:,.0f} | {signed(row['growth_from_baseline_pct'])} | {signed(row['year_on_year_pct'])} | {row['growth_to_2024_average_pct']:+.2f} |")
    lines += ["", f"The {month_label(early['North West']['period'])} early estimates put cumulative growth at "
              f"{early['North West']['growth_from_baseline_pct']:+.2f}% and {early['West Midlands']['growth_from_baseline_pct']:+.2f}%. "
              "All PAYE months can be revised.", "",
              "PAYE counts people receiving pay through payroll, including paid leave and furlough, by residence. "
              "It excludes self-employment and covers all ages. An index measures changes in counts, without controlling "
              "for population growth. Monthly observations are not treated as independent samples.", "",
              "## 3. Industry structure and employee job growth", "",
              f"![Shift-share decomposition]({image_prefix}shift_share.png)", "",
              "| Region | Actual growth (%) | England growth (pp) | Industry mix (pp) | Within-section remainder (pp) |",
              "|---|---:|---:|---:|---:|---:|"]
    for name, row in main.items():
        lines.append(f"| {name} | {signed(row['actual_growth_pct'])} | {signed(row['national_growth_pp'])} | {signed(row['industry_mix_pp'])} | {signed(row['within_industry_pp'])} |")
    lines += ["", f"![Industry contributions]({image_prefix}sector_contributions.png)", "",
              *industry_discussion(tables, table_prefix), *annual_discussion(tables, image_prefix, table_prefix)]
    reassigned = fine['industry_mix_gap_pp'] - gap['industry_mix_gap_pp']
    inactive = fine['inactive_industries'].split(';') if fine['inactive_industries'] else []
    coverage = f"The division-level calculation uses {fine['industry_count']} active divisions in sections A–S. "
    if inactive:
        coverage += (f"The following divisions have zero published jobs in every English region at both endpoints: {', '.join(inactive)}. They "
                     "are omitted from growth-rate calculations. ")
    coverage += "The covered employment totals are unchanged."
    lines += ["", "### What changes with finer industry detail?", "", coverage, "",
              f"Moving from 19 sections to {fine['industry_count']} active divisions changes the industry-mix contribution "
              f"to the regional gap by {reassigned:+.2f} percentage points, from {gap['industry_mix_gap_pp']:+.2f} "
              f"to {fine['industry_mix_gap_pp']:+.2f}. The remainder changes by {-reassigned:+.2f} points, "
              f"from {gap['within_industry_gap_pp']:+.2f} to {fine['within_industry_gap_pp']:+.2f}. "
              "This isolates the accounting contribution of finer industry composition within sections; it does not identify a causal mechanism.", "",
              "| Section | Original within-section gap (pp) | Finer composition (pp) | Remaining within-division gap (pp) |",
              "|---|---:|---:|---:|"]
    for row in sorted(tables["within_section_composition"], key=lambda r: abs(r["finer_composition_gap_pp"]), reverse=True)[:5]:
        lines.append(f"| {row['sector_label']} | {signed(row['section_within_gap_pp'])} | {signed(row['finer_composition_gap_pp'])} | {signed(row['division_within_gap_pp'])} |")
    lines += ["", "The five sections above have the largest absolute finer-composition contributions. In each row, the "
              "last two columns sum to the original remainder. Contributions use each region's total covered baseline employment, "
              "so each column in the full section table sums to its corresponding aggregate component.", "",
              f"[All sections and the nested decomposition]({table_prefix}within_section_composition.csv)", "",
              "### Sensitivity", "",
              "| Specification | Growth gap (pp) | Industry mix (pp) | Within-industry remainder (pp) |",
              "|---|---:|---:|---:|"]
    for row in tables["shift_share_gap"]:
        lines.append(f"| {case_label(row)} | {signed(row['growth_gap_pp'])} | {signed(row['industry_mix_gap_pp'])} | {signed(row['within_industry_gap_pp'])} |")
    lines += ["", sensitivity_conclusion(tables["shift_share_gap"]), "",
              "BRES counts workplace jobs. Rounded division counts need not sum exactly to the separately rounded official "
              "total; that difference is retained in the reconciliation table. The decomposition has no estimated standard "
              "errors. Its remainder includes worker and firm composition, local conditions and measurement error, among other influences.", "",
              "## 4. Hourly pay", "", f"![Hourly pay]({image_prefix}hourly_pay.png)", "",
              f"| Work pattern | NW April {pay_year} (GBP/hour) | WM April {pay_year} (GBP/hour) | Gap (GBP/hour) | NW real change from 2019 (%) | WM real change from 2019 (%) |",
              "|---|---:|---:|---:|---:|---:|"]
    for row in latest_pay:
        lines.append(f"| {PATTERNS[row['work_pattern']]} | {row['north_west_gbp_hour']:.2f} | {row['west_midlands_gbp_hour']:.2f} | {signed(row['gap_gbp_hour'])} | {row['north_west_real_growth_since_2019_pct']:+.2f} | {row['west_midlands_real_growth_since_2019_pct']:+.2f} |")
    lines += ["", f"The {pay_year} figures are {all_pay['vintage']}. In revised {revised['year']} estimates, all-employee "
              f"median hourly pay was GBP {revised['north_west_gbp_hour']:.2f} and GBP {revised['west_midlands_gbp_hour']:.2f}, "
              f"a gap of GBP {revised['gap_gbp_hour']:+.2f}. These are descriptive comparisons.", "",
              "ASHE measures hourly earnings excluding overtime for eligible workplace employee jobs. Real changes use matching "
              "April UK CPIH, expressed in April 2019 prices. This does not adjust for regional living costs or follow the same "
              "workers over time.", "",
              "### Pay within industries", "",
              "Revised 2025 full-time medians are shown when both regional median CVs are at most 5%. The full export retains "
              "all 19 sections. This is a precision screen, not a significance test.", "",
              "| Industry | NW (GBP/hour) | WM (GBP/hour) | Gap (GBP/hour) |", "|---|---:|---:|---:|"]
    for row in tables["industry_pay_comparison"]:
        if row["passes_cv_5pct_in_both"]:
            lines.append(f"| {row['sector_label']} | {row['north_west_gbp_hour']:.2f} | {row['west_midlands_gbp_hour']:.2f} | {signed(row['gap_gbp_hour'])} |")
    lines += ["", "Industry medians are not averaged into a regional median. These comparisons do not hold worker "
              "characteristics constant or estimate a regional wage premium.", "",
              "## Reading the sources together", "",
              f"Over the common 2019–2024 comparison, the PAYE annual-average growth gap is {payroll_gap_2024:+.2f} points, "
              f"compared with {gap['growth_gap_pp']:+.2f} points for BRES workplace jobs. "
              "Thus the workplace and residence measures need separate interpretation even with aligned years. "
              "Commuting and multiple jobs are possible areas for further investigation, but these aggregates cannot determine "
              "their contributions. The reference-date and coverage differences also remain.", "",
              f"At the latest ASHE endpoint, the all-employee hourly median gap is GBP {all_pay['gap_gbp_hour']:+.2f}. "
              "The pay and job-growth comparisons describe different aspects of the labour market; they do not provide a single regional ranking.", "",
              "## Sources and reproduction", "",
              "The study uses the frozen 24 November 2026 downloads: APS annual windows through June 2026; November 2026 "
              "PAYE RTI and CPIH releases; BRES 2018–2024 (2024 provisional); and revised 2019/2024/2025 plus provisional "
              "2026 ASHE Table 5.6a/b. Source hashes, vintages and original rows or cells are recorded in data/extended.", ""]
    for name, url in manifest["source_pages"].items():
        lines.append(f"- [{name.upper()} source]({url})")
    lines += ["", "Run `python code/python/research.py` to regenerate this report, its tables and figures offline.", "",
              f"[APS tests]({table_prefix}aps_gap_tests.csv) · [Growth decomposition]({table_prefix}shift_share_summary.csv) · "
              f"[Industry contributions]({table_prefix}sector_gap_contributions.csv) · [Pay comparisons]({table_prefix}hourly_pay_comparison.csv)", ""]
    return "\n".join(lines)
