# Power BI Semantic Model Specification

Phase 6 — Workforce Intelligence Dashboard
Source of truth: PostgreSQL `job_market_analytics` → Phase 5 analytical exports in `data/analytics/`.

## 1. Modelling principles

1. **One job-grain fact.** `Jobs` is the single fact at 1 row = 1 unique posting.
   It already carries every dimension attribute produced by Phase 5 (role,
   seniority, company, city, country, work mode, salary, source, period).
   No derived dimension tables are duplicated from those attributes except the
   two listed below (`DimDate`, `DimSkill`), which are generated **inside the
   model** to avoid CSV drift.
2. **Skills need a bridge.** Skill analysis must respond to page slicers
   (role, seniority, location, date). Pre-aggregated skill CSVs cannot do that,
   so a job↔skill bridge (`JobSkills`) is exported from the existing
   `job_skills` table — same rows, reshaped. It contains no new logic: counts
   remain DISTINCT job-level links (Phase 5 rule).
3. **Disconnected aggregates are labelled.** The remaining Phase 5 CSVs are
   pre-computed views. They are imported as *reference* tables with **no
   relationships**, powering specific report visuals where live aggregation is
   unnecessary or impossible in DAX (e.g. co-occurrence pairs). Each one lists
   its consuming pages below.
4. **No many-to-many, no circular paths, no ambiguous filters.**
   The only non-single-direction behaviour in the model is achieved through a
   measure (`Jobs Requiring Selected Skills`), not through bidirectional
   relationships.
5. **NaN ≠ NULL.** PostgreSQL float8 `NaN` values export into the salary
   columns. Power Query prep (see `power_query_prep.m`) and every salary DAX
   measure guard against them. Salary Coverage % reported by this dashboard is
   therefore **lower than the naive Phase 5 CSV figure** and is the correct
   number (see `docs/powerbi_dashboard_specification.md`, Page 10).

## 2. Tables

### Connected core (live star)

| Table | Source file | Grain | Role |
|---|---|---|---|
| `Jobs` | `13_analytical_jobs.csv` | 1 job | Fact — all KPIs, salary, geography, seniority, temporal |
| `JobSkills` | `14_job_skills_bridge.csv` | 1 job × skill link | Bridge fact — skills page, role-skill profiles |
| `DimDate` | DAX `CALENDAR()` on `Jobs[posting_date]` | 1 day | Dimension — date slicer, trend visuals |
| `DimSkill` | DAX `DISTINCT(JobSkills[skill_name & category])` | 1 canonical skill | Dimension — skill slicer/matrix |
| `DimSource` | DAX table from `01_market_overview.csv` rows | 1 source | Dimension — carries `dataset_period` + data-status labels |
| `DimCountry` | DAX table (2 rows) | 1 ISO country | Dimension — country names for labels |
| `_Measures` | empty shell + `measures.dax` | — | Measure home |

### Disconnected reference aggregates (imported, no relationships)

| Table | Source file | Consuming pages | Why disconnected |
|---|---|---|---|
| `Market Overview` | `01_market_overview.csv` | P1 composition | Already aggregated per source |
| `Role Demand` | `02_role_demand.csv` | P1, P8 fallback | Role × country roll-up incl. seniority split |
| `Skill Comparison` | `04_skill_comparison.csv` | P6 | UK/PK rank-diff computed in SQL |
| `Skill Co-occurrence` | `05_skill_cocurrence.csv` | P9 | Pair combinations not expressible in DAX |
| `Role Skills (agg)` | `06_role_skills.csv` | P9 career cards | Pre-filtered ≥3-job threshold |
| `London Analysis` | `07_london_analysis.csv` | P3 validation strip | Fixed London/UK-Other split |
| `Skill Salary` | `09_skill_salary.csv` | P7 | SQL percentile association, GB rows only after PQ filter |
| `Seniority Analysis` | `10_seniority_analysis.csv` | P8 validation | Seniority × country roll-up |
| `Employer Analysis` | `11_employer_analysis.csv` | P2 top employers | Top-100 concentration list |
| `Temporal Analysis` | `12_temporal_analysis.csv` | P1 trend validation | Month × source roll-up |
| `Salary Analysis (ref)` | `08_salary_analysis.csv` | none (validation only) | Superseded inside the model by `Jobs[salary_midpoint]`; imported only so QA can reconcile |

Not imported: nothing else. `03_skill_demand` is intentionally **not imported**
as a visual source because everything it contains is computed live from
`Jobs × JobSkills` with correct cross-filtering; it remains the QA benchmark.

## 3. Relationships

| From (1) | To (*) | Cardinality | Cross-filter | Notes |
|---|---|---|---|---|
| `DimDate[date]` | `Jobs[posting_date]` | 1:* | single | Date slicer drives all pages |
| `DimSource[source_name]` | `Jobs[source_name]` | 1:* | single | Period/status labels onto jobs |
| `DimCountry[country_code]` | `Jobs[country_code]` | 1:* | single | Country naming |
| `DimSkill[skill_name]` | `JobSkills[skill_name]` | 1:* | single | Skill slicers |
| `Jobs[job_id]` | `JobSkills[job_id]` | 1:* | single | Job context flows INTO skills |

Filter flow: `DimDate / DimSource / DimCountry / DimSkill → facts`.
Slicing any job attribute (role, seniority, city, work mode…) filters
`Jobs → JobSkills`, which makes `Skill Penetration %` contextual under every
page filter. "Which jobs require skill X" is answered by the
`Jobs Requiring Selected Skills` measure (expanded-table join in DAX) instead
of enabling bidirectionality — zero m:m risk.

## 4. Calculated columns (kept minimal)

| Table | Column | DAX intent |
|---|---|---|
| `Jobs` | `salary_usable` | `AND(NOT ISBLANK([salary_midpoint]), NOT ISNAN([salary_midpoint]))` — used by PQ alternative; measures re-guard anyway |
| `DimDate` | `Year`, `Month`, `YearMonthKey`, `YearMonth Label` | standard calendar attributes |

Everything else stays a measure. No role-playing date tables needed (single
posting date).

## 5. Row-level context labels (honesty layer)

`DimSource` carries:

| source_name | country_code | dataset_period | data_status |
|---|---|---|---|
| adzuna_uk | GB | Recent UK (2023–2026) | Recent postings |
| chisel_pk | PK | Historical PK (2019–2021) | Historical archive |
| kaggle_rozee_pk | PK | Supplementary PK | Small supplementary sample |

Every page header includes `Title Market Context` (dynamic) plus the fixed
disclaimer text specified in `docs/powerbi_dashboard_specification.md` §Page 1.

## 6. Build order (Power BI Desktop)

1. Get Data → Text/CSV: import all files from `data/analytics/`
   (`01`–`14`, the bridge included).
2. Apply `power_query_prep.m` transformations (types, NaN→null for salary
   columns, trim company/city blanks).
3. Create `DimDate`, `DimSkill`, `DimSource`, `DimCountry`, `_Measures`
   calculated tables/columns per §2/§4.
4. Create relationships per §3 (Power BI will auto-detect most; verify filter
   direction = single on every one).
5. Paste `measures.dax` into `_Measures`.
6. Apply `theme.json` (View ▸ Themes ▸ Browse for themes).
7. Build pages per `docs/powerbi_dashboard_specification.md`.
