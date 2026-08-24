# Power BI Dashboard Specification

## Design System

- **Primary colors:** #1B2A4A (navy), #2E86AB (teal), #A23B72 (accent), #F18F01 (warning), #C73E1D (alert)
- **Background:** #F5F7FA
- **Text:** #1B2A4A primary, #5A6B7F secondary
- **Fonts:** Segoe UI Semibold (headings), Segoe UI (body)
- **Card style:** White background, subtle shadow, left colored border
- **Charts:** Minimal gridlines, no chart borders, direct labeling preferred
- **Slicers:** Dropdown style, top of page, consistent order

---

## Page 1: Executive Workforce Overview

**Purpose:** High-level summary of the entire dataset
**Audience:** Recruiters, interviewers, project stakeholders
**Layout:** 4 KPI cards top row, 2 charts middle, 2 charts bottom

### KPI Cards (Top Row)
| Card | Measure | Format | Subtitle |
|------|---------|--------|----------|
| Total Jobs | [Total Jobs] | #,##0 | "8,256 job postings analyzed" |
| UK Jobs (Recent) | [UK Jobs] | #,##0 | "2023-2026 Adzuna data" |
| PK Jobs (Historical) | [Pakistan Jobs] | #,##0 | "2019-2021 CHISEL data" |
| Companies | [Unique Companies] | #,##0 | "Across all sources" |

### Methodology Banner
Full-width text box with:
> **Dataset Limitation:** UK data is recent (2023-2026). Pakistan data is historical (2019-2021). These datasets are NOT temporally equivalent and should NOT be compared as current market conditions.

### Charts
| Visual | Type | Data Source | Config |
|--------|------|-------------|--------|
| Dataset Composition | Donut chart | fact_jobs by source_name | 3 segments: adzuna_uk, chisel_pk, kaggle_rozee_pk |
| Role Distribution | Horizontal bar | fact_jobs by role_category | Sorted desc, top 10 |
| Top 10 Skills | Horizontal bar | agg_skill_demand (UK only, top 10 by penetration) | Penetration % labels |
| Seniority Distribution | Donut chart | fact_jobs by seniority | 4 segments |

### Filters
- Country slicer (hidden — page-level filter: show all)
- Source slicer (dropdown, default: all)

---

## Page 2: UK Job Market

**Purpose:** Deep dive into recent UK job market
**Audience:** Data Analyst/BI job seekers targeting UK
**Layout:** 5 KPI cards top, 4 charts middle, 3 charts bottom

### KPI Cards
| Card | Measure |
|------|---------|
| UK Jobs | [UK Jobs] |
| UK Companies | [UK Companies] |
| Data Analyst | [Data Analyst Count] |
| Data Scientist | [Data Scientist Count] |
| Median Salary | [UK Median Salary] |

### Charts
| Visual | Type | Data Source | Config |
|--------|------|-------------|--------|
| Jobs by Role | Horizontal bar | fact_jobs WHERE country_code=GB, by role_category | Sorted desc |
| Top 15 UK Skills | Horizontal bar | agg_skill_demand WHERE country_code=GB | Top 15 by penetration_pct |
| Salary Distribution | Histogram | fact_jobs WHERE country_code=GB AND has_salary=TRUE | 10 bins of £10,000 |
| Seniority Breakdown | Donut | fact_jobs WHERE country_code=GB, by seniority | |
| Work Mode | Donut | fact_jobs WHERE country_code=GB, by work_mode | |
| Employment Type | Bar | fact_jobs WHERE country_code=GB, by employment_type | |
| Jobs by Location (Top 15) | Horizontal bar | fact_jobs WHERE country_code=GB, by city | Top 15 |

### Slicers
- Role Category (dropdown)
- Seniority (dropdown)
- Location Group (dropdown: London, Greater London, UK Other)
- Work Mode (dropdown)

---

## Page 3: London Intelligence

**Purpose:** London-specific market analysis
**Audience:** London-targeting job seekers
**Layout:** 4 KPI cards, 4 charts, comparison section

### KPI Cards
| Card | Measure |
|------|---------|
| London Jobs | [London Jobs] |
| Greater London | [Greater London Jobs] |
| London Data Analyst | CALCULATE([Data Analyst Count], location_group="London") |
| London Median Salary | [London Median Salary] |

### Charts
| Visual | Type | Data Source | Config |
|--------|------|-------------|--------|
| London vs UK Comparison | Grouped bar | agg_london | 3 groups: London, Greater London, UK Other; metrics: total_jobs, data_analyst_jobs, data_scientist_jobs |
| London Roles | Horizontal bar | fact_jobs WHERE location_group IN ('London','Greater London'), by role_category | |
| London Top Skills | Horizontal bar | agg_skill_demand WHERE country_code=GB, filtered to London-relevant roles | Top 12 |
| London Seniority | Donut | fact_jobs WHERE location_group IN ('London','Greater London'), by seniority | |
| London Work Mode | Donut | fact_jobs WHERE location_group IN ('London','Greater London'), by work_mode | |

### Slicers
- Location Group (dropdown)
- Role Category (dropdown)

---

## Page 4: Pakistan Historical Market

**Purpose:** Historical Pakistan job market context
**Audience:** Market comparison, historical analysis
**Layout:** Prominent HISTORICAL label, KPIs, charts

### Prominent Label
> **HISTORICAL DATA — 2019-2021**
> This page shows historical Pakistan job postings from the CHISEL/LUMS dataset. These are NOT current 2026 conditions.

### KPI Cards
| Card | Measure |
|------|---------|
| PK Jobs | [Pakistan Jobs] |
| PK Companies | [PK Companies] |
| PK Cities | CALCULATE(DISTINCTCOUNT(fact_jobs[city]), country_code="PK") |
| PK Skills | CALCULATE(DISTINCTCOUNT(agg_skill_demand[skill_name]), country_code="PK") |

### Charts
| Visual | Type | Data Source | Config |
|--------|------|-------------|--------|
| Jobs by City | Horizontal bar | fact_jobs WHERE country_code=PK, by city | Sorted desc |
| Top 15 PK Skills | Horizontal bar | agg_skill_demand WHERE country_code=PK | Top 15 |
| Seniority | Donut | fact_jobs WHERE country_code=PK, by seniority | |
| Role Classification | Text box | Explain 99% "other" is due to CHISEL taxonomy, not absence of data roles |

### Slicers
- City (dropdown)
- Seniority (dropdown)

---

## Page 5: Skills Intelligence

**Purpose:** Core skills analysis — the strongest page
**Audience:** All stakeholders
**Layout:** KPIs, 3-4 major charts, slicers

### KPI Cards
| Card | Measure |
|------|---------|
| Total Unique Skills | 77 (static or calculated) |
| Most Demanded (UK) | "Reporting" (top UK skill) |
| Most Demanded (PK) | "PHP" (top PK skill) |
| Skills with Salary Data | 65 |

### Charts
| Visual | Type | Data Source | Config |
|--------|------|-------------|--------|
| Top 20 Skills: UK vs PK | Clustered bar | agg_skill_demand (combine UK+PK, top 20 by total) | Two bars per skill: UK penetration, PK penetration |
| Skill Category Treemap | Treemap | agg_skill_demand, by skill_category | Size = total job_count |
| Skill Penetration Heatmap | Matrix/table | agg_skill_demand (top 15 skills x UK/PK) | Color scale on penetration_pct |
| Role-Specific Top Skills | Matrix | agg_role_skills (top 5 skills per role for UK) | Rows: role_category, Columns: skill_name, Values: penetration_pct |

### Slicers
- Country (dropdown: All, GB, PK)
- Role Category (dropdown)
- Skill Category (dropdown: technical, analytical, ai_ml, tool, business_soft, education)

---

## Page 6: Skill Comparison

**Purpose:** Direct UK vs PK skill comparison
**Audience:** Cross-market analysts
**Layout:** Scatter plot dominant, supporting charts

### KPI Cards
| Card | Measure |
|------|---------|
| Common Skills | CALCULATE(COUNTROWS(agg_skill_compare), emphasis="UK-emphasized" OR emphasis="PK-emphasized") |
| UK-Emphasized | CALCULATE(COUNTROWS(agg_skill_compare), emphasis="UK-emphasized") |
| PK-Emphasized | CALCULATE(COUNTROWS(agg_skill_compare), emphasis="PK-emphasized") |

### Charts
| Visual | Type | Data Source | Config |
|--------|------|-------------|--------|
| UK vs PK Penetration | Scatter plot | agg_skill_compare | X=uk_penetration_pct, Y=pk_penetration_pct, Size=uk_job_count+pk_job_count, Labels=skill_name |
| Penetration Divergence | Diverging bar | agg_skill_compare (top 20) | Left=PK, Right=UK, sorted by abs(penetration_diff) |
| Emphasis Classification | Table | agg_skill_compare | Columns: skill_name, uk_pen, pk_pen, diff, emphasis |

### Note
> Temporal limitation: UK data is 2023-2026, PK data is 2019-2021. Differences may reflect dataset period, not market evolution.

---

## Page 7: Salary Intelligence

**Purpose:** UK salary analysis (PK has no salary data)
**Audience:** Job seekers, salary benchmarking
**Layout:** KPIs, distribution, breakdowns

### KPI Cards
| Card | Measure |
|------|---------|
| UK Median Salary | [UK Median Salary] |
| UK Average Salary | [UK Average Salary] |
| Salary Range | [Minimum Salary] & " - " & [Maximum Salary] |
| Jobs with Salary | [Jobs with Salary] |

### Charts
| Visual | Type | Data Source | Config |
|--------|------|-------------|--------|
| Salary Distribution | Histogram | fact_jobs WHERE country_code=GB AND has_salary=TRUE | Bins: £0-20k, 20-30k, 30-40k, 40-50k, 50-60k, 60-70k, 70-80k, 80-100k, 100k+ |
| Salary by Role | Bar with error bars | agg_role (UK only, where avg_salary_midpoint IS NOT NULL) | Bar=avg, error=range |
| Salary by Seniority | Grouped bar | fact_jobs WHERE country_code=GB AND has_salary=TRUE, by seniority | Median salary per seniority |
| Salary by Location | Bar | fact_jobs WHERE country_code=GB AND has_salary=TRUE, by location_group | Median per group |
| Skill-Salary Association | Scatter | agg_skill_salary WHERE country_code=GB | X=job_count, Y=median_salary, Labels=skill_name |

### Slicers
- Role Category (dropdown)
- Seniority (dropdown)
- Location Group (dropdown)

---

## Page 8: Role & Seniority Analysis

**Purpose:** Detailed role and seniority breakdown
**Audience:** Career planners, recruiters
**Layout:** Role overview, cross-tabulations

### Charts
| Visual | Type | Data Source | Config |
|--------|------|-------------|--------|
| Role Distribution | Treemap | fact_jobs, by role_category | Size = job_count |
| Role x Seniority | Matrix | agg_role (UK) | Rows: role_category, Columns: seniority, Values: job_count |
| Role x Work Mode | Stacked bar | fact_jobs WHERE country_code=GB, by role_category + work_mode | 100% stacked |
| Top Skills per Role | Small multiples | agg_role_skills WHERE country_code=GB | 4 charts: Data Analyst, Data Scientist, Analytics Engineer, Data Architect; each shows top 8 skills |

### Slicers
- Country (dropdown)
- Seniority (dropdown)

---

## Page 9: Career Intelligence

**Purpose:** Career progression intelligence
**Audience:** Data Analyst job seekers
**Layout:** 3-column progression layout

### Structure
Three columns showing progression:

**Column 1: Data Analyst**
- Top 10 skills (bar)
- Skill categories (donut)
- Salary range
- UK demand: [Data Analyst Count]

**Column 2: Analytics Engineer**
- Top 10 skills (bar)
- Skill categories (donut)
- Salary range
- UK demand: [Analytics Engineer Count]

**Column 3: Data Scientist**
- Top 10 skills (bar)
- Skill categories (donut)
- Salary range
- UK demand: [Data Scientist Count]

### Data Source
agg_role_skills for each role, filtered to country_code=GB

### Note
> Market intelligence from job postings. Not a personal skill assessment.

---

## Page 10: Data Quality & Methodology

**Purpose:** Transparency and credibility
**Audience:** Interviewers, technical reviewers
**Layout:** Structured information sections

### Sections

**1. Data Sources**
| Source | Period | Jobs | Country | Method |
|--------|--------|------|---------|--------|
| Adzuna API | 2023-2026 | 3,029 | UK | REST API |
| CHISEL/LUMS | 2019-2021 | 5,211 | Pakistan | CSV (Kaggle) |
| Kaggle Rozee | Various | 16 | Pakistan | CSV |

**2. NLP Methodology**
- Lexicon-based skill extraction with 78 canonical skills
- Contextual disambiguation for ambiguous skills (R, Go, Scala, SAS)
- Word boundary matching to prevent false positives
- Confidence scoring: high/medium/low

**3. Role Classification**
- Title-normalizer keyword matching
- 12 role categories defined
- 89.5% of PK jobs classified as "other" (CHISEL taxonomy limitation)

**4. Known Limitations**
- UK and PK datasets are NOT temporally equivalent
- PK data is historical (2019-2021), not current
- Skill extraction limited to 78 canonical skills
- Salary data only available for UK (Adzuna)
- Role classification weak for PK data
- Job postings ≠ complete labor market

**5. Statistical Tests**
- Chi-square: Skill distribution differs significantly between UK and PK (p≈0)
- Mann-Whitney U: Senior vs Junior salary difference not significant (p=0.07)

**6. How to Read This Dashboard**
- Use slicers to filter by country, role, seniority
- Skill penetration % = jobs with skill / total jobs in filter context
- Salary data is UK-only; PK pages show no salary
- London analysis uses location_group from the enriched fact table
