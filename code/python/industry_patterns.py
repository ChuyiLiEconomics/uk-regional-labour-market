"""Trace annual job changes and the manufacturing composition of the two regions."""
from collections import defaultdict
import math


def annual_changes(sections, focus, baseline=2019):
    values = {}
    labels = {}
    for row in sections:
        key = (row['region'], row['sector'], row['year'])
        if key in values:
            raise ValueError('Duplicate annual industry cell')
        value = row['employees']
        if value is None or not math.isfinite(value) or value < 0:
            raise ValueError('Invalid annual industry count')
        values[key] = value
        labels[row['sector']] = row['sector_label']
    years = sorted({r['year'] for r in sections})
    names = {r['region'] for r in sections}
    industries = sorted(labels)
    if not years or years != list(range(years[0], years[-1] + 1)) or baseline not in years or not set(focus).issubset(names):
        raise ValueError('A continuous annual panel and the baseline are required')
    if any((n, s, y) not in values for n in names for s in industries for y in years):
        raise ValueError('Incomplete annual industry panel')
    totals = {(n, y): math.fsum(values[(n, s, y)] for s in industries) for n in names for y in years}
    if any(v <= 0 for v in totals.values()):
        raise ValueError('Annual regional totals must be positive')
    paths = []
    for n in focus:
        base = totals[(n, baseline)]
        for y in years:
            current = totals[(n, y)]
            paths.append({'year': y, 'region': n, 'employees': current, 'baseline_year': baseline,
                          'baseline_employees': base, 'index_baseline_100': 100 * current / base,
                          'growth_since_baseline_pct': 100 * (current / base - 1),
                          'year_on_year_pct': 100 * (current / totals[(n, y - 1)] - 1) if y > years[0] else None})
    gaps, contributions = [], []
    a, b = focus
    previous_gap = None
    for y in [v for v in years if v >= baseline]:
        growth = {n: 100 * (totals[(n, y)] / totals[(n, baseline)] - 1) for n in focus}
        gap = growth[a] - growth[b]
        annual = gap - previous_gap if previous_gap is not None else None
        gaps.append({'year': y, 'baseline_year': baseline, 'north_west_growth_pct': growth[a],
                     'west_midlands_growth_pct': growth[b], 'growth_gap_pp': gap,
                     'annual_gap_contribution_pp': annual})
        if y > baseline:
            for s in industries:
                changes = {n: values[(n, s, y)] - values[(n, s, y - 1)] for n in focus}
                contributions.append({'start_year': y - 1, 'end_year': y, 'sector': s, 'sector_label': labels[s],
                                      'north_west_job_change': changes[a], 'west_midlands_job_change': changes[b],
                                      'north_west_contribution_pp': 100 * changes[a] / totals[(a, baseline)],
                                      'west_midlands_contribution_pp': 100 * changes[b] / totals[(b, baseline)],
                                      'growth_gap_contribution_pp': 100 * (changes[a] / totals[(a, baseline)] - changes[b] / totals[(b, baseline)])})
            calculated = math.fsum(r['growth_gap_contribution_pp'] for r in contributions if r['end_year'] == y)
            if not math.isclose(calculated, annual, abs_tol=1e-9):
                raise ValueError('Annual industry contributions do not reconcile')
        previous_gap = gap
    return paths, gaps, contributions


def manufacturing_changes(divisions, sections, focus, baseline=2019, endpoint=2024):
    totals = defaultdict(float)
    for row in sections:
        totals[(row['region'], row['year'])] += row['employees']
    selected = [r for r in divisions if r['division'] != 'TOTAL' and 10 <= int(r['division']) <= 33 and
                r['region'] in focus and r['year'] in [baseline, endpoint]]
    values = {}
    labels = {}
    for row in selected:
        key = (row['region'], row['division'], row['year'])
        if key in values:
            raise ValueError('Duplicate manufacturing cell')
        if row['employees'] is None or not math.isfinite(row['employees']) or row['employees'] < 0:
            raise ValueError('Invalid manufacturing count')
        values[key] = row['employees']
        labels[row['division']] = row['division_label']
    result = []
    for n in focus:
        base_manufacturing = math.fsum(values[(n, d, baseline)] for d in labels if (n, d, baseline) in values)
        if base_manufacturing <= 0 or totals[(n, baseline)] <= 0:
            raise ValueError('Manufacturing and covered baselines must be positive')
        for d, label in sorted(labels.items()):
            if any((n, d, y) not in values for y in [baseline, endpoint]):
                raise ValueError('Incomplete manufacturing endpoints')
            start, end = values[(n, d, baseline)], values[(n, d, endpoint)]
            if any(v is None or not math.isfinite(v) or v < 0 for v in [start, end]):
                raise ValueError('Invalid manufacturing count')
            result.append({'region': n, 'division': d, 'division_label': label, 'start_year': baseline,
                           'end_year': endpoint, 'baseline_employees': start, 'end_employees': end,
                           'change_jobs': end - start, 'growth_pct': 100 * (end / start - 1) if start > 0 else None,
                           'baseline_share_of_manufacturing_pct': 100 * start / base_manufacturing,
                           'baseline_share_of_covered_jobs_pct': 100 * start / totals[(n, baseline)],
                           'growth_contribution_pp': 100 * (end - start) / totals[(n, baseline)]})
    return result
