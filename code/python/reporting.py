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
                "Solid lines end in September 2026. Open markers: October early estimates. England sums nine regions.")
    save(fig, "paye_recovery")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.8))
    fig.subplots_adjust(left=0.09, right=0.98, top=0.83, bottom=0.24, wspace=0.30)
    x = np.arange(3)
    latest = [next(r for r in tables["hourly_pay_comparison"] if r["year"] == 2026 and r["work_pattern"] == p)
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
    axes[0].set_title("Median hourly pay, April 2026", loc="left", fontsize=12, fontweight="bold", pad=15)
    axes[0].set_ylabel("GBP per hour, excluding overtime")
    axes[0].legend(frameon=False, fontsize=9)
    axes[1].set_title("Real change from April 2019", loc="left", fontsize=12, fontweight="bold", pad=15)
    axes[1].set_ylabel("Change (%)")
    footer(fig, "Source: ONS ASHE Table 5.6a, 2019 revised and 2026 provisional. Workplace-based employee jobs.\n"
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
    ax.set_ylim(-2.1, 6.5)
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


def findings(tables, aps, manifest, local=False):
    image_prefix = "figures/" if local else "../output/figures/"
    table_prefix = "tables/" if local else "../output/tables/"
    main = {r["region"]: r for r in tables["shift_share_summary"] if r["case"] == "2019-2024_england_sections"}
    gap = next(r for r in tables["shift_share_gap"] if r["case"] == "2019-2024_england_sections")
    paye = {r["region"]: r for r in tables["paye_summary"] if r["baseline_year"] == 2019 and r["estimate_status"] == "latest_non_early"}
    latest_pay = [r for r in tables["hourly_pay_comparison"] if r["year"] == 2026]
    lines = ["# Employment, pay and industrial change in two English regions", "",
             "The comparison asks how the North West and West Midlands have changed since 2019, and how much of their "
             "employee job growth gap is associated with their initial industry mix. The sources measure different "
             "populations and locations, so each comparison is interpreted within its own scope.", "",
             "## What the sources show", "",
             f"PAYE employment growth was close: by September 2026, payrolled employee numbers were "
             f"{paye['North West']['growth_from_baseline_pct']:.2f}% above their 2019 average in the North West and "
             f"{paye['West Midlands']['growth_from_baseline_pct']:.2f}% above in the West Midlands. In contrast, "
             f"workplace-based BRES employee jobs in the covered industries grew by {main['North West']['actual_growth_pct']:.2f}% "
             f"and {main['West Midlands']['actual_growth_pct']:.2f}% respectively between 2019 and 2024.", "",
             f"The BRES growth gap was {gap['growth_gap_pp']:.2f} percentage points. The shift-share decomposition assigns "
             f"{gap['industry_mix_gap_pp']:.2f} points to differences in initial industry mix and "
             f"{gap['within_industry_gap_pp']:.2f} points to differences in growth within the industry sections. "
             "The second component includes all remaining regional differences and estimation error; it is not a causal effect.", "",
             "## 1. Resident employment and sampling uncertainty", "",
             "The APS measures employment and inactivity rates among residents aged 16–64. For July 2025–June 2026:", "",
             "| Indicator | North West (%) | West Midlands (%) | Gap (pp) | Approx. 95% interval for gap | Raw p | Holm p |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for row in tables["aps_gap_tests"]:
        interval = f"[{row['approx_ci_lower_pp']:.2f}, {row['approx_ci_upper_pp']:.2f}]" if row["approx_ci_lower_pp"] is not None else "Unavailable"
        raw_p = f"{row['approx_p_two_sided']:.3f}" if row["approx_p_two_sided"] is not None else "Unavailable"
        adj_p = f"{row['holm_adjusted_p']:.3f}" if row["holm_adjusted_p"] is not None else "Unavailable"
        lines.append(f"| {row['indicator'].capitalize()} | {row['region_a_pct']:.1f} | {row['region_b_pct']:.1f} | {row['gap_pp']:+.1f} | {interval} | {raw_p} | {adj_p} |")
    lines += ["", "Neither comparison rejects equal regional rates at 5% under a normal approximation that sets the "
              "cross-region covariance to zero. This is not an equivalence test or a full survey-design test. The standard "
              "errors are reconstructed from rounded Nomis confidence margins. Holm adjustment covers the two latest-period "
              "indicators only. No search across historical windows is used to select significant results.", "",
              "Relative to calendar 2019, employment estimates changed by −0.2 percentage points in the North West and "
              "−0.4 in the West Midlands. Those time changes remain descriptive because their covariance is not provided.", "",
              "## 2. Monthly payrolled employment", "",
              f"![Payrolled employment]({image_prefix}paye_recovery.png)", "",
              "| Region | Sep 2026 employees | Change from 2019 average (%) | Annual change (%) | 2019–2024 annual-average growth (%) |",
              "|---|---:|---:|---:|---:|"]
    for name, row in paye.items():
        lines.append(f"| {name} | {row['payrolled_employees']:,.0f} | {row['growth_from_baseline_pct']:+.2f} | {row['year_on_year_pct']:+.2f} | {row['growth_to_2024_average_pct']:+.2f} |")
    early = {r["region"]: r for r in tables["paye_summary"] if r["baseline_year"] == 2019 and r["estimate_status"] == "early_estimate"}
    lines += ["", f"October 2026 is an early estimate. Including it changes cumulative growth to "
              f"{early['North West']['growth_from_baseline_pct']:.2f}% and {early['West Midlands']['growth_from_baseline_pct']:.2f}%. "
              "It does not change the conclusion that the two indexed PAYE paths are close. All PAYE months can still be revised.", "",
              "PAYE counts people receiving pay through payroll, including paid leave and furlough. It excludes self-employment, "
              "covers all ages and assigns people by residence. An index measures changes in counts; it is not an employment "
              "rate and does not control for population growth. Monthly observations are not treated as independent samples.", "",
              "## 3. Industry structure and employee job growth", "",
              f"![Shift-share decomposition]({image_prefix}shift_share.png)", "",
              "| Region | Actual growth (%) | England growth (pp) | Industry mix (pp) | Within-industry remainder (pp) |",
              "|---|---:|---:|---:|---:|"]
    for name, row in main.items():
        lines.append(f"| {name} | {row['actual_growth_pct']:+.2f} | {row['national_growth_pp']:+.2f} | {row['industry_mix_pp']:+.2f} | {row['within_industry_pp']:+.2f} |")
    lines += ["", "Both regions began with an industry mix that would have grown more slowly than the English aggregate "
              "if every local industry had followed its England-wide growth rate. This compositional drag was larger in the "
              "West Midlands. The larger part of the main growth gap remains within the broad industry sections.", "",
              f"![Industry contributions]({image_prefix}sector_contributions.png)", "",
              "Manufacturing contributed +1.55 percentage points to the North West minus West Midlands growth gap. "
              "Transport and storage contributed −1.33 points, while wholesale and retail contributed −1.12 points. "
              "These opposing contributions show why a single regional average conceals substantial industry differences.", "",
              "### Sensitivity to the comparison", "",
              "| Specification | Growth gap (pp) | Industry-mix contribution (pp) | Within-industry remainder (pp) |",
              "|---|---:|---:|---:|"]
    for row in tables["shift_share_gap"]:
        lines.append(f"| {row['case'].replace('_', ' ')} | {row['growth_gap_pp']:+.2f} | {row['industry_mix_gap_pp']:+.2f} | {row['within_industry_gap_pp']:+.2f} |")
    lines += ["", "The North West growth advantage remains positive in every specification shown. Its magnitude changes "
              "with the start and end years. Grouping 19 sections into four broader categories moves part of the industry-mix "
              "component into the remainder, so the allocation depends on the classification. Removing both focal regions "
              "from the benchmark leaves the main qualitative pattern intact.", "",
              "BRES counts jobs at their workplace. The decomposition uses sums of SIC 2007 sections A–S, built from the "
              "published two-digit divisions. Rounded divisions need not sum exactly to the separately rounded official total. "
              "The reconciliation table preserves that difference; no count is adjusted to force agreement. No standard error "
              "for this decomposition is supplied, so the growth gap is not labelled statistically significant.", "",
              "## 4. Hourly pay", "",
              f"![Hourly pay]({image_prefix}hourly_pay.png)", "",
              "| Work pattern | NW April 2026 (GBP/hour) | WM April 2026 (GBP/hour) | Gap (GBP/hour) | NW real change from 2019 (%) | WM real change from 2019 (%) |",
              "|---|---:|---:|---:|---:|---:|"]
    for row in latest_pay:
        lines.append(f"| {PATTERNS[row['work_pattern']]} | {row['north_west_gbp_hour']:.2f} | {row['west_midlands_gbp_hour']:.2f} | {row['gap_gbp_hour']:+.2f} | {row['north_west_real_growth_since_2019_pct']:+.2f} | {row['west_midlands_real_growth_since_2019_pct']:+.2f} |")
    revised = next(r for r in tables["hourly_pay_comparison"] if r["year"] == 2025 and r["work_pattern"] == "all")
    lines += ["", "The latest figures are provisional. In the revised 2025 estimates, all-employee median hourly pay was "
              f"GBP {revised['north_west_gbp_hour']:.2f} in the North West and GBP {revised['west_midlands_gbp_hour']:.2f} "
              f"in the West Midlands, a gap of GBP {revised['gap_gbp_hour']:.2f}. The latest aggregate pay gap is therefore "
              "smaller than in the revised 2025 comparison. These levels and changes are not significance-test results.", "",
              "Pay is hourly earnings excluding overtime, measured for workplace-based employee jobs on adult rates under "
              "the ASHE eligibility rules. Full-time and part-time estimates are kept separate. Real changes deflate each "
              "April estimate using the matching UK CPIH index, expressed in April 2019 prices. A common UK deflator does "
              "not measure differences in regional living costs. Changes in medians can reflect workforce composition, "
              "rather than pay changes for the same workers.", "",
              "### Pay within industries", "",
              "The following table uses revised 2025 full-time estimates. Both regional median CVs must be at most 5% to "
              "be included. The full export retains all 19 sections, including suppressed or less precise estimates. "
              "The filter is a precision screen, not a significance test.", "",
              "| Industry | NW (GBP/hour) | WM (GBP/hour) | Gap (GBP/hour) |",
              "|---|---:|---:|---:|"]
    for row in tables["industry_pay_comparison"]:
        if row["passes_cv_5pct_in_both"]:
            lines.append(f"| {row['sector_label']} | {row['north_west_gbp_hour']:.2f} | {row['west_midlands_gbp_hour']:.2f} | {row['gap_gbp_hour']:+.2f} |")
    lines += ["", "Industry medians are not averaged to construct a regional median. The table does not hold worker "
              "characteristics constant and does not estimate a like-for-like regional wage premium.", "",
              "## Reading the evidence together", "",
              "The sources support a narrower conclusion than a single ranking of the two labour markets. Resident payroll "
              "counts grew at similar rates, while workplace job growth differed more and varied across industries. Latest "
              "aggregate hourly pay estimates were close. These differences in coverage and timing matter; the data cannot "
              "establish which mechanism, such as commuting, population change or worker composition, produces the patterns.", "",
              "A causal explanation would require an identified shock or policy and a defensible comparison design. The "
              "shift-share remainder should not be interpreted as the effect of a regional policy, competitiveness or the pandemic.", "",
              "## Sources and reproduction", "",
              "- APS: July 2025–June 2026 latest window; snapshot retrieved 24 November 2026.",
              "- PAYE RTI: November 2026 release, with October early estimates separated from September.",
              "- BRES: available API years 2018–2024, source last updated 28 October 2025. The 2024 observations are provisional.",
              "- ASHE Table 5.6a/b: revised 2019, 2024 and 2025; provisional 2026.",
              "- CPIH: ONS L522, November 2026 release, matching April observations.", ""]
    for name, url in manifest["source_pages"].items():
        lines.append(f"- [{name.upper()} source]({url})")
    lines += ["", "Frozen prepared inputs and original-download hashes are in data/extended. The preparation script "
              "records original workbook names, sheet names and cells or rows. Run python code/python/research.py to "
              "regenerate this report, its tables and figures without downloading new data.", "",
              f"[APS tests]({table_prefix}aps_gap_tests.csv) · [Growth decomposition]({table_prefix}shift_share_summary.csv) · "
              f"[Industry contributions]({table_prefix}sector_gap_contributions.csv) · [Pay comparisons]({table_prefix}hourly_pay_comparison.csv)", ""]
    return "\n".join(lines)
