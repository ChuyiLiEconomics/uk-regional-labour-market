-- Parameters are ONS geography codes, not region names.
SELECT o.indicator, o.period_end, MAX(o.period_label) AS period_label,
       MAX(CASE WHEN o.region_code = :region_a THEN r.name END) AS region_a,
       MAX(CASE WHEN o.region_code = :region_b THEN r.name END) AS region_b,
       MAX(CASE WHEN o.region_code = :region_a THEN o.rate_pct END) AS region_a_pct,
       MAX(CASE WHEN o.region_code = :region_b THEN o.rate_pct END) AS region_b_pct,
       ROUND(MAX(CASE WHEN o.region_code = :region_a THEN o.rate_pct END)
           - MAX(CASE WHEN o.region_code = :region_b THEN o.rate_pct END), 2) AS gap_pp
FROM observations o
JOIN regions r ON r.code = o.region_code
WHERE o.region_code IN (:region_a, :region_b)
GROUP BY o.indicator, o.period_end
HAVING COUNT(*) = 2 AND COUNT(o.rate_pct) = 2
ORDER BY o.indicator, o.period_end;
