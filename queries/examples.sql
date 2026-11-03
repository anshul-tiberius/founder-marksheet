-- Run from the repo root with DuckDB:  duckdb -c ".read queries/examples.sql"

-- 1. Which founder signals matter most, all else equal (2021-26)?
SELECT label, n, round(odds_ratio, 2) AS odds, round(lo, 2) AS lo, round(hi, 2) AS hi, round(q, 3) AS q
FROM 'data/signals_2021-2026.csv' ORDER BY odds_ratio DESC;

-- 2. What changed between 2021-24 and 2025-26?
SELECT a.label, round(a.odds_ratio, 2) AS odds_2021_24, round(b.odds_ratio, 2) AS odds_2025_26, round(b.q, 3) AS q_2025_26
FROM 'data/signals_2021-2024.csv' a JOIN 'data/signals_2025-2026.csv' b USING (signal)
ORDER BY b.odds_ratio - a.odds_ratio DESC;

-- 3. Cities ranked by adjusted odds of a tier-1 lead
SELECT name, startups, round(tier1_rate * 100, 1) AS tier1_pct, round(odds_vs_rest, 2) AS odds, round(p, 3) AS p
FROM 'data/groups.csv' WHERE kind = 'city' ORDER BY odds_vs_rest DESC;

-- 4. What does Hyderabad look like, signal by signal?
SELECT label, n_with, round(rate_with * 100, 1) AS with_pct, round(rate_without * 100, 1) AS without_pct, round(lift, 2) AS lift
FROM 'data/group_signals.csv' WHERE kind = 'city' AND name = 'Hyderabad' ORDER BY lift DESC;

-- 5. Where does an IIT founder help most?
SELECT kind, name, n_with, round(rate_with * 100, 1) AS with_pct, round(rate_without * 100, 1) AS without_pct, round(lift, 2) AS lift
FROM 'data/group_signals.csv' WHERE signal = 'iit' ORDER BY lift DESC;

-- 6. Sectors where tier-1 funds lead most often
SELECT name, startups, tier1_led, round(tier1_rate * 100, 1) AS tier1_pct, round(odds_vs_rest, 2) AS odds
FROM 'data/groups.csv' WHERE kind = 'sector' ORDER BY tier1_rate DESC;
