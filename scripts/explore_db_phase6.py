"""Exploratory QA queries against PostgreSQL for Phase 6 Power BI validation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analytics.engine import get_engine, sql_query  # noqa: E402


def main() -> None:
    e = get_engine()
    checks = {
        "total_jobs": "SELECT COUNT(*) AS n FROM jobs",
        "jobs_any_salary_bound": (
            "SELECT COUNT(*) AS n FROM jobs WHERE salary_min IS NOT NULL OR salary_max IS NOT NULL"
        ),
        "jobs_both_bounds": (
            "SELECT COUNT(*) AS n FROM jobs WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL"
        ),
        "salary_data_table_rows": "SELECT COUNT(*) AS n FROM salary_data",
        "uk_jobs": "SELECT COUNT(*) AS n FROM jobs j JOIN job_sources s ON j.source_id=s.source_id WHERE s.name='adzuna_uk'",
        "pk_chisel": "SELECT COUNT(*) AS n FROM jobs j JOIN job_sources s ON j.source_id=s.source_id WHERE s.name='chisel_pk'",
        "pk_rozee": "SELECT COUNT(*) AS n FROM jobs j JOIN job_sources s ON j.source_id=s.source_id WHERE s.name='kaggle_rozee_pk'",
        "unique_companies": "SELECT COUNT(DISTINCT company_id) AS n FROM jobs WHERE company_id IS NOT NULL",
        "skills_normalized": "SELECT COUNT(*) AS n FROM skills",
        "job_skill_links": "SELECT COUNT(*) AS n FROM job_skills",
        "distinct_skills_used": "SELECT COUNT(DISTINCT skill_id) AS n FROM job_skills",
    }
    print("== BASE COUNTS ==")
    for name, q in checks.items():
        print(f"{name}: {sql_query(e, q).iloc[0]['n']}")

    print("\n== SALARY REALITY CHECK ==")
    print(sql_query(e, """
        SELECT source_name,
               COUNT(*) AS jobs,
               COUNT(*) FILTER (WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL) AS both_bounds,
               COUNT(*) FILTER (WHERE salary_midpoint IS NOT NULL) AS mid_not_null,
               ROUND(AVG(salary_midpoint)::numeric,0) AS avg_mid,
               ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_midpoint))::numeric,0) AS med_mid
        FROM v_analytical_jobs
        GROUP BY source_name ORDER BY source_name
    """).to_string(index=False))

    print("\n== SALARY BY CURRENCY/PERIOD (midpoint non-null) ==")
    print(sql_query(e, """
        SELECT salary_currency, salary_period, COUNT(*) AS n
        FROM v_analytical_jobs WHERE salary_midpoint IS NOT NULL
        GROUP BY 1,2 ORDER BY n DESC
    """).to_string(index=False))

    print("\n== LONDON GROUPS (GB) ==")
    print(sql_query(e, """
        SELECT location_group, COUNT(*) AS jobs,
               COUNT(*) FILTER (WHERE role_category='data_analyst') AS da,
               COUNT(*) FILTER (WHERE role_category='data_scientist') AS ds,
               COUNT(*) FILTER (WHERE role_category='analytics_engineer') AS ae
        FROM v_analytical_jobs WHERE country_code='GB'
        GROUP BY location_group ORDER BY jobs DESC
    """).to_string(index=False))

    print("\n== ROLE x COUNTRY ==")
    print(sql_query(e, """
        SELECT role_category, country_code, COUNT(*) AS jobs
        FROM v_analytical_jobs GROUP BY 1,2 ORDER BY country_code, jobs DESC
    """).to_string(index=False))

    print("\n== SENIORITY x COUNTRY ==")
    print(sql_query(e, """
        SELECT seniority, country_code, COUNT(*) AS jobs
        FROM v_analytical_jobs GROUP BY 1,2 ORDER BY country_code, jobs DESC
    """).to_string(index=False))

    print("\n== WORK MODE (GB) ==")
    print(sql_query(e, """
        SELECT work_mode, COUNT(*) AS jobs FROM v_analytical_jobs
        WHERE country_code='GB' GROUP BY 1 ORDER BY jobs DESC
    """).to_string(index=False))

    print("\n== EMPLOYMENT / CONTRACT TYPE (GB) ==")
    print(sql_query(e, """
        SELECT employment_type, COUNT(*) AS jobs FROM v_analytical_jobs
        WHERE country_code='GB' GROUP BY 1 ORDER BY jobs DESC
    """).to_string(index=False))

    print("\n== TEMPORAL RANGE ==")
    print(sql_query(e, """
        SELECT source_name, MIN(posting_date) AS min_d, MAX(posting_date) AS max_d,
               COUNT(posting_date) AS dated_jobs
        FROM v_analytical_jobs GROUP BY source_name ORDER BY source_name
    """).to_string(index=False))

    print("\n== TOP 10 SKILLS GB ==")
    print(sql_query(e, """
        SELECT skill_name, skill_category, job_count, penetration_pct
        FROM v_skill_demand WHERE country_code='GB'
        ORDER BY job_count DESC LIMIT 10
    """).to_string(index=False))

    print("\n== TOP 10 SKILLS PK ==")
    print(sql_query(e, """
        SELECT skill_name, skill_category, job_count, penetration_pct
        FROM v_skill_demand WHERE country_code='PK'
        ORDER BY job_count DESC LIMIT 10
    """).to_string(index=False))


if __name__ == "__main__":
    main()
