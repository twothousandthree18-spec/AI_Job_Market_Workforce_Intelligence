"""
Phase 5 Analytics Engine — Workforce Market Intelligence.

Computes analytical metrics from the PostgreSQL database and processed parquet.
Generates Power BI-ready outputs and validates SQL/Python agreement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
ANALYTICS_DIR = DATA_DIR / "analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = "postgresql://jobmarket:changeme@localhost:5432/job_market_analytics"


def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def sql_query(engine, query: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def load_parquet() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "processed.parquet")


def extract_skills_from_parquet(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Extract skill counts per country from parquet skills_list column."""
    uk_skills: dict[str, int] = {}
    pk_skills: dict[str, int] = {}
    uk_jobs = set()
    pk_jobs = set()

    for _, row in df.iterrows():
        src = row.get("source", "")
        skills = row.get("skills_list", [])
        if isinstance(skills, np.ndarray):
            skills = skills.tolist()
        if not isinstance(skills, list) or len(skills) == 0:
            continue

        job_key = (src, row.get("source_job_id", ""))
        if src == "adzuna_uk":
            uk_jobs.add(job_key)
            for s in skills:
                if isinstance(s, dict):
                    name = s.get("normalized_skill", "")
                    if name:
                        uk_skills[name] = uk_skills.get(name, 0) + 1
        elif src in ("chisel_pk", "kaggle_rozee_pk"):
            pk_jobs.add(job_key)
            for s in skills:
                if isinstance(s, dict):
                    name = s.get("normalized_skill", "")
                    if name:
                        pk_skills[name] = pk_skills.get(name, 0) + 1

    return {
        "uk_skills": uk_skills,
        "pk_skills": pk_skills,
        "uk_job_count": len(uk_jobs),
        "pk_job_count": len(pk_jobs),
    }


def step02_profile(df: pd.DataFrame) -> dict[str, Any]:
    """STEP 2: Dataset profiling."""
    profile = {
        "total_rows": len(df),
        "unique_jobs": df.groupby(["source", "source_job_id"]).ngroups,
        "by_source": df["source"].value_counts().to_dict(),
        "by_country": df["country"].value_counts().to_dict(),
        "salary_coverage": {
            "has_salary": int(df["salary_min"].notna().sum() + df["salary_max"].notna().sum()),
            "pct": round(100 * (df["salary_min"].notna() | df["salary_max"].notna()).mean(), 1),
        },
        "work_mode": df["work_mode"].value_counts().dropna().to_dict(),
        "employment_type": df["employment_type"].value_counts().dropna().to_dict(),
        "seniority": df["seniority"].value_counts().dropna().to_dict(),
        "role_category": df["role_category"].value_counts().to_dict(),
        "skills_extracted": 0,
        "unique_skills": 0,
    }

    # Count skills
    total_skills = 0
    unique_skills = set()
    for skills in df["skills_list"]:
        if isinstance(skills, np.ndarray):
            skills = skills.tolist()
        if isinstance(skills, list):
            for s in skills:
                if isinstance(s, dict):
                    name = s.get("normalized_skill", "")
                    if name:
                        total_skills += 1
                        unique_skills.add(name)
    profile["skills_extracted"] = total_skills
    profile["unique_skills"] = len(unique_skills)

    return profile


def step03_market_demand(engine) -> pd.DataFrame:
    """STEP 3: Market demand analysis from SQL."""
    return sql_query(engine, "SELECT * FROM v_market_overview ORDER BY total_jobs DESC")


def step04_skill_demand(engine) -> pd.DataFrame:
    """STEP 4: Skill demand with job-level penetration."""
    return sql_query(engine, """
        SELECT skill_name, skill_category, country_code, dataset_period,
               job_count, penetration_pct
        FROM v_skill_demand
        ORDER BY country_code, job_count DESC
    """)


def step05_skill_comparison(engine) -> pd.DataFrame:
    """STEP 5: UK vs PK skill comparison."""
    return sql_query(engine, """
        SELECT skill_name, skill_category,
               uk_job_count, uk_penetration_pct,
               pk_job_count, pk_penetration_pct,
               penetration_diff, emphasis
        FROM v_skill_comparison
        WHERE uk_job_count + pk_job_count >= 5
        ORDER BY uk_job_count + pk_job_count DESC
    """)


def step06_cocurrence(engine) -> pd.DataFrame:
    """STEP 6: Skill co-occurrence."""
    return sql_query(engine, """
        SELECT skill_a, skill_b, country_code,
               co_occurrence_count, co_occurrence_pct
        FROM v_skill_cocurrence
        ORDER BY co_occurrence_count DESC
        LIMIT 100
    """)


def step07_role_skills(engine) -> pd.DataFrame:
    """STEP 7: Role-specific skill analysis."""
    return sql_query(engine, "SELECT * FROM v_role_skills")


def step08_london(engine) -> pd.DataFrame:
    """STEP 8: London analysis."""
    return sql_query(engine, "SELECT * FROM v_london_analysis")


def step09_salary(engine) -> pd.DataFrame:
    """STEP 9: Salary analysis."""
    return sql_query(engine, """
        SELECT role_category, seniority, country_code,
               COUNT(*) AS job_count,
                ROUND(AVG(salary_midpoint)::numeric, 0) AS avg_salary,
                ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
                    ORDER BY salary_midpoint))::numeric, 0) AS median_salary,
                ROUND((PERCENTILE_CONT(0.25) WITHIN GROUP (
                    ORDER BY salary_midpoint))::numeric, 0) AS q25,
                ROUND((PERCENTILE_CONT(0.75) WITHIN GROUP (
                    ORDER BY salary_midpoint))::numeric, 0) AS q75,
               ROUND(MIN(salary_midpoint)::numeric, 0) AS min_salary,
               ROUND(MAX(salary_midpoint)::numeric, 0) AS max_salary
        FROM v_salary_analysis
        GROUP BY role_category, seniority, country_code
        HAVING COUNT(*) >= 3
        ORDER BY country_code, job_count DESC
    """)


def step10_skill_salary(engine) -> pd.DataFrame:
    """STEP 10: Skill-salary association."""
    return sql_query(engine, "SELECT * FROM v_skill_salary ORDER BY job_count DESC")


def step11_seniority(engine) -> pd.DataFrame:
    """STEP 11: Seniority analysis."""
    return sql_query(engine, "SELECT * FROM v_seniority_analysis")


def step12_employer(engine) -> pd.DataFrame:
    """STEP 12: Employer concentration."""
    return sql_query(engine, """
        SELECT company_name, country_code, job_count, pct_of_country,
               distinct_roles, jobs_with_salary
        FROM v_employer_analysis
        ORDER BY job_count DESC
        LIMIT 50
    """)


def step13_temporal(engine) -> pd.DataFrame:
    """STEP 13: Temporal analysis."""
    return sql_query(engine, "SELECT * FROM v_temporal_analysis ORDER BY month")


def step14_career_intelligence(engine) -> dict[str, Any]:
    """STEP 14: Career intelligence framework."""
    # Data Analyst profile
    da_uk = sql_query(engine, """
        SELECT skill_name, job_count, penetration_pct
        FROM v_role_skills
        WHERE role_category = 'data_analyst' AND country_code = 'GB'
        ORDER BY job_count DESC LIMIT 15
    """)
    da_pk = sql_query(engine, """
        SELECT skill_name, job_count, penetration_pct
        FROM v_role_skills
        WHERE role_category = 'data_analyst' AND country_code = 'PK'
        ORDER BY job_count DESC LIMIT 15
    """)

    # Data Scientist profile
    ds_uk = sql_query(engine, """
        SELECT skill_name, job_count, penetration_pct
        FROM v_role_skills
        WHERE role_category = 'data_scientist' AND country_code = 'GB'
        ORDER BY job_count DESC LIMIT 15
    """)

    # Analytics Engineer profile
    ae_uk = sql_query(engine, """
        SELECT skill_name, job_count, penetration_pct
        FROM v_role_skills
        WHERE role_category = 'analytics_engineer' AND country_code = 'GB'
        ORDER BY job_count DESC LIMIT 15
    """)

    return {
        "data_analyst_uk": da_uk.to_dict("records"),
        "data_analyst_pk": da_pk.to_dict("records"),
        "data_scientist_uk": ds_uk.to_dict("records"),
        "analytics_engineer_uk": ae_uk.to_dict("records"),
    }


def step17_statistical_validation(df: pd.DataFrame) -> dict[str, Any]:
    """STEP 17: Statistical validation tests."""
    results = {}

    # Test 1: Is skill penetration different between UK and PK?
    # Use chi-square test on top skills
    engine = get_engine()
    comparison = step05_skill_comparison(engine)

    if len(comparison) > 0:
        # Chi-square test for top 10 skills
        top_skills = comparison.head(10)
        contingency = top_skills[["uk_job_count", "pk_job_count"]].values
        if contingency.sum() > 0 and contingency.shape == (10, 2):
            chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
            results["skill_comparison_chi2"] = {
                "test": "Chi-square test for UK vs PK skill distribution",
                "null_hypothesis": "Skill distribution is independent of country",
                "chi2_statistic": round(chi2, 2),
                "p_value": round(p_value, 6),
                "dof": dof,
                "interpretation": (
                    "Statistically significant difference in skill distribution"
                    if p_value < 0.05
                    else "No significant difference in skill distribution"
                ),
            }

    # Test 2: Salary comparison (UK data only since PK has no salary)
    uk_salary = df[(df["country"] == "GB") & (df["salary_min"].notna())]
    if len(uk_salary) > 10:
        senior_sal = uk_salary[uk_salary["seniority"] == "senior"]["salary_min"].dropna()
        junior_sal = uk_salary[uk_salary["seniority"] == "junior"]["salary_min"].dropna()
        if len(senior_sal) >= 5 and len(junior_sal) >= 5:
            u_stat, p_val = stats.mannwhitneyu(senior_sal, junior_sal, alternative="greater")
            results["salary_seniority_test"] = {
                "test": "Mann-Whitney U: Senior vs Junior salary (UK)",
                "null_hypothesis": "Senior salaries are not higher than junior salaries",
                "u_statistic": round(u_stat, 2),
                "p_value": round(p_val, 6),
                "senior_n": len(senior_sal),
                "junior_n": len(junior_sal),
                "senior_median": round(senior_sal.median(), 0),
                "junior_median": round(junior_sal.median(), 0),
                "interpretation": (
                    "Senior salaries are significantly higher"
                    if p_val < 0.05
                    else "No significant salary difference by seniority"
                ),
            }

    return results


def step20_sql_python_validation(engine) -> dict[str, Any]:
    """STEP 20: SQL vs Python metric agreement."""
    validation = {}

    # Total jobs
    sql_total = sql_query(engine, "SELECT COUNT(*) AS cnt FROM jobs").iloc[0]["cnt"]
    py_df = load_parquet()
    py_total = py_df.groupby(["source", "source_job_id"]).ngroups
    validation["total_jobs"] = {
        "sql": int(sql_total), "python": int(py_total),
        "match": sql_total == py_total,
    }

    # UK jobs
    sql_uk = sql_query(engine, "SELECT COUNT(*) AS cnt FROM jobs WHERE country='GB'").iloc[0]["cnt"]
    py_uk = len(py_df[py_df["country"] == "GB"].drop_duplicates(subset=["source", "source_job_id"]))
    validation["uk_jobs"] = {"sql": int(sql_uk), "python": int(py_uk), "match": sql_uk == py_uk}

    # PK jobs
    sql_pk = sql_query(engine, "SELECT COUNT(*) AS cnt FROM jobs WHERE country='PK'").iloc[0]["cnt"]
    py_pk = len(py_df[py_df["country"] == "PK"].drop_duplicates(subset=["source", "source_job_id"]))
    validation["pk_jobs"] = {"sql": int(sql_pk), "python": int(py_pk), "match": sql_pk == py_pk}

    # Skills: SQL counts unique skill_ids in job_skills, Python counts total mentions
    sql_skill_links = sql_query(engine, "SELECT COUNT(*) AS cnt FROM job_skills").iloc[0]["cnt"]
    py_skill_mentions = 0
    for skills in py_df["skills_list"]:
        if isinstance(skills, np.ndarray):
            skills = skills.tolist()
        if isinstance(skills, list):
            py_skill_mentions += len([s for s in skills if isinstance(s, dict)])
    validation["skill_mentions"] = {
        "sql": int(sql_skill_links),
        "python": py_skill_mentions,
        "match": False,  # Different metrics by design
        "note": "SQL=job_skill links, Python=total skill mentions across all rows",
    }

    # Salary records
    sql_sal = sql_query(engine, "SELECT COUNT(*) AS cnt FROM salary_data").iloc[0]["cnt"]
    py_sal = int((py_df["salary_min"].notna() | py_df["salary_max"].notna()).sum())
    validation["salary_records"] = {
        "sql": int(sql_sal), "python": int(py_sal),
        "match": abs(sql_sal - py_sal) <= 50,
    }

    return validation


def step21_powerbi_outputs(engine) -> list[Path]:
    """STEP 21: Generate Power BI-ready CSV outputs."""
    outputs = []

    views = {
        "01_market_overview": "SELECT * FROM v_market_overview",
        "02_role_demand": "SELECT * FROM v_role_demand",
        "03_skill_demand": "SELECT * FROM v_skill_demand",
        "04_skill_comparison": "SELECT * FROM v_skill_comparison",
        "05_skill_cocurrence": "SELECT * FROM v_skill_cocurrence LIMIT 200",
        "06_role_skills": "SELECT * FROM v_role_skills",
        "07_london_analysis": "SELECT * FROM v_london_analysis",
        "08_salary_analysis": "SELECT * FROM v_salary_analysis",
        "09_skill_salary": "SELECT * FROM v_skill_salary",
        "10_seniority_analysis": "SELECT * FROM v_seniority_analysis",
        "11_employer_analysis": "SELECT * FROM v_employer_analysis LIMIT 100",
        "12_temporal_analysis": "SELECT * FROM v_temporal_analysis",
        "13_analytical_jobs": "SELECT * FROM v_analytical_jobs",
    }

    for name, query in views.items():
        df = sql_query(engine, query)
        path = ANALYTICS_DIR / f"{name}.csv"
        df.to_csv(path, index=False)
        outputs.append(path)

    return outputs


def run_all() -> dict[str, Any]:
    """Run the complete Phase 5 analytics pipeline."""
    engine = get_engine()
    df = load_parquet()
    results = {}

    print("=" * 70)
    print("PHASE 5: WORKFORCE MARKET ANALYTICS")
    print("=" * 70)

    # STEP 2: Profile
    print("\n[STEP 2] Dataset profiling...")
    results["profile"] = step02_profile(df)
    print(f"  Total rows: {results['profile']['total_rows']}")
    print(f"  Unique jobs: {results['profile']['unique_jobs']}")
    print(f"  Skills extracted: {results['profile']['skills_extracted']}")
    print(f"  Unique skills: {results['profile']['unique_skills']}")

    # STEP 3: Market demand
    print("\n[STEP 3] Market demand...")
    results["market_overview"] = step03_market_demand(engine)
    print(results["market_overview"].to_string(index=False))

    # STEP 4: Skill demand
    print("\n[STEP 4] Skill demand...")
    results["skill_demand"] = step04_skill_demand(engine)
    print(f"  {len(results['skill_demand'])} skill-country records")

    # STEP 5: Skill comparison
    print("\n[STEP 5] UK vs PK skill comparison...")
    results["skill_comparison"] = step05_skill_comparison(engine)
    print(results["skill_comparison"].head(15).to_string(index=False))

    # STEP 6: Co-occurrence
    print("\n[STEP 6] Skill co-occurrence...")
    results["cocurrence"] = step06_cocurrence(engine)
    print(f"  {len(results['cocurrence'])} co-occurring skill pairs")

    # STEP 7: Role skills
    print("\n[STEP 7] Role-specific skills...")
    results["role_skills"] = step07_role_skills(engine)
    print(f"  {len(results['role_skills'])} role-skill records")

    # STEP 8: London
    print("\n[STEP 8] London analysis...")
    results["london"] = step08_london(engine)
    print(results["london"].to_string(index=False))

    # STEP 9: Salary
    print("\n[STEP 9] Salary analysis...")
    results["salary"] = step09_salary(engine)
    print(f"  {len(results['salary'])} salary records by role/seniority/country")

    # STEP 10: Skill-salary
    print("\n[STEP 10] Skill-salary association...")
    results["skill_salary"] = step10_skill_salary(engine)
    print(f"  {len(results['skill_salary'])} skills with salary data")

    # STEP 11: Seniority
    print("\n[STEP 11] Seniority analysis...")
    results["seniority"] = step11_seniority(engine)
    print(results["seniority"].to_string(index=False))

    # STEP 12: Employers
    print("\n[STEP 12] Employer concentration...")
    results["employers"] = step12_employer(engine)
    print(results["employers"].head(10).to_string(index=False))

    # STEP 13: Temporal
    print("\n[STEP 13] Temporal analysis...")
    results["temporal"] = step13_temporal(engine)
    print(f"  {len(results['temporal'])} monthly records")

    # STEP 14: Career intelligence
    print("\n[STEP 14] Career intelligence...")
    results["career_intel"] = step14_career_intelligence(engine)
    print(f"  Data Analyst UK skills: {len(results['career_intel']['data_analyst_uk'])}")
    print(f"  Data Scientist UK skills: {len(results['career_intel']['data_scientist_uk'])}")

    # STEP 17: Statistical validation
    print("\n[STEP 17] Statistical validation...")
    results["statistics"] = step17_statistical_validation(df)
    for test_name, test_result in results["statistics"].items():
        print(f"  {test_name}: p={test_result['p_value']} — {test_result['interpretation']}")

    # STEP 20: SQL/Python validation
    print("\n[STEP 20] SQL-Python validation...")
    results["validation"] = step20_sql_python_validation(engine)
    for metric, vals in results["validation"].items():
        status = "MATCH" if vals["match"] else "MISMATCH"
        print(f"  {metric}: SQL={vals['sql']}, Python={vals['python']} [{status}]")

    # STEP 21: Power BI outputs
    print("\n[STEP 21] Generating Power BI-ready outputs...")
    outputs = step21_powerbi_outputs(engine)
    for path in outputs:
        print(f"  {path.name}")

    # Save comprehensive results
    results_path = ANALYTICS_DIR / "phase5_results.json"
    serializable = {}
    for k, v in results.items():
        if isinstance(v, pd.DataFrame):
            serializable[k] = v.to_dict("records")
        elif isinstance(v, dict):
            serializable[k] = v
        else:
            serializable[k] = str(v)

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nResults saved to {results_path}")

    print("\n" + "=" * 70)
    print("PHASE 5 COMPLETE")
    print("=" * 70)

    return results


if __name__ == "__main__":
    run_all()
