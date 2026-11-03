# Data dictionary

All tables are aggregates over Indian startups with a Seed or Series A round between 1 Jan 2021 and 2 Nov 2026 (Tracxn). "Tier-1 lead" means at least one of those rounds was led by one of 15 Indian funds that most often lead Seed and Series A rounds. Rates are shares (0.081 = 8.1%). Odds ratios above 1 mean more likely.

## signals_2021-2026.csv, signals_2021-2024.csv, signals_2025-2026.csv

One row per founder signal. Each comes from one logistic model per period with all signals and year, sector, city and founding-year controls.

| column | meaning |
|---|---|
| period | rounds window used for both outcome and controls |
| group | VC network, Track record, Employer, College, MBA, Team |
| signal / label | machine id / readable name |
| n | startups with at least one founder carrying the signal |
| rate_with / rate_without | raw tier-1 lead rate for startups with / without it |
| odds_ratio, lo, hi | adjusted odds ratio and 95% confidence interval |
| p, q | p-value and Benjamini–Hochberg q-value (q < 0.05 = clear, < 0.15 = likely) |

Signals in the MBA group are not exclusive: a founder can hold two. `any_mba`, `ex_vc_pe`, `repeat_founder` and `no_elite_credential` are each estimated in their own model, in place of their sub-signals.

## groups.csv

Every city and sector with at least 100 startups (2021–26).

| column | meaning |
|---|---|
| kind / name | `city` or `sector` / its name (sectors are Tracxn practice areas) |
| startups, tier1_led, tier1_rate | size and raw outcome |
| iit_share, any_mba_share, no_elite_share | share of startups with an IIT founder / an MBA founder / no elite credential |
| odds_vs_rest, lo, hi, p | adjusted odds of a tier-1 lead vs all other startups. Cities control for sector; sectors control for city. |

## group_signals.csv

Inside each city or sector: the tier-1 rate with and without each founder signal. These are raw rates with no controls, so treat them as descriptive. Rows are dropped when fewer than 25 startups have the signal, or fewer than 25 don't.

| column | meaning |
|---|---|
| kind, name | the city or sector |
| signal, label, group | the founder signal |
| n_with | startups in the group with the signal |
| rate_with, rate_without, lift | raw rates and their ratio |

## years.csv

Startups by the year of their first Seed or Series A in the window, plus `lead_recorded` (the share with any lead investor recorded in Tracxn), which shows the recent-data lag.

## mba_decomposition.csv

For each MBA type, the odds ratio as controls are added:

1. `raw`
2. `+IIT/eng`
3. `+McKinsey/unicorn/bigtech` (adds those employers and investment banks)
4. `+city/year` (adds city, year and founding year)

## ladder.csv

Raw tier-1 rate for credential profiles:

| profile | meaning |
|---|---|
| `none` | no elite credential |
| `mba_no_iit` | MBA without an IIT founder |
| `all` | every startup |
| `iit_no_mba` | IIT without an MBA founder |
| `iit_mba` | IIT and an MBA |
| `iit_mbb` | IIT plus ex-McKinsey/BCG/Bain |
| `ex_t1` | ex tier-1 VC staff |
| `ex_unicorn` | ex-Indian unicorn |

## meta.json

Sample sizes, base rate, the year mix and the publication thresholds (`min_cell` = 25 startups, `min_group` = 100).
