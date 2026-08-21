"""Tests for Phase 5 analytics layer."""
from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://jobmarket:changeme@localhost:5432/job_market_analytics"


@pytest.fixture
def engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


class TestAnalyticalViews:
    """Verify all analytical views exist and return valid data."""

    def test_v_analytical_jobs_has_rows(self, engine):
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM v_analytical_jobs")).scalar()
        assert count > 0

    def test_v_market_overview_has_all_sources(self, engine):
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT COUNT(*) FROM v_market_overview")).scalar()
        assert rows >= 3  # chisel_pk, adzuna_uk, kaggle_rozee_pk

    def test_v_skill_demand_has_skills(self, engine):
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM v_skill_demand")).scalar()
        assert count > 0

    def test_v_skill_comparison_has_both_countries(self, engine):
        with engine.connect() as conn:
            query = (
                "SELECT * FROM v_skill_comparison "
                "WHERE uk_job_count > 0 AND pk_job_count > 0"
            )
            df = pd.read_sql(text(query), conn)
        assert len(df) > 0

    def test_v_london_analysis_has_london(self, engine):
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM v_london_analysis"), conn)
        locations = df["location_group"].tolist()
        assert "London" in locations

    def test_v_role_demand_has_roles(self, engine):
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM v_role_demand"), conn)
        roles = df["role_category"].unique()
        assert "data_analyst" in roles or "data_scientist" in roles

    def test_v_seniority_analysis_has_levels(self, engine):
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM v_seniority_analysis"), conn)
        levels = df["seniority"].unique()
        assert "junior" in levels or "senior" in levels


class TestSkillPenetration:
    """Verify skill penetration percentages are valid."""

    def test_penetration_pct_range(self, engine):
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM v_skill_demand"), conn)
        assert (df["penetration_pct"] >= 0).all()
        assert (df["penetration_pct"] <= 100).all()

    def test_penetration_sums_reasonably(self, engine):
        with engine.connect() as conn:
            df = pd.read_sql(text(
                "SELECT country_code, SUM(penetration_pct) AS total "
                "FROM v_skill_demand GROUP BY country_code"
            ), conn)
        # Total penetration can exceed 100% since skills are not mutually exclusive
        assert (df["total"] > 0).all()


class TestSalaryAnalysis:
    """Verify salary calculations are sensible."""

    def test_salary_midpoint_positive(self, engine):
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM v_salary_analysis"), conn)
        valid = df[df["salary_midpoint"].notna()]
        if len(valid) > 0:
            assert (valid["salary_midpoint"] > 0).all()

    def test_salary_min_le_max(self, engine):
        with engine.connect() as conn:
            df = pd.read_sql(text(
                "SELECT * FROM v_salary_analysis "
                "WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL"
            ), conn)
        if len(df) > 0:
            violations = df[df["salary_min"] > df["salary_max"]]
            assert len(violations) == 0, f"Salary min > max in {len(violations)} rows"


class TestCooccurrence:
    """Verify co-occurrence pairs are valid."""

    def test_no_self_pairs(self, engine):
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM v_skill_cocurrence"), conn)
        self_pairs = df[df["skill_a"] == df["skill_b"]]
        assert len(self_pairs) == 0

    def test_cooccurrence_positive(self, engine):
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM v_skill_cocurrence"), conn)
        assert (df["co_occurrence_count"] > 0).all()


class TestEmployerAnalysis:
    """Verify employer concentration is valid."""

    def test_employer_pct_range(self, engine):
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM v_employer_analysis"), conn)
        assert (df["pct_of_country"] >= 0).all()
        assert (df["pct_of_country"] <= 100).all()

    def test_top_employer_has_multiple_jobs(self, engine):
        with engine.connect() as conn:
            df = pd.read_sql(text(
                "SELECT * FROM v_employer_analysis ORDER BY job_count DESC LIMIT 1"
            ), conn)
        assert len(df) > 0
        assert df.iloc[0]["job_count"] >= 2


class TestCrossValidation:
    """SQL-Python cross-validation tests."""

    def test_total_jobs_agree(self, engine):
        with engine.connect() as conn:
            sql_count = conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar()
        df = pd.read_parquet("data/processed/processed.parquet")
        py_count = df.groupby(["source", "source_job_id"]).ngroups
        assert sql_count == py_count

    def test_uk_job_count_agree(self, engine):
        with engine.connect() as conn:
            sql_count = conn.execute(
                text("SELECT COUNT(*) FROM jobs WHERE country='GB'")
            ).scalar()
        df = pd.read_parquet("data/processed/processed.parquet")
        uk_df = df[df["country_code"] == "GB"]
        py_count = len(uk_df.drop_duplicates(subset=["source", "source_job_id"]))
        assert sql_count == py_count

    def test_pk_job_count_agree(self, engine):
        with engine.connect() as conn:
            sql_count = conn.execute(
                text("SELECT COUNT(*) FROM jobs WHERE country='PK'")
            ).scalar()
        df = pd.read_parquet("data/processed/processed.parquet")
        pk_df = df[df["country_code"] == "PK"]
        py_count = len(pk_df.drop_duplicates(subset=["source", "source_job_id"]))
        assert sql_count == py_count
