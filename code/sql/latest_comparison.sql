-- period_comparisons contains only periods with two valid rates.
WITH latest AS (
    SELECT indicator, MAX(period_end) AS period_end
    FROM period_comparisons
    GROUP BY indicator
)
SELECT p.*
FROM period_comparisons p
JOIN latest l ON l.indicator = p.indicator AND l.period_end = p.period_end
ORDER BY p.indicator;
