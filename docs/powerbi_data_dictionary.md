# Power BI Data Dictionary

## 13_analytical_jobs.csv — Primary Fact Table

| Column | Type | Description | Source | Example |
|--------|------|-------------|--------|---------|
| job_id | Integer | Unique job identifier | jobs.job_id | 1234 |
| job_title | Text | Original job title | jobs.job_title | "Senior Data Analyst" |
| normalized_title | Text | Cleaned/normalized title | job_titles.normalized_title | "data analyst" |
| role_category | Text | Classified role | job_titles.role_category | "data_analyst" |
| seniority | Text | Seniority level | job_titles.seniority | "senior" |
| company_name | Text | Company name | companies.name | "Amazon" |
| city | Text | City | locations.city | "London" |
| region | Text | Region | locations.region | NULL |
| country_code | Text | ISO country code | jobs.country | "GB" |
| location_group | Text | Grouped location | Derived | "London" |
| salary_min | Numeric | Minimum advertised salary | jobs.salary_min | 35000.00 |
| salary_max | Numeric | Maximum advertised salary | jobs.salary_max | 55000.00 |
| salary_currency | Text | Currency code | jobs.salary_currency | "GBP" |
| salary_period | Text | Pay period | jobs.salary_period | "annual" |
| salary_type | Text | Advertised vs estimated | jobs.salary_type | "advertised" |
| employment_type | Text | Contract type | jobs.employment_type | "permanent" |
| work_mode | Text | Remote/hybrid/on-site | jobs.work_mode | "hybrid" |
| experience_level | Text | Experience requirement | jobs.experience_level | NULL |
| education_requirement | Text | Education requirement | jobs.education_requirement | "bachelors" |
| posting_date | Date | Job posting date | jobs.posting_date | 2024-03-15 |
| collected_at | DateTime | When data was collected | jobs.collected_at | 2026-08-21 |
| dq_score | Numeric | Data quality score (0-100) | jobs.dq_score | 85.00 |
| source_name | Text | Data source | job_sources.name | "adzuna_uk" |
| has_salary | Boolean | Whether salary data exists | Derived | true |
| salary_midpoint | Numeric | (min+max)/2 salary | Derived | 45000.00 |
| dataset_period | Text | Human-readable period | Derived | "Recent UK (2023-2026)" |

## 08_salary_analysis.csv — Salary Fact

Same grain as analytical_jobs but focused on salary fields. All 8,256 rows included; salary_midpoint is NULL for jobs without salary data.

Additional column: job_title (original title for reference)

## 05_skill_cocurrence.csv — Skill Pairs

| Column | Type | Description |
|--------|------|-------------|
| skill_a | Text | First skill (alphabetically) |
| skill_b | Text | Second skill |
| country_code | Text | Country |
| co_occurrence_count | Integer | Jobs containing both skills |
| co_occurrence_pct | Numeric | % of country's jobs |

## 01_market_overview.csv — Market Summary

| Column | Type | Description |
|--------|------|-------------|
| country_code | Text | Country |
| source_name | Text | Data source |
| dataset_period | Text | Period label |
| total_jobs | Integer | Job count |
| jobs_with_salary | Integer | Jobs with salary |
| salary_coverage_pct | Numeric | Salary coverage % |
| remote_jobs | Integer | Remote job count |
| hybrid_jobs | Integer | Hybrid job count |
| on_site_jobs | Integer | On-site job count |
| unique_companies | Integer | Distinct companies |
| unique_cities | Integer | Distinct cities |
| avg_dq_score | Numeric | Average DQ score |

## 02_role_demand.csv — Role Distribution

| Column | Type | Description |
|--------|------|-------------|
| role_category | Text | Role classification |
| country_code | Text | Country |
| dataset_period | Text | Period label |
| job_count | Integer | Jobs in this role/country |
| pct_within_country | Numeric | % of country's jobs |
| junior_count | Integer | Junior-level jobs |
| mid_count | Integer | Mid-level jobs |
| senior_count | Integer | Senior-level jobs |
| unknown_seniority | Integer | Unclassified seniority |
| jobs_with_salary | Integer | Jobs with salary |
| avg_salary_midpoint | Numeric | Average salary midpoint |

## 03_skill_demand.csv — Skill Penetration

| Column | Type | Description |
|--------|------|-------------|
| skill_name | Text | Canonical skill name |
| skill_category | Text | Category (technical/analytical/ai_ml/tool/business_soft/education) |
| country_code | Text | Country |
| dataset_period | Text | Period label |
| job_count | Integer | Jobs requiring this skill |
| penetration_pct | Numeric | % of country's jobs with this skill |

## 04_skill_comparison.csv — UK vs PK Comparison

| Column | Type | Description |
|--------|------|-------------|
| skill_name | Text | Skill name |
| skill_category | Text | Category |
| uk_job_count | Integer | UK jobs with skill |
| uk_penetration_pct | Numeric | UK penetration % |
| pk_job_count | Integer | PK jobs with skill |
| pk_penetration_pct | Numeric | PK penetration % |
| penetration_diff | Numeric | UK - PK difference |
| emphasis | Text | "UK-emphasized", "PK-emphasized", or "Equal" |

## 06_role_skills.csv — Role-Specific Skills

| Column | Type | Description |
|--------|------|-------------|
| role_category | Text | Role |
| skill_name | Text | Skill |
| skill_category | Text | Skill category |
| country_code | Text | Country |
| job_count | Integer | Jobs with this skill in this role |
| penetration_pct | Numeric | % of role's jobs |

## 07_london_analysis.csv — London Breakdown

| Column | Type | Description |
|--------|------|-------------|
| location_group | Text | "London", "Greater London", or "UK Other" |
| total_jobs | Integer | Jobs in this group |
| data_analyst_jobs | Integer | Data analyst jobs |
| data_scientist_jobs | Integer | Data scientist jobs |
| analytics_engineer_jobs | Integer | Analytics engineer jobs |
| jobs_with_salary | Integer | Jobs with salary |
| avg_salary_midpoint | Numeric | Average salary |
| remote_jobs | Integer | Remote jobs |
| hybrid_jobs | Integer | Hybrid jobs |
| on_site_jobs | Integer | On-site jobs |
| junior_count | Integer | Junior jobs |
| senior_count | Integer | Senior jobs |

## 09_skill_salary.csv — Skill-Salary Association

| Column | Type | Description |
|--------|------|-------------|
| skill_name | Text | Skill |
| skill_category | Text | Category |
| country_code | Text | Country |
| job_count | Integer | Jobs with this skill AND salary data |
| avg_salary_midpoint | Numeric | Average salary |
| median_salary | Numeric | Median salary |
| q25_salary | Numeric | 25th percentile |
| q75_salary | Numeric | 75th percentile |

## 10_seniority_analysis.csv — Seniority Distribution

| Column | Type | Description |
|--------|------|-------------|
| seniority | Text | junior/mid/senior/unknown |
| country_code | Text | Country |
| dataset_period | Text | Period |
| total_jobs | Integer | Jobs at this seniority |
| data_analyst | Integer | Data analyst count |
| data_scientist | Integer | Data scientist count |
| analytics_engineer | Integer | Analytics engineer count |
| jobs_with_salary | Integer | Jobs with salary |
| avg_salary_midpoint | Numeric | Average salary |
| remote_count | Integer | Remote jobs |
| hybrid_count | Integer | Hybrid jobs |
| on_site_count | Integer | On-site jobs |

## 11_employer_analysis.csv — Top Employers

| Column | Type | Description |
|--------|------|-------------|
| company_name | Text | Company |
| country_code | Text | Country |
| source_name | Text | Source |
| job_count | Integer | Jobs posted |
| pct_of_country | Numeric | % of country's jobs |
| distinct_roles | Integer | Different role types |
| jobs_with_salary | Integer | Jobs with salary |

## 12_temporal_analysis.csv — Monthly Trends

| Column | Type | Description |
|--------|------|-------------|
| month | Date | Month (first day) |
| country_code | Text | Country |
| source_name | Text | Source |
| job_count | Integer | Jobs posted that month |
| data_analyst_count | Integer | Data analyst jobs |
| data_scientist_count | Integer | Data scientist jobs |
| jobs_with_salary | Integer | Jobs with salary |
| avg_salary_midpoint | Numeric | Average salary |
