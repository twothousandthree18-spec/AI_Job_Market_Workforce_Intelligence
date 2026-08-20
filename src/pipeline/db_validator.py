"""
Post-load database validator.

Runs referential-integrity and completeness checks against the PostgreSQL
analytical schema after a load step.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from pipeline.config import DATABASE_URL, RunManifest

_MAIN_TABLES = [
    "job_sources",
    "companies",
    "locations",
    "industries",
    "job_titles",
    "skills",
    "jobs",
    "job_skills",
    "salary_data",
    "data_quality_results",
    "ingestion_runs",
    "skill_trends",
    "job_categories",
]


class DatabaseValidator:
    """Validates referential integrity and completeness of the loaded data."""

    def __init__(self, manifest: RunManifest) -> None:
        self.manifest = manifest
        self.logger = manifest.logger
        self.engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def validate(self) -> dict:
        """Run all validation checks and return a results dictionary.

        Keys
        ----
        row_counts : dict[str, int]
        orphaned_skills : int
        orphaned_companies : int
        orphaned_locations : int
        jobs_without_skills : int
        dq_results_count : int
        all_passed : bool
        """
        self.logger.info("=== STAGE: DB_VALIDATE ===")
        start = datetime.now(UTC)

        results: dict = {}

        with self.engine.connect() as conn:
            # 1. Row counts
            row_counts: dict[str, int] = {}
            for table in _MAIN_TABLES:
                try:
                    count = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()  # noqa: S608
                    row_counts[table] = count
                except Exception:
                    row_counts[table] = -1
            results["row_counts"] = row_counts

            # 2. Orphaned skills (job_skills → jobs / skills FKs)
            results["orphaned_skills"] = conn.execute(text(
                "SELECT count(*) FROM job_skills js "
                "LEFT JOIN jobs j ON js.job_id = j.job_id "
                "LEFT JOIN skills sk ON js.skill_id = sk.skill_id "
                "WHERE j.job_id IS NULL OR sk.skill_id IS NULL"
            )).scalar()

            # 3. Orphaned companies (jobs → companies FK)
            results["orphaned_companies"] = conn.execute(text(
                "SELECT count(*) FROM jobs j "
                "LEFT JOIN companies c ON j.company_id = c.company_id "
                "WHERE j.company_id IS NOT NULL AND c.company_id IS NULL"
            )).scalar()

            # 4. Orphaned locations (jobs → locations FK)
            results["orphaned_locations"] = conn.execute(text(
                "SELECT count(*) FROM jobs j "
                "LEFT JOIN locations l ON j.location_id = l.location_id "
                "WHERE j.location_id IS NOT NULL AND l.location_id IS NULL"
            )).scalar()

            # 5. Jobs without any skill links
            results["jobs_without_skills"] = conn.execute(text(
                "SELECT count(*) FROM jobs j "
                "LEFT JOIN job_skills js ON j.job_id = js.job_id "
                "WHERE js.job_id IS NULL"
            )).scalar()

            # 6. DQ results count
            results["dq_results_count"] = conn.execute(text(
                "SELECT count(*) FROM data_quality_results"
            )).scalar()

        # 7. Overall pass
        results["all_passed"] = (
            results["orphaned_skills"] == 0
            and results["orphaned_companies"] == 0
            and results["orphaned_locations"] == 0
        )

        elapsed = (datetime.now(UTC) - start).total_seconds()
        self.logger.info(f"DB validation complete in {elapsed:.1f}s")
        self.log_results(results)
        return results

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_results(self, results: dict) -> None:
        """Log a human-readable summary table."""
        self.logger.info("--- Database Validation Results ---")

        row_counts = results.get("row_counts", {})
        if row_counts:
            self.logger.info("Row counts:")
            for table, count in row_counts.items():
                self.logger.info(f"  {table:30s} {count:>8,}")

        self.logger.info(f"Orphaned skills:          {results.get('orphaned_skills', '?'):>8}")
        self.logger.info(f"Orphaned companies:       {results.get('orphaned_companies', '?'):>8}")
        self.logger.info(f"Orphaned locations:       {results.get('orphaned_locations', '?'):>8}")
        self.logger.info(f"Jobs without skills:      {results.get('jobs_without_skills', '?'):>8}")
        self.logger.info(f"DQ results count:         {results.get('dq_results_count', '?'):>8}")
        self.logger.info(f"All checks passed:        {results.get('all_passed', False)}")
