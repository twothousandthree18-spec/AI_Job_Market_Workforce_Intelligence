"""
Database loader — loads processed DataFrames into the PostgreSQL analytical schema.

Uses SQLAlchemy with parameterized queries.  Dimension tables are upserted
(get-or-create), fact and junction tables are inserted.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from pipeline.config import DATABASE_URL, RunManifest


class DatabaseLoader:
    """Loads processed job-posting data into PostgreSQL."""

    def __init__(self, manifest: RunManifest) -> None:
        self.manifest = manifest
        self.logger = manifest.logger
        self.engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def load(self, df: pd.DataFrame) -> None:
        """Load a processed DataFrame into the database.

        Steps:
          1. Load dimension tables (get-or-create IDs)
          2. Insert fact rows (jobs)
          3. Insert junction rows (job_skills, salary_data)
        """
        self.logger.info("=== STAGE: LOAD ===")
        start = datetime.now(UTC)

        if df.empty:
            self.logger.warning("Nothing to load — DataFrame is empty")
            return

        job_count = 0
        skill_rows = 0
        salary_rows = 0

        with self.engine.begin() as conn:
            for _idx, row in df.iterrows():
                record = row.to_dict()

                source_id = self._ensure_source(conn, str(record.get("source", "unknown")))
                company_id = self._ensure_company(
                    conn,
                    str(record.get("company_name", "")),
                    str(record.get("country_code", record.get("country", ""))),
                )
                location_id = self._ensure_location(
                    conn,
                    str(record.get("city", "")) or None,
                    str(record.get("region", "")) or None,
                    str(record.get("country_code", record.get("country", ""))),
                )
                industry_id = self._ensure_industry(conn, str(record.get("industry", "")) or None)
                title_id = self._ensure_title(
                    conn,
                    str(record.get("normalized_title", record.get("job_title", ""))),
                    str(record.get("role_category", "other")),
                    str(record.get("seniority", "unknown")),
                )

                job_id = self._load_job(
                    conn, record, source_id, company_id, location_id, industry_id, title_id,
                )
                if job_id is None:
                    continue
                job_count += 1

                # Skills
                skills = record.get("skills_list")
                if skills is not None and hasattr(skills, "__iter__") and len(skills) > 0:
                    skills_list = list(skills)
                    self._load_job_skills(conn, job_id, skills_list)
                    skill_rows += len(skills_list)

                # Salary detail
                if self._has_salary(record):
                    self._load_salary(conn, job_id, record)
                    salary_rows += 1

        elapsed = (datetime.now(UTC) - start).total_seconds()
        self.manifest.records_accepted = job_count
        self.logger.info(
            f"Load complete in {elapsed:.1f}s: "
            f"{job_count} jobs, {skill_rows} skill links, {salary_rows} salary records"
        )

    # ------------------------------------------------------------------
    # Dimension upserts
    # ------------------------------------------------------------------

    def _ensure_source(self, conn, source_name: str) -> int:
        result = conn.execute(
            text("SELECT source_id FROM job_sources WHERE name = :name"),
            {"name": source_name},
        )
        row = result.fetchone()
        if row:
            return int(row[0])

        result = conn.execute(
            text(
                "INSERT INTO job_sources (name, country) "
                "VALUES (:name, :country) "
                "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING source_id"
            ),
            {"name": source_name, "country": source_name.split("_")[-1].upper()[:2]},
        )
        return int(result.fetchone()[0])

    def _ensure_company(self, conn, name: str, country: str) -> int | None:
        if not name or name == "nan":
            return None
        result = conn.execute(
            text("SELECT company_id FROM companies WHERE name = :name AND country = :country"),
            {"name": name, "country": country},
        )
        row = result.fetchone()
        if row:
            return int(row[0])

        result = conn.execute(
            text(
                "INSERT INTO companies (name, name_raw, country) "
                "VALUES (:name, :name_raw, :country) "
                "ON CONFLICT (name, country) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING company_id"
            ),
            {"name": name, "name_raw": name, "country": country},
        )
        return int(result.fetchone()[0])

    def _ensure_location(
        self, conn, city: str | None, region: str | None, country: str,
    ) -> int | None:
        if not country:
            return None
        result = conn.execute(
            text(
                "SELECT location_id FROM locations "
                "WHERE city IS NOT DISTINCT FROM :city "
                "AND region IS NOT DISTINCT FROM :region "
                "AND country = :country"
            ),
            {"city": city, "region": region, "country": country},
        )
        row = result.fetchone()
        if row:
            return int(row[0])

        result = conn.execute(
            text(
                "INSERT INTO locations (city, region, country) "
                "VALUES (:city, :region, :country) "
                "ON CONFLICT (city, region, country) DO UPDATE SET city = EXCLUDED.city "
                "RETURNING location_id"
            ),
            {"city": city, "region": region, "country": country},
        )
        return int(result.fetchone()[0])

    def _ensure_industry(self, conn, name: str | None) -> int | None:
        if not name or name == "nan":
            return None
        result = conn.execute(
            text("SELECT industry_id FROM industries WHERE name = :name"),
            {"name": name},
        )
        row = result.fetchone()
        if row:
            return int(row[0])

        result = conn.execute(
            text(
                "INSERT INTO industries (name) "
                "VALUES (:name) "
                "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING industry_id"
            ),
            {"name": name},
        )
        return int(result.fetchone()[0])

    def _ensure_title(
        self, conn, normalized_title: str, role_category: str, seniority: str,
    ) -> int | None:
        if not normalized_title or normalized_title == "nan":
            return None
        result = conn.execute(
            text(
                "SELECT title_id FROM job_titles "
                "WHERE normalized_title = :nt AND role_category = :rc"
            ),
            {"nt": normalized_title, "rc": role_category},
        )
        row = result.fetchone()
        if row:
            return int(row[0])

        result = conn.execute(
            text(
                "INSERT INTO job_titles (normalized_title, role_category, seniority) "
                "VALUES (:nt, :rc, :seniority) "
                "ON CONFLICT (normalized_title, role_category) "
                "DO UPDATE SET seniority = EXCLUDED.seniority "
                "RETURNING title_id"
            ),
            {"nt": normalized_title, "rc": role_category, "seniority": seniority},
        )
        return int(result.fetchone()[0])

    def _ensure_skill(self, conn, canonical_name: str, category: str) -> int | None:
        if not canonical_name or canonical_name == "nan":
            return None
        result = conn.execute(
            text("SELECT skill_id FROM skills WHERE canonical_name = :name"),
            {"name": canonical_name},
        )
        row = result.fetchone()
        if row:
            return int(row[0])

        valid_categories = {
            "technical", "analytical", "ai_ml", "tool",
            "business_soft", "certification", "education",
        }
        if category not in valid_categories:
            category = "technical"

        result = conn.execute(
            text(
                "INSERT INTO skills (canonical_name, category) "
                "VALUES (:name, :category) "
                "ON CONFLICT (canonical_name) DO UPDATE SET category = EXCLUDED.category "
                "RETURNING skill_id"
            ),
            {"name": canonical_name, "category": category},
        )
        return int(result.fetchone()[0])

    # ------------------------------------------------------------------
    # Fact / junction inserts
    # ------------------------------------------------------------------

    def _load_job(
        self,
        conn,
        record: dict,
        source_id: int,
        company_id: int | None,
        location_id: int | None,
        industry_id: int | None,
        title_id: int | None,
    ) -> int | None:
        source_job_id = str(record.get("source_job_id", ""))
        if not source_job_id or source_job_id == "nan":
            return None

        job_title = str(record.get("job_title", ""))[:500]
        country = str(record.get("country_code", record.get("country", "")))
        if not country or country == "nan":
            country = "XX"

        salary_min = record.get("salary_min")
        salary_max = record.get("salary_max")
        salary_currency = record.get("salary_currency")
        salary_period = record.get("salary_period")
        employment_type = record.get("employment_type")
        work_mode = record.get("work_mode")
        experience_level = record.get("experience_level")
        education_requirement = record.get("education_requirement")
        description = record.get("description") or record.get("description_cleaned", "")
        posting_date = self._parse_date_value(record.get("posting_date"))
        closing_date = self._parse_date_value(record.get("closing_date"))
        job_url = record.get("job_url")
        dq_score = record.get("dq_score")
        is_active = record.get("is_active", True)
        collected_at = record.get("collected_at") or datetime.now(UTC)

        result = conn.execute(
            text(
                "INSERT INTO jobs ("
                "  source_id, source_job_id, job_title, title_id, company_id, location_id, country,"
                "  salary_min, salary_max, salary_currency, salary_period,"
                "  employment_type, work_mode, experience_level,"
                "  industry_id, education_requirement,"
                "  description_raw, posting_date, closing_date, job_url,"
                "  dq_score, collected_at, is_active"
                ") VALUES ("
                "  :source_id, :source_job_id, :job_title, :title_id,"
                "  :company_id, :location_id, :country,"
                "  :salary_min, :salary_max, :salary_currency, :salary_period,"
                "  :employment_type, :work_mode, :experience_level,"
                "  :industry_id, :education_requirement,"
                "  :description, :posting_date, :closing_date, :job_url,"
                "  :dq_score, :collected_at, :is_active"
                ") "
                "ON CONFLICT (source_id, source_job_id) "
                "DO UPDATE SET "
                "  job_title = EXCLUDED.job_title,"
                "  title_id = EXCLUDED.title_id,"
                "  company_id = EXCLUDED.company_id,"
                "  location_id = EXCLUDED.location_id,"
                "  salary_min = EXCLUDED.salary_min,"
                "  salary_max = EXCLUDED.salary_max,"
                "  dq_score = EXCLUDED.dq_score,"
                "  updated_at = now() "
                "RETURNING job_id"
            ),
            {
                "source_id": source_id,
                "source_job_id": source_job_id[:200],
                "job_title": job_title,
                "title_id": title_id,
                "company_id": company_id,
                "location_id": location_id,
                "country": country[:5],
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": str(salary_currency)[:3] if salary_currency else None,
                "salary_period": salary_period,
                "employment_type": employment_type,
                "work_mode": work_mode,
                "experience_level": experience_level,
                "industry_id": industry_id,
                "education_requirement": education_requirement,
                "description": str(description)[:50000] if description else None,
                "posting_date": posting_date,
                "closing_date": closing_date,
                "job_url": str(job_url)[:1000] if job_url else None,
                "dq_score": dq_score,
                "collected_at": collected_at,
                "is_active": is_active,
            },
        )
        row = result.fetchone()
        return int(row[0]) if row else None

    def _load_job_skills(self, conn, job_id: int, skills: list[dict]) -> None:
        for skill in skills:
            canonical = skill.get("normalized_skill", "")
            category = skill.get("category", "technical")
            method = skill.get("method", "lexicon")
            skill_id = self._ensure_skill(conn, canonical, category)
            if skill_id is None:
                continue

            conn.execute(
                text(
                    "INSERT INTO job_skills (job_id, skill_id, extraction_method) "
                    "VALUES (:job_id, :skill_id, :method) "
                    "ON CONFLICT (job_id, skill_id) "
                    "DO UPDATE SET mention_count = job_skills.mention_count + 1"
                ),
                {"job_id": job_id, "skill_id": skill_id, "method": method},
            )

    def _load_salary(self, conn, job_id: int, record: dict) -> None:
        salary_min = record.get("salary_min")
        salary_max = record.get("salary_max")
        currency = record.get("salary_currency")
        period = record.get("salary_period")
        salary_type = record.get("salary_type")

        conn.execute(
            text(
                "INSERT INTO salary_data"
                " (job_id, salary_min, salary_max,"
                "  currency, period, salary_type) "
                "VALUES (:job_id, :salary_min, :salary_max, :currency, :period, :salary_type)"
            ),
            {
                "job_id": job_id,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "currency": str(currency)[:3] if currency else None,
                "period": period,
                "salary_type": salary_type,
            },
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_load(self) -> dict:
        """Run post-load validation queries and return a results dict."""
        results: dict = {}
        with self.engine.connect() as conn:
            # Row counts for main tables
            for table in (
                "jobs", "companies", "locations", "skills",
                "job_skills", "salary_data", "job_sources",
            ):
                count = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
                results[f"count_{table}"] = count

            # Orphaned job_skills
            orphaned = conn.execute(text(
                "SELECT count(*) FROM job_skills js "
                "LEFT JOIN jobs j ON js.job_id = j.job_id "
                "LEFT JOIN skills sk ON js.skill_id = sk.skill_id "
                "WHERE j.job_id IS NULL OR sk.skill_id IS NULL"
            )).scalar()
            results["orphaned_job_skills"] = orphaned

            # Jobs without skills
            no_skills = conn.execute(text(
                "SELECT count(*) FROM jobs j "
                "LEFT JOIN job_skills js ON j.job_id = js.job_id "
                "WHERE js.job_id IS NULL"
            )).scalar()
            results["jobs_without_skills"] = no_skills

        self.logger.info(f"Load validation: {results}")
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date_value(value) -> str | None:
        """Best-effort conversion to a date string for PostgreSQL."""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value or value == "NaT" or value == "nan":
                return None
        try:
            ts = pd.Timestamp(value)
            if pd.isna(ts):
                return None
            return ts.strftime("%Y-%m-%d")
        except Exception:
            return None

    @staticmethod
    def _has_salary(record: dict) -> bool:
        """Return True if the record carries usable salary data."""
        sal_min = record.get("salary_min")
        sal_max = record.get("salary_max")
        has_values = (
            sal_min is not None
            and not (isinstance(sal_min, float) and pd.isna(sal_min))
        ) or (
            sal_max is not None
            and not (isinstance(sal_max, float) and pd.isna(sal_max))
        )
        return bool(has_values)
