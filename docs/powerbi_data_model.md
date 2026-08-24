# Power BI Semantic Model Specification

## Star Schema Design

```
                        ┌─────────────────┐
                        │   dim_source     │
                        │ source_name (PK) │
                        │ dataset_period   │
                        └────────┬────────┘
                                 │ 1:M
┌──────────────┐  1:M   ┌───────┴────────┐  M:1   ┌──────────────┐
│  dim_role    │────────│  fact_jobs     │────────│ dim_location │
│ role_cat (PK)│        │ job_id (PK)    │        │ location_id  │
│              │        │ source_name(FK)│        │ city         │
└──────────────┘        │ role_category  │        │ location_grp │
                        │ seniority      │        │ country_code │
┌──────────────┐  1:M   │ company_name   │  M:1   └──────────────┘
│ dim_seniority│────────│ country_code   │
│ seniority(PK)│        │ salary_midpoint│
└──────────────┘        │ work_mode      │
                        │ employment_type│
                        │ posting_date   │
                        └───────┬────────┘
                                │ 1:M
                        ┌───────┴────────┐
                        │  fact_skills   │
                        │ job_id (FK)    │
                        │ skill_name     │
                        │ skill_category │
                        │ penetration    │
                        └────────────────┘
```

## Table Mapping

### Primary Fact Table

**13_analytical_jobs.csv** → `fact_jobs`
- Grain: 1 row = 1 unique job posting
- 8,256 rows
- Central fact table; all other tables relate through this or are independent aggregates

### Supporting Fact Tables

**08_salary_analysis.csv** → `fact_salary`
- Grain: 1 row = 1 salary observation (subset of jobs with salary data)
- 8,256 rows (all jobs, but salary_midpoint is NULL for ~5,211 PK jobs)
- Use only for salary-focused visuals

**05_skill_cocurrence.csv** → `fact_skill_pairs`
- Grain: 1 row = 1 skill pair / country combination
- 133 rows
- Independent aggregate; use for co-occurrence visuals only

### Aggregate / Summary Tables

| CSV File | Table Name | Grain | Rows | Primary Use |
|----------|-----------|-------|------|-------------|
| 01_market_overview.csv | `agg_market` | source/country | 3 | Executive KPIs |
| 02_role_demand.csv | `agg_role` | role/country | 28 | Role distribution |
| 03_skill_demand.csv | `agg_skill_demand` | skill/country | 159 | Skill penetration |
| 04_skill_comparison.csv | `agg_skill_compare` | skill | 77 | UK vs PK comparison |
| 06_role_skills.csv | `agg_role_skills` | skill/role/country | 184 | Role-specific skills |
| 07_london_analysis.csv | `agg_london` | location group | 3 | London analysis |
| 09_skill_salary.csv | `agg_skill_salary` | skill/country | 65 | Skill-salary assoc |
| 10_seniority_analysis.csv | `agg_seniority` | seniority/country | 12 | Seniority analysis |
| 11_employer_analysis.csv | `agg_employer` | company/country | 100 | Employer concentration |
| 12_temporal_analysis.csv | `agg_temporal` | month/country | 47 | Temporal trends |

## Relationships

### fact_jobs Relationships

| From Table | From Column | To Table | To Column | Cardinality | Cross-Filter |
|-----------|------------|----------|-----------|-------------|--------------|
| fact_jobs | source_name | dim_source | source_name | M:1 | Single |
| fact_jobs | role_category | dim_role | role_category | M:1 | Single |
| fact_jobs | seniority | dim_seniority | seniority | M:1 | Single |
| fact_jobs | country_code | dim_country | country_code | M:1 | Single |
| fact_jobs | work_mode | dim_workmode | work_mode | M:1 | Single |

### Aggregate Tables (Independent)

The aggregate tables (01-12) are pre-computed and do NOT join to fact_jobs. They are used independently for their respective visuals. This avoids ambiguity and circular relationships.

## Dimension Tables (Create in Power BI)

### dim_source
| Column | Type | Example |
|--------|------|---------|
| source_name | Text (PK) | adzuna_uk |
| dataset_period | Text | Recent UK (2023-2026) |
| country_code | Text | GB |

### dim_role
| Column | Type | Example |
|--------|------|---------|
| role_category | Text (PK) | data_analyst |

### dim_seniority
| Column | Type | Example |
|--------|------|---------|
| seniority | Text (PK) | junior |

### dim_country
| Column | Type | Example |
|--------|------|---------|
| country_code | Text (PK) | GB |
| country_name | Text | United Kingdom |
| dataset_period | Text | Recent UK (2023-2026) |

### dim_workmode
| Column | Type | Example |
|--------|------|---------|
| work_mode | Text (PK) | remote |

## Model Notes

1. The aggregate tables are independent — they do NOT join to fact_jobs
2. fact_jobs is the single source of truth for job-level analysis
3. Slicers on fact_jobs propagate to all visuals built on fact_jobs
4. Aggregate table visuals are standalone and use their own filters
5. No many-to-many relationships required
6. No circular relationships
