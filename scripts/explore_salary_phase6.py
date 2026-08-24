"""Precise salary truth-check (NaN vs NULL) for Phase 6 dashboard honesty."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analytics.engine import get_engine, sql_query  # noqa: E402


def main() -> None:
    e = get_engine()
    print("== REAL salary_midpoint (excl NaN) by source ==")
    print(sql_query(e, """
        SELECT source_name,
               COUNT(*) AS jobs,
               COUNT(*) FILTER (WHERE salary_midpoint IS NOT NULL AND NOT salary_midpoint::text = 'NaN') AS real_mid,
               ROUND(AVG(salary_midpoint) FILTER (WHERE NOT salary_midpoint::text = 'NaN')::numeric, 0) AS avg_mid,
               ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_midpoint)
                      FILTER (WHERE NOT salary_midpoint::text = 'NaN'))::numeric, 0) AS med_mid
        FROM v_analytical_jobs GROUP BY source_name ORDER BY source_name
    """).to_string(index=False))

    print("\n== GB salary midpoint distribution sanity ==")
    print(sql_query(e, """
        SELECT COUNT(*) AS n,
               ROUND(MIN(salary_midpoint)::numeric,0) AS mn,
               ROUND((PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY salary_midpoint))::numeric,0) AS q25,
               ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_midpoint))::numeric,0) AS med,
               ROUND((PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY salary_midpoint))::numeric,0) AS q75,
               ROUND(MAX(salary_midpoint)::numeric,0) AS mx
        FROM v_analytical_jobs
        WHERE country_code='GB' AND salary_midpoint IS NOT NULL AND NOT salary_midpoint::text='NaN'
    """).to_string(index=False))

    print("\n== salary_data table structure ==")
    print(sql_query(e, """
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name='salary_data' ORDER BY ordinal_position
    """).to_string(index=False))
    print(sql_query(e, "SELECT COUNT(*) AS n FROM salary_data").iloc[0])

    print("\n== salary_data joinable to jobs? ==")
    print(sql_query(e, """
        SELECT s.name AS source_name,
               COUNT(*) AS obs,
               COUNT(DISTINCT sd.job_id) AS distinct_jobs
        FROM salary_data sd JOIN jobs j ON sd.job_id=j.job_id
        JOIN job_sources s ON j.source_id=s.source_id
        GROUP BY 1 ORDER BY obs DESC
    """).to_string(index=False))

    print("\n== v_salary_analysis row count & NaN share ==")
    print(sql_query(e, """
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE salary_midpoint::text='NaN' OR salary_midpoint IS NULL) AS unusable,
               COUNT(*) FILTER (WHERE salary_midpoint IS NOT NULL AND NOT salary_midpoint::text='NaN') AS usable
        FROM v_salary_analysis
    """).to_string(index=False))

    print("\n== GB usable salary by seniority ==")
    print(sql_query(e, """
        SELECT seniority, COUNT(*) AS n,
               ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_midpoint))::numeric,0) AS med
        FROM v_analytical_jobs
        WHERE country_code='GB' AND salary_midpoint IS NOT NULL AND NOT salary_midpoint::text='NaN'
        GROUP BY seniority ORDER BY n DESC
    """).to_string(index=False))

    print("\n== skill_salary view usable rows (GB only?) ==")
    print(sql_query(e, """
        SELECT country_code, COUNT(*) AS skills,
               COUNT(*) FILTER (WHERE median_salary::text='NaN') AS nan_medians
        FROM v_skill_salary GROUP BY 1
    """).to_string(index=False))


if __name__ == "__main__":
    main()
