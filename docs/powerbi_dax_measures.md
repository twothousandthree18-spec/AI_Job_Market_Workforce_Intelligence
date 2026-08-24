# Power BI DAX Measures

All measures assume `fact_jobs` as the primary table unless noted.

## Core Job Measures

```dax
Total Jobs = COUNTROWS(fact_jobs)

UK Jobs =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[country_code] = "GB")

Pakistan Jobs =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[country_code] = "PK")

London Jobs =
CALCULATE(
    COUNTROWS(fact_jobs),
    fact_jobs[country_code] = "GB",
    fact_jobs[location_group] = "London"
)

Greater London Jobs =
CALCULATE(
    COUNTROWS(fact_jobs),
    fact_jobs[country_code] = "GB",
    fact_jobs[location_group] = "Greater London"
)

UK Other Jobs =
CALCULATE(
    COUNTROWS(fact_jobs),
    fact_jobs[country_code] = "GB",
    fact_jobs[location_group] = "UK Other"
)
```

## Dimension Counts

```dax
Unique Companies =
DISTINCTCOUNT(fact_jobs[company_name])

Unique Locations =
DISTINCTCOUNT(fact_jobs[city])

UK Companies =
CALCULATE(DISTINCTCOUNT(fact_jobs[company_name]), fact_jobs[country_code] = "GB")

PK Companies =
CALCULATE(DISTINCTCOUNT(fact_jobs[company_name]), fact_jobs[country_code] = "PK")
```

## Role Measures

```dax
Data Analyst Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[role_category] = "data_analyst")

Data Scientist Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[role_category] = "data_scientist")

Analytics Engineer Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[role_category] = "analytics_engineer")

Data Architect Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[role_category] = "data_architect")

Financial Analyst Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[role_category] = "financial_analyst")

Other Roles Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[role_category] = "other")
```

## Seniority Measures

```dax
Senior Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[seniority] = "senior")

Mid Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[seniority] = "mid")

Junior Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[seniority] = "junior")

Unknown Seniority Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[seniority] = "unknown")
```

## Salary Measures

```dax
Jobs with Salary =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[has_salary] = TRUE())

Salary Coverage % =
DIVIDE([Jobs with Salary], [Total Jobs], 0) * 100

Average Salary =
AVERAGE(fact_jobs[salary_midpoint])

Median Salary =
MEDIAN(fact_jobs[salary_midpoint])

Minimum Salary =
MIN(fact_jobs[salary_midpoint])

Maximum Salary =
MAX(fact_jobs[salary_midpoint])

UK Median Salary =
CALCULATE(MEDIAN(fact_jobs[salary_midpoint]), fact_jobs[country_code] = "GB")

UK Average Salary =
CALCULATE(AVERAGE(fact_jobs[salary_midpoint]), fact_jobs[country_code] = "GB")

London Median Salary =
CALCULATE(
    MEDIAN(fact_jobs[salary_midpoint]),
    fact_jobs[country_code] = "GB",
    fact_jobs[location_group] = "London"
)

Senior Median Salary =
CALCULATE(MEDIAN(fact_jobs[salary_midpoint]), fact_jobs[seniority] = "senior")

Junior Median Salary =
CALCULATE(MEDIAN(fact_jobs[salary_midpoint]), fact_jobs[seniority] = "junior")
```

## Work Mode Measures

```dax
Remote Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[work_mode] = "remote")

Hybrid Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[work_mode] = "hybrid")

On-Site Count =
CALCULATE(COUNTROWS(fact_jobs), fact_jobs[work_mode] = "on_site")

Remote % =
DIVIDE([Remote Count], [Total Jobs], 0) * 100

Hybrid % =
DIVIDE([Hybrid Count], [Total Jobs], 0) * 100

On-Site % =
DIVIDE([On-Site Count], [Total Jobs], 0) * 100
```

## Percentage Measures

```dax
UK % of Total =
DIVIDE([UK Jobs], [Total Jobs], 0) * 100

PK % of Total =
DIVIDE([Pakistan Jobs], [Total Jobs], 0) * 100

London % of UK =
DIVIDE([London Jobs], [UK Jobs], 0) * 100

Data Analyst % of UK =
DIVCULATE(
    CALCULATE(COUNTROWS(fact_jobs), fact_jobs[role_category] = "data_analyst"),
    [UK Jobs], 0
) * 100

Senior % of Total =
DIVIDE([Senior Count], [Total Jobs], 0) * 100
```

## Skill Measures (from agg_skill_demand)

```dax
Skill Job Count = SUM(agg_skill_demand[job_count])

Skill Penetration % = MAX(agg_skill_demand[penetration_pct])

UK Skill Penetration =
CALCULATE(
    MAX(agg_skill_demand[penetration_pct]),
    agg_skill_demand[country_code] = "GB"
)

PK Skill Penetration =
CALCULATE(
    MAX(agg_skill_demand[penetration_pct]),
    agg_skill_demand[country_code] = "PK"
)
```

## Formatting Notes

| Measure | Format |
|---------|--------|
| All counts | #,##0 |
| All percentages | #,##0.0% |
| All salary measures | £#,##0 |
| Penetration % | #,##0.0 |
