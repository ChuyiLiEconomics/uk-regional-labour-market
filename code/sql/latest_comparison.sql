-- Find a common valid period; do not compare different survey periods.
WITH comparable AS (
    SELECT indicator, period_end
    FROM observations
    GROUP BY indicator, period_end
    HAVING COUNT(*) = 2 AND COUNT(rate_pct) = 2
), latest AS (
    SELECT indicator, MAX(period_end) AS period_end
    FROM comparable
    GROUP BY indicator
)
SELECT o.indicator, o.period_end, MAX(o.period_label) AS period_label,
       MAX(CASE WHEN r.name = 'North West' THEN o.rate_pct END) AS north_west_pct,
       MAX(CASE WHEN r.name = 'West Midlands' THEN o.rate_pct END) AS west_midlands_pct,
       ROUND(MAX(CASE WHEN r.name = 'North West' THEN o.rate_pct END)
           - MAX(CASE WHEN r.name = 'West Midlands' THEN o.rate_pct END), 2) AS gap_pp
FROM observations o
JOIN regions r ON r.code = o.region_code
JOIN latest l ON l.indicator = o.indicator AND l.period_end = o.period_end
GROUP BY o.indicator, o.period_end
ORDER BY o.indicator;
