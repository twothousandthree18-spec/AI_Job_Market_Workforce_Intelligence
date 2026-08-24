"""Phase 6 QA — validate Power BI-ready assets against PostgreSQL.

Checks every data/analytics CSV against live SQL views and produces the KPI
reference file consumed by unit tests and documentation:

    dashboard/powerbi/kpi_validation.json

Run:  python scripts/powerbi_qa.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from analytics.engine import get_engine, sql_query  # noqa: E402

ANALYTICS_DIR = PROJECT_ROOT / "data" / "analytics"
OUTPUT_PATH = PROJECT_ROOT / "dashboard" / "powerbi" / "kpi_validation.json"

EXPECTED_FILES = {f"{i:02d}_" for i in range(1, 15)}

# PostgreSQL float8 NaN survives a text cast as 'NaN'; real observations only.
USABLE_MIDPOINT = (
    "salary_midpoint IS NOT NULL "
    "AND NOT salary_midpoint::text = 'NaN'"
)


def _coerce(value):
    """Convert numpy scalars / sets to JSON-serialisable natives."""
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, set):
        return sorted(value)
    return value


def check(name: str, expected, actual, ok: bool) -> dict:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}: expected={expected} actual={actual}")
    return {
        "check": name,
        "expected": _coerce(expected),
        "actual": _coerce(actual),
        "pass": bool(ok),
    }


def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(ANALYTICS_DIR / name)


def main() -> int:
    engine = get_engine()
    results: list[dict] = []
    kpis: dict = {}

    print("== 1. File inventory ==")
    present = sorted(p.name[:3] for p in ANALYTICS_DIR.glob("*.csv"))
    missing = EXPECTED_FILES - set(present)
    results.append(
        check("csv files 01-14 present", sorted(EXPECTED_FILES), present, not missing)
    )

    print("== 2. Row counts vs database ==")
    db_jobs = sql_query(engine, "SELECT COUNT(*) AS n FROM jobs").iloc[0]["n"]
    jobs_df = csv("13_analytical_jobs.csv")
    results.append(check("Jobs rows", db_jobs, len(jobs_df), len(jobs_df) == db_jobs))
    kpis["total_jobs"] = int(db_jobs)

    bridge_db = sql_query(
        engine, "SELECT COUNT(*) AS n FROM job_skills"
    ).iloc[0]["n"]
    bridge = csv("14_job_skills_bridge.csv")
    results.append(
        check(
            "JobSkills bridge rows",
            bridge_db,
            len(bridge),
            len(bridge) == bridge_db,
        )
    )
    kpis["job_skill_links"] = int(bridge_db)

    sal_ref = sql_query(
        engine,
        f"SELECT COUNT(*) AS n FROM v_analytical_jobs WHERE {USABLE_MIDPOINT}",
    ).iloc[0]["n"]
    kpis["salary_observations"] = int(sal_ref)

    print("== 3. Country composition ==")
    by_country = jobs_df["country_code"].value_counts().to_dict()
    db_gb = sql_query(
        engine,
        "SELECT COUNT(*) AS n FROM jobs j JOIN job_sources s "
        "ON j.source_id = s.source_id WHERE s.name = 'adzuna_uk'",
    ).iloc[0]["n"]
    db_pk_hist = sql_query(
        engine,
        "SELECT COUNT(*) AS n FROM jobs j JOIN job_sources s "
        "ON j.source_id = s.source_id WHERE s.name = 'chisel_pk'",
    ).iloc[0]["n"]
    db_pk_supp = sql_query(
        engine,
        "SELECT COUNT(*) AS n FROM jobs j JOIN job_sources s "
        "ON j.source_id = s.source_id WHERE s.name = 'kaggle_rozee_pk'",
    ).iloc[0]["n"]
    results.extend([
        check("UK jobs", db_gb, by_country.get("GB"), by_country.get("GB") == db_gb),
        check(
            "Pakistan total",
            db_pk_hist + db_pk_supp,
            by_country.get("PK"),
            by_country.get("PK") == db_pk_hist + db_pk_supp,
        ),
        check(
            "dataset_period labels on UK rows",
            {"Recent UK (2023-2026)"},
            set(jobs_df.loc[jobs_df.country_code == "GB", "dataset_period"].unique()),
            set(jobs_df.loc[jobs_df.country_code == "GB", "dataset_period"].unique())
            == {"Recent UK (2023-2026)"},
        ),
        check(
            "dataset_period labels on historical PK rows",
            {"Historical PK (2019-2021)"},
            set(
                jobs_df.loc[
                    jobs_df.source_name == "chisel_pk", "dataset_period"
                ].unique()
            ),
            set(
                jobs_df.loc[
                    jobs_df.source_name == "chisel_pk", "dataset_period"
                ].unique()
            )
            == {"Historical PK (2019-2021)"},
        ),
    ])
    kpis.update(uk_jobs=int(db_gb), pk_historical=int(db_pk_hist),
                pk_supplementary=int(db_pk_supp))

    print("== 4. Companies / locations / skills ==")
    db_companies = sql_query(
        engine,
        "SELECT COUNT(DISTINCT company_id) AS n FROM jobs WHERE company_id IS NOT NULL",
    ).iloc[0]["n"]
    results.append(
        check(
            "Unique companies (CSV vs DB)",
            db_companies,
            jobs_df["company_name"].nunique(),
            abs(jobs_df["company_name"].nunique() - db_companies) <= 5,
        )
    )
    kpis["unique_companies"] = int(db_companies)
    db_cities = sql_query(
        engine, "SELECT COUNT(DISTINCT city) AS n FROM locations"
    ).iloc[0]["n"]
    kpis["unique_locations_master"] = int(db_cities)
    kpis["unique_locations_in_postings"] = int(jobs_df["city"].nunique())
    kpis["unique_skills"] = int(bridge["skill_name"].nunique())
    db_skills = sql_query(
        engine, "SELECT COUNT(DISTINCT skill_id) AS n FROM job_skills"
    ).iloc[0]["n"]
    results.append(
        check(
            "Distinct skills used",
            db_skills,
            kpis["unique_skills"],
            kpis["unique_skills"] == db_skills,
        )
    )

    print("== 5. London split ==")
    london_db = sql_query(
        engine,
        "SELECT location_group, COUNT(*) AS n FROM v_analytical_jobs "
        "WHERE country_code = 'GB' GROUP BY location_group ORDER BY location_group",
    )
    london_csv = csv("07_london_analysis.csv")[["location_group", "total_jobs"]]
    merged = london_csv.merge(london_db, on="location_group")
    results.append(
        check(
            "London groups match DB",
            len(london_db),
            len(merged),
            len(merged) == len(london_db)
            and (merged["total_jobs"] == merged["n"]).all(),
        )
    )
    lg = dict(zip(london_db.location_group, london_db.n))
    kpis["london"] = int(lg.get("London", 0))
    kpis["greater_london"] = int(lg.get("Greater London", 0))
    kpis["uk_other"] = int(lg.get("UK Other", 0))
    results.append(
        check(
            "London groups sum to UK total",
            db_gb,
            kpis["london"] + kpis["greater_london"] + kpis["uk_other"],
            kpis["london"] + kpis["greater_london"] + kpis["uk_other"] == db_gb,
        )
    )

    print("== 6. Roles & seniority ==")
    role_csv_total = int(csv("02_role_demand.csv")["job_count"].sum())
    results.append(
        check("Role demand CSV sums to total jobs", db_jobs, role_csv_total,
              role_csv_total == db_jobs)
    )
    sen_db = sql_query(
        engine,
        "SELECT seniority, country_code, COUNT(*) AS n FROM v_analytical_jobs "
        "GROUP BY seniority, country_code",
    )
    # CSV grain is seniority x country x dataset_period (PK splits into two
    # sources); aggregate to seniority x country before comparing.
    sen_csv = (
        csv("10_seniority_analysis.csv")
        .groupby(["seniority", "country_code"], as_index=False)["total_jobs"]
        .sum()
    )
    merged_sen = sen_csv.merge(sen_db, on=["seniority", "country_code"])
    results.append(
        check(
            "Seniority analysis matches DB",
            len(sen_db),
            len(merged_sen),
            len(merged_sen) == len(sen_db)
            and (merged_sen["total_jobs"] == merged_sen["n"]).all(),
        )
    )
    kpis["senior_uk"] = int(
        sen_db.query("seniority == 'senior' and country_code == 'GB'")["n"].iloc[0]
    )
    kpis["junior_uk"] = int(
        sen_db.query("seniority == 'junior' and country_code == 'GB'")["n"].iloc[0]
    )

    print("== 7. Skills: penetration denominators ==")
    skill_demand = csv("03_skill_demand.csv")
    denom_db = sql_query(
        engine, "SELECT country, COUNT(*) AS n FROM jobs GROUP BY country"
    )
    denom_map = dict(zip(denom_db.country, denom_db.n))
    bad_pen: list[str] = []
    for _, r in skill_demand.iterrows():
        expected_pct = round(100 * r.job_count / denom_map[r.country_code], 1)
        if abs(expected_pct - float(r.penetration_pct)) > 0.11:
            bad_pen.append(r.skill_name)
    results.append(
        check(
            "Skill penetration uses country denominator",
            0,
            len(bad_pen),
            not bad_pen,
        )
    )

    print("== 8. Salary truth (NaN artifact correction) ==")
    for source, expect_real in (("adzuna_uk", None), ("chisel_pk", 0),
                                ("kaggle_rozee_pk", None)):
        real = sql_query(
            engine,
            f"SELECT COUNT(*) AS n FROM v_analytical_jobs "
            f"WHERE source_name = '{source}' AND {USABLE_MIDPOINT}",
        ).iloc[0]["n"]
        if expect_real is not None:
            results.append(
                check(f"Usable salaries — {source}", expect_real, real,
                      real == expect_real)
            )
        kpis[f"usable_salaries_{source}"] = int(real)

    mo = csv("01_market_overview.csv")
    naive_cov = mo[["source_name", "salary_coverage_pct"]].to_dict("records")
    kpis["phase5_naive_salary_coverage"] = naive_cov
    results.append(
        check(
            "Phase 5 naive coverage overstates reality (documented)",
            True,
            bool((mo["salary_coverage_pct"] == 100.0).all()),
            bool((mo["salary_coverage_pct"] == 100.0).all()),
        )
    )

    print("== 9. Salary benchmarks (GBP, usable midpoints) ==")
    bench = sql_query(
        engine,
        f"""
        SELECT COUNT(*) AS n,
               ROUND(AVG(salary_midpoint)::numeric, 0) AS avg_sal,
               ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP
                      (ORDER BY salary_midpoint))::numeric, 0) AS med_sal,
               ROUND((PERCENTILE_CONT(0.25) WITHIN GROUP
                      (ORDER BY salary_midpoint))::numeric, 0) AS q25,
               ROUND((PERCENTILE_CONT(0.75) WITHIN GROUP
                      (ORDER BY salary_midpoint))::numeric, 0) AS q75
        FROM v_analytical_jobs
        WHERE country_code = 'GB' AND {USABLE_MIDPOINT}
        """,
    ).iloc[0]
    kpis["gb_salary"] = {k: float(bench[k]) for k in
                         ("n", "avg_sal", "med_sal", "q25", "q75")}
    print(f"  GB salary benchmark: {kpis['gb_salary']}")

    ss = csv("09_skill_salary.csv")
    gb_ss = ss[ss.country_code == "GB"]
    pk_ss_nan = int(ss[ss.country_code == "PK"]["median_salary"].isna().sum())
    results.extend([
        check(
            "Skill-salary view: PK medians are all unusable (excluded in PQ)",
            pk_ss_nan,
            int((ss.country_code == "PK").sum()),
            pk_ss_nan == int((ss.country_code == "PK").sum()),
        ),
        check(
            "Skill-salary GB rows have valid medians",
            0,
            int(gb_ss["median_salary"].isna().sum()),
            int(gb_ss["median_salary"].isna().sum()) == 0,
        ),
    ])

    print("== 10. Temporal ranges ==")
    trange = sql_query(
        engine,
        "SELECT source_name, MIN(posting_date)::date AS min_d, "
        "MAX(posting_date)::date AS max_d FROM v_analytical_jobs "
        "GROUP BY source_name ORDER BY source_name",
    )
    kpis["temporal_ranges"] = [
        {"source": r.source_name, "min": str(r.min_d), "max": str(r.max_d)}
        for r in trange.itertuples()
    ]
    print(f"  {kpis['temporal_ranges']}")

    passed = all(r["pass"] for r in results)
    summary = {
        "generated_by": "scripts/powerbi_qa.py",
        "database": "job_market_analytics (PostgreSQL)",
        "all_checks_pass": passed,
        "checks": results,
        "kpi_reference_values": kpis,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {OUTPUT_PATH}")
    print(f"RESULT: {'ALL CHECKS PASS' if passed else 'FAILURES PRESENT'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
