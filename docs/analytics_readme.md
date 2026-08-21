# Phase 5: Workforce Market Analytics

## Overview

Analytical intelligence layer transforming validated job-market data into workforce insights for Data Analyst, Business Intelligence, and Data Science career planning.

## Dataset Limitations

**Critical temporal mismatch:**
- **Recent UK postings** (Adzuna): 2023–2026
- **Historical Pakistan postings** (CHISEL/LUMS): December 2019–March 2021
- **Supplementary Pakistan** (Kaggle Rozee): Small sample

All analyses explicitly label which dataset period they reference. UK vs Pakistan comparisons are NOT current 2026 comparisons.

## Data Summary

| Metric | Value |
|--------|-------|
| Total unique jobs | 8,256 |
| UK jobs (Recent) | 3,029 |
| Pakistan jobs (Historical) | 5,211 |
| Pakistan jobs (Supplementary) | 16 |
| Unique skills extracted | 77 |
| Total skill mentions | 7,233 |
| Jobs with salary data | 3,045 |
| Unique companies | 3,889 |
| Unique locations | 193 |

## Analytical Architecture

```
PostgreSQL (job_market_analytics)
    ├── 14 production tables
    ├── 13 analytical views (v_analytical_jobs, v_skill_demand, etc.)
    └── SQL scripts (sql/analytics/)

Python Analytics (src/analytics/engine.py)
    ├── SQL queries via analytical views
    ├── Parquet-based validation
    ├── Statistical tests (scipy)
    └── Power BI-ready CSV outputs (data/analytics/)
```

## SQL Views

| View | Grain | Purpose |
|------|-------|---------|
| `v_analytical_jobs` | 1 row = 1 job | Enriched fact table with all dimensions |
| `v_market_overview` | 1 row = 1 source/country | High-level market metrics |
| `v_role_demand` | 1 row = 1 role/country | Role distribution |
| `v_skill_demand` | 1 row = 1 skill/country | Job-level skill penetration |
| `v_skill_comparison` | 1 row = 1 skill | UK vs PK penetration diff |
| `v_skill_cocurrence` | 1 row = 1 skill pair | Skills appearing together |
| `v_role_skills` | 1 row = 1 skill/role | Role-specific skill profiles |
| `v_london_analysis` | 1 row = 1 location group | London vs rest of UK |
| `v_salary_analysis` | 1 row = 1 salary observation | Salary by role/seniority |
| `v_skill_salary` | 1 row = 1 skill with salary | Skill-salary association |
| `v_seniority_analysis` | 1 row = 1 seniority/country | Seniority distribution |
| `v_employer_analysis` | 1 row = 1 company | Hiring concentration |
| `v_temporal_analysis` | 1 row = 1 month/country | Temporal patterns |

## Key Findings

### UK Market (Recent 2023-2026)
- **Top skills:** Reporting (10.9%), Machine Learning (7.6%), Leadership (4.6%), Business Intelligence (3.9%), Data Governance (3.5%)
- **London dominance:** 2,312 of 3,029 UK jobs (76%)
- **Role mix:** Data Analyst 24.4%, Data Scientist 12.6%, Analytics Engineer 9.5%
- **Seniority:** Senior 50%, Junior 8.9%, Unknown 40.8%

### Pakistan Market (Historical 2019-2021)
- **Top skills:** PHP (7.4%), Communication (5.1%), JavaScript (3.9%), C# (2.2%), HTML (2.3%)
- **Cities:** Lahore (32%), Islamabad (29%), Karachi (25%)
- **Role mix:** 99% classified as "other" (non-data roles)
- **Seniority:** Junior 76%, Mid 21%

### Skill Overlap & Differences
- **UK-emphasized:** Reporting, Machine Learning, Leadership, BI, Data Governance, Python, SQL, A/B Testing
- **PK-emphasized:** PHP, Communication, JavaScript, C#, HTML, CSS, MySQL
- **Common ground:** SQL, Python, Excel, AWS (present in both but higher UK penetration)

### Salary Intelligence (UK Only)
- Senior roles: ~£47,532 median
- Junior roles: ~£50,456 median
- Statistical test: Mann-Whitney U p=0.07 (not significant at α=0.05)
- Note: Small sample sizes limit salary conclusions

### Statistical Validation
- Chi-square test on skill distribution: p≈0 (significant difference between UK and PK)
- Mann-Whitney U on salary by seniority: p=0.07 (not significant)

## Analytical Rules

1. Skill counts use job-level penetration (each job counted once per skill)
2. Salary analysis uses only advertised salaries, no estimation
3. Missing data is explicitly reported, never imputed
4. Statistical significance ≠ practical importance
5. No causal claims from observational data

## Power BI-Ready Outputs

13 CSV files in `data/analytics/` ready for direct Power BI import:
- `01_market_overview.csv` through `13_analytical_jobs.csv`

## Running

```bash
# Run full analytics pipeline
python -m analytics.engine

# Run tests
pytest tests/ -x

# Lint
ruff check src/ tests/
```
