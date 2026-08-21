"""
Database loader — loads processed DataFrames into the PostgreSQL analytical schema.

Uses batch operations (execute_values) for performance. Dimension tables are
upserted via bulk get-or-create with in-memory caching. Fact and junction
tables are bulk-inserted.
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

        # Dimension caches: (key) -> id
        self._source_cache: dict[str, int] = {}
        self._company_cache: dict[tuple[str, str], int] = {}
        self._location_cache: dict[tuple[str | None, str | None, str], int] = {}
        self._industry_cache: dict[str, int] = {}
        self._title_cache: dict[tuple[str, str], int] = {}
        self._skill_cache: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def load(self, df: pd.DataFrame) -> None:
        """Load a processed DataFrame into the database.

        Steps:
          1. Bulk-load dimension tables, populate caches
          2. Bulk-insert fact rows (jobs) using executemany
          3. Bulk-insert junction rows (job_skills, salary_data)
        """
        self.logger.info("=== STAGE: LOAD ===")
        start = datetime.now(UTC)

        if df.empty:
            self.logger.warning("Nothing to load — DataFrame is empty")
            return

        total = len(df)
        self.logger.info(f"Loading {total} records...")

        with self.engine.begin() as conn:
            # 1. Preload dimension caches
            self._warm_caches(conn)
            self.logger.info(
                f"Caches: {len(self._source_cache)} sources, "
                f"{len(self._company_cache)} companies, "
                f"{len(self._location_cache)} locations, "
                f"{len(self._industry_cache)} industries, "
                f"{len(self._title_cache)} titles, "
                f"{len(self._skill_cache)} skills"
            )

            # 2. Bulk upsert dimensions from DataFrame
            self._bulk_ensure_dimensions(conn, df)

            # 3. Bulk insert jobs
            job_id_map = self._bulk_insert_jobs(conn, df)
            job_count = len(job_id_map)
            self.logger.info(f"Inserted {job_count} jobs")

            # 4. Bulk insert job_skills
            skill_rows = self._bulk_insert_job_skills(conn, df, job_id_map)

            # 5. Bulk insert salary_data
            salary_rows = self._bulk_insert_salaries(conn, df, job_id_map)

        elapsed = (datetime.now(UTC) - start).total_seconds()
        self.manifest.records_accepted = job_count
        self.logger.info(
            f"Load complete in {elapsed:.1f}s: "
            f"{job_count} jobs, {skill_rows} skill links, {salary_rows} salary records"
        )

    # ------------------------------------------------------------------
    # Cache warming
    # ------------------------------------------------------------------

    def _warm_caches(self, conn) -> None:
        """Load existing dimension IDs into memory."""
        for row in conn.execute(text("SELECT source_id, name FROM job_sources")):
            self._source_cache[row[1]] = int(row[0])

        for row in conn.execute(
            text("SELECT company_id, name, country FROM companies")
        ):
            self._company_cache[(row[1], row[2])] = int(row[0])

        for row in conn.execute(
            text("SELECT location_id, city, region, country FROM locations")
        ):
            self._location_cache[(row[1], row[2], row[3])] = int(row[0])

        for row in conn.execute(text("SELECT industry_id, name FROM industries")):
            self._industry_cache[row[1]] = int(row[0])

        for row in conn.execute(
            text(
                "SELECT title_id, normalized_title, role_category FROM job_titles"
            )
        ):
            self._title_cache[(row[1], row[2])] = int(row[0])

        for row in conn.execute(
            text("SELECT skill_id, canonical_name FROM skills")
        ):
            self._skill_cache[row[1]] = int(row[0])

    # ------------------------------------------------------------------
    # Bulk dimension upserts
    # ------------------------------------------------------------------

    def _bulk_ensure_dimensions(self, conn, df: pd.DataFrame) -> None:
        """Upsert all dimension rows from the DataFrame, populating caches."""
        # Sources
        sources = df["source"].dropna().unique()
        for src in sources:
            src = str(src)
            if src not in self._source_cache:
                res = conn.execute(
                    text(
                        "INSERT INTO job_sources (name, country) "
                        "VALUES (:name, :country) "
                        "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name "
                        "RETURNING source_id"
                    ),
                    {
                        "name": src,
                        "country": src.split("_")[-1].upper()[:2],
                    },
                )
                self._source_cache[src] = int(res.fetchone()[0])

        # Companies
        country_col = "country_code" if "country_code" in df.columns else "country"
        company_pairs = (
            df[["company_name", country_col]]
            .dropna().drop_duplicates().values.tolist()
        )
        for name, country in company_pairs:
            name, country = str(name), str(country)[:5]
            if not name or name == "nan":
                continue
            key = (name, country)
            if key not in self._company_cache:
                res = conn.execute(
                    text(
                        "INSERT INTO companies (name, name_raw, country) "
                        "VALUES (:name, :name_raw, :country) "
                        "ON CONFLICT (name, country) "
                        "DO UPDATE SET name = EXCLUDED.name "
                        "RETURNING company_id"
                    ),
                    {"name": name, "name_raw": name, "country": country},
                )
                self._company_cache[key] = int(res.fetchone()[0])

        # Locations
        loc_cols = ["city", "region", country_col]
        loc_df = df[loc_cols].dropna(subset=[country_col]).drop_duplicates()
        for _, row in loc_df.iterrows():
            city = str(row["city"]) if pd.notna(row["city"]) else None
            region = str(row["region"]) if pd.notna(row["region"]) else None
            country = str(row[country_col])[:5]
            if not city or city == "nan":
                city = None
            if not region or region == "nan":
                region = None
            key = (city, region, country)
            if key not in self._location_cache:
                res = conn.execute(
                    text(
                        "INSERT INTO locations (city, region, country) "
                        "VALUES (:city, :region, :country) "
                        "ON CONFLICT (city, region, country) "
                        "DO UPDATE SET city = EXCLUDED.city "
                        "RETURNING location_id"
                    ),
                    {"city": city, "region": region, "country": country},
                )
                self._location_cache[key] = int(res.fetchone()[0])

        # Industries
        industries = df["industry"].dropna().unique()
        for ind in industries:
            ind = str(ind)
            if not ind or ind == "nan" or ind in self._industry_cache:
                continue
            res = conn.execute(
                text(
                    "INSERT INTO industries (name) VALUES (:name) "
                    "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name "
                    "RETURNING industry_id"
                ),
                {"name": ind},
            )
            self._industry_cache[ind] = int(res.fetchone()[0])

        # Titles
        title_df = (
            df[["normalized_title", "role_category", "seniority"]]
            .dropna(subset=["normalized_title", "role_category"])
            .drop_duplicates()
        )
        for _, row in title_df.iterrows():
            nt = str(row["normalized_title"])
            rc = str(row["role_category"])
            sen = str(row.get("seniority", "unknown"))
            key = (nt, rc)
            if key not in self._title_cache:
                res = conn.execute(
                    text(
                        "INSERT INTO job_titles "
                        "(normalized_title, role_category, seniority) "
                        "VALUES (:nt, :rc, :seniority) "
                        "ON CONFLICT (normalized_title, role_category) "
                        "DO UPDATE SET seniority = EXCLUDED.seniority "
                        "RETURNING title_id"
                    ),
                    {"nt": nt, "rc": rc, "seniority": sen},
                )
                self._title_cache[key] = int(res.fetchone()[0])

        # Skills (from skills_list column)
        import numpy as np
        all_skills: set[tuple[str, str]] = set()
        for skills in df["skills_list"].dropna():
            if isinstance(skills, np.ndarray):
                skills = skills.tolist()
            if isinstance(skills, (list, tuple)):
                for s in skills:
                    if isinstance(s, dict):
                        name = s.get("normalized_skill", "")
                        cat = s.get("category", "technical")
                        if name:
                            all_skills.add((name, cat))
        for name, category in all_skills:
            if name not in self._skill_cache:
                valid_cats = {
                    "technical", "analytical", "ai_ml", "tool",
                    "business_soft", "certification", "education",
                }
                if category not in valid_cats:
                    category = "technical"
                res = conn.execute(
                    text(
                        "INSERT INTO skills (canonical_name, category) "
                        "VALUES (:name, :category) "
                        "ON CONFLICT (canonical_name) "
                        "DO UPDATE SET category = EXCLUDED.category "
                        "RETURNING skill_id"
                    ),
                    {"name": name, "category": category},
                )
                self._skill_cache[name] = int(res.fetchone()[0])

    # ------------------------------------------------------------------
    # Bulk job insert
    # ------------------------------------------------------------------

    def _bulk_insert_jobs(
        self, conn, df: pd.DataFrame
    ) -> dict[int, int]:
        """Bulk insert jobs using psycopg2 execute_values for speed.

        Returns {row_idx: job_id}.
        """
        job_rows: list[dict] = []
        valid_indices: list[int] = []

        for idx, row in df.iterrows():
            record = row.to_dict()
            source_id = self._source_cache.get(str(record.get("source", "")))
            if source_id is None:
                continue

            cc = str(record.get("country_code", record.get("country", "")))[:5]
            if not cc or cc == "nan":
                cc = "XX"

            company_id = self._company_cache.get((
                str(record.get("company_name", "")),
                cc,
            ))
            location_id = self._location_cache.get((
                str(record.get("city", "")) if record.get("city") else None,
                str(record.get("region", "")) if record.get("region") else None,
                cc,
            ))
            industry_id = self._industry_cache.get(
                str(record.get("industry", "")) if record.get("industry") else None
            )
            title_id = self._title_cache.get((
                str(record.get("normalized_title", record.get("job_title", ""))),
                str(record.get("role_category", "other")),
            ))

            source_job_id = str(record.get("source_job_id", ""))[:200]
            if not source_job_id or source_job_id == "nan":
                continue

            description = (
                record.get("description")
                or record.get("description_cleaned", "")
            )
            posting_date = self._parse_date_value(record.get("posting_date"))
            closing_date = self._parse_date_value(record.get("closing_date"))
            job_url = str(record.get("job_url") or "")[:1000] or None

            job_rows.append((
                source_id,
                source_job_id,
                str(record.get("job_title", ""))[:500],
                title_id,
                company_id,
                location_id,
                cc,
                record.get("salary_min"),
                record.get("salary_max"),
                str(record.get("salary_currency"))[:3] if record.get("salary_currency") else None,
                record.get("salary_period"),
                record.get("employment_type"),
                record.get("work_mode"),
                record.get("experience_level"),
                industry_id,
                record.get("education_requirement"),
                str(description)[:50000] if description else None,
                posting_date,
                closing_date,
                job_url,
                record.get("dq_score"),
                record.get("collected_at") or datetime.now(UTC),
                record.get("is_active", True),
            ))
            valid_indices.append(idx)

        if not job_rows:
            return {}

        # Deduplicate by (source_id, source_job_id) — keep last occurrence
        seen: dict[tuple, int] = {}
        deduped_rows: list[tuple] = []
        deduped_indices: list[int] = []
        for i, jrow in enumerate(job_rows):
            key = (jrow[0], jrow[1])  # (source_id, source_job_id)
            seen[key] = i
        for _key, orig_idx in seen.items():
            deduped_rows.append(job_rows[orig_idx])
            deduped_indices.append(valid_indices[orig_idx])
        job_rows = deduped_rows
        valid_indices = deduped_indices
        self.logger.info(
            f"Deduplicated {len(seen)} unique jobs from {len(df)} rows"
        )

        # Use psycopg2 execute_values for true bulk upsert
        raw_conn = conn.connection
        cursor = raw_conn.cursor()

        from psycopg2.extras import execute_values

        insert_sql = (
            "INSERT INTO jobs ("
            "  source_id, source_job_id, job_title, title_id, company_id,"
            "  location_id, country, salary_min, salary_max, salary_currency,"
            "  salary_period, employment_type, work_mode, experience_level,"
            "  industry_id, education_requirement, description_raw,"
            "  posting_date, closing_date, job_url,"
            "  dq_score, collected_at, is_active"
            ") VALUES %s "
            "ON CONFLICT (source_id, source_job_id) DO UPDATE SET "
            "  job_title = EXCLUDED.job_title,"
            "  title_id = EXCLUDED.title_id,"
            "  company_id = EXCLUDED.company_id,"
            "  location_id = EXCLUDED.location_id,"
            "  salary_min = EXCLUDED.salary_min,"
            "  salary_max = EXCLUDED.salary_max,"
            "  dq_score = EXCLUDED.dq_score,"
            "  updated_at = now() "
            "RETURNING job_id, source_job_id"
        )

        id_map: dict[int, int] = {}
        batch_size = 500

        for start in range(0, len(job_rows), batch_size):
            batch = job_rows[start : start + batch_size]
            batch_indices = valid_indices[start : start + batch_size]
            results = execute_values(
                cursor,
                insert_sql,
                batch,
                fetch=True,
                page_size=batch_size,
            )
            # results = [(job_id, source_job_id), ...]
            returned_ids = {r[1]: r[0] for r in results}

            # Map back to DataFrame indices
            for i, jrow in enumerate(batch):
                sjid = jrow[1]  # source_job_id
                if sjid in returned_ids:
                    id_map[batch_indices[i]] = returned_ids[sjid]

        self.logger.info(f"execute_values inserted {len(id_map)} jobs")
        return id_map

    # ------------------------------------------------------------------
    # Bulk job_skills insert
    # ------------------------------------------------------------------

    def _bulk_insert_job_skills(
        self, conn, df: pd.DataFrame, job_id_map: dict[int, int]
    ) -> int:
        """Bulk insert job-skill junction rows using psycopg2."""
        import numpy as np

        rows: list[tuple] = []
        for idx, job_id in job_id_map.items():
            skills = df.at[idx, "skills_list"]
            if skills is None or (isinstance(skills, float) and pd.isna(skills)):
                continue
            if isinstance(skills, np.ndarray):
                skills = skills.tolist()
            if not isinstance(skills, (list, tuple)) or len(skills) == 0:
                continue
            for skill in skills:
                if not isinstance(skill, dict):
                    continue
                canonical = skill.get("normalized_skill", "")
                skill_id = self._skill_cache.get(canonical)
                if skill_id is None:
                    continue
                rows.append((job_id, skill_id, skill.get("method", "lexicon")))

        if not rows:
            return 0

        # Deduplicate (job_id, skill_id) — keep first occurrence
        seen_skills: dict[tuple, tuple] = {}
        for row in rows:
            key = (row[0], row[1])
            if key not in seen_skills:
                seen_skills[key] = row
        rows = list(seen_skills.values())

        raw_conn = conn.connection
        cursor = raw_conn.cursor()
        from psycopg2.extras import execute_values

        insert_sql = (
            "INSERT INTO job_skills (job_id, skill_id, extraction_method) "
            "VALUES %s "
            "ON CONFLICT (job_id, skill_id) "
            "DO UPDATE SET mention_count = job_skills.mention_count + 1"
        )

        batch_size = 1000
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            execute_values(cursor, insert_sql, batch, page_size=batch_size)

        self.logger.info(f"Inserted {len(rows)} job-skill links")
        return len(rows)

    # ------------------------------------------------------------------
    # Bulk salary insert
    # ------------------------------------------------------------------

    def _bulk_insert_salaries(
        self, conn, df: pd.DataFrame, job_id_map: dict[int, int]
    ) -> int:
        """Bulk insert salary detail rows using psycopg2."""
        rows: list[tuple] = []
        for idx, job_id in job_id_map.items():
            record = df.iloc[idx].to_dict()
            if not self._has_salary(record):
                continue
            rows.append((
                job_id,
                record.get("salary_min"),
                record.get("salary_max"),
                str(record.get("salary_currency"))[:3] if record.get("salary_currency") else None,
                record.get("salary_period"),
                record.get("salary_type"),
            ))

        if not rows:
            return 0

        raw_conn = conn.connection
        cursor = raw_conn.cursor()
        from psycopg2.extras import execute_values

        insert_sql = (
            "INSERT INTO salary_data"
            " (job_id, salary_min, salary_max,"
            "  currency, period, salary_type) "
            "VALUES %s"
        )
        execute_values(cursor, insert_sql, rows, page_size=500)
        self.logger.info(f"Inserted {len(rows)} salary records")
        return len(rows)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_load(self) -> dict:
        """Run post-load validation queries and return a results dict."""
        results: dict = {}
        with self.engine.connect() as conn:
            for table in (
                "jobs", "companies", "locations", "skills",
                "job_skills", "salary_data", "job_sources",
            ):
                count = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
                results[f"count_{table}"] = count

            orphaned = conn.execute(text(
                "SELECT count(*) FROM job_skills js "
                "LEFT JOIN jobs j ON js.job_id = j.job_id "
                "LEFT JOIN skills sk ON js.skill_id = sk.skill_id "
                "WHERE j.job_id IS NULL OR sk.skill_id IS NULL"
            )).scalar()
            results["orphaned_job_skills"] = orphaned

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
