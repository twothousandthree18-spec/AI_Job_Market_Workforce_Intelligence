"""
Pipeline processor — orchestrates validate → clean → normalize → NLP → save.

This is the core of Phase 3: takes staged parquet files through validation,
cleaning, normalisation, skill extraction, and outputs processed artefacts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd

from cleaning.text_cleaner import TextCleaner
from nlp.skill_extractor import SkillExtractor
from nlp.skill_normalizer import SkillNormalizer
from normalization.location_normalizer import LocationNormalizer
from normalization.salary_normalizer import SalaryNormalizer
from normalization.title_normalizer import TitleNormalizer
from pipeline.config import (
    PROCESSED_DIR,
    QUARANTINE_DIR,
    STAGING_DIR,
    RunManifest,
)
from validation.dq_report import DQReport
from validation.duplicate_detector import DuplicateDetector
from validation.validator import RecordValidator


class PipelineProcessor:
    """Orchestrates the processing pipeline: validate → clean → normalise → NLP."""

    def __init__(self, manifest: RunManifest) -> None:
        self.manifest = manifest
        self.logger = manifest.logger
        self.validator = RecordValidator()
        self.dup_detector = DuplicateDetector()
        self.dq_report = DQReport()
        self.cleaner = TextCleaner()
        self.skill_extractor = SkillExtractor()
        self.skill_normalizer = SkillNormalizer()
        self.title_normalizer = TitleNormalizer()
        self.location_normalizer = LocationNormalizer()
        self.salary_normalizer = SalaryNormalizer()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def process(self, source: str | None = None) -> pd.DataFrame:
        """Run the full processing pipeline on staging data.

        Parameters
        ----------
        source : str | None
            If given, process only the parquet for this source
            (e.g. ``"kaggle_rozee_pk"``).  Otherwise process all staging files.

        Returns
        -------
        pd.DataFrame
            The fully processed DataFrame.
        """
        self.logger.info("=== STAGE: PROCESS ===")
        start = datetime.now(UTC)

        df = self._load_staging(source)
        if df.empty:
            self.logger.warning("No staging records to process")
            return df

        self.manifest.records_read = len(df)
        self.logger.info(f"Loaded {len(df)} staging records")

        df = self._validate(df)
        df = self._clean(df)
        df = self._normalize(df)
        df = self._extract_skills(df)
        self._save_outputs(df)

        elapsed = (datetime.now(UTC) - start).total_seconds()
        self.logger.info(
            f"Processing complete: {len(df)} records in {elapsed:.1f}s "
            f"(accepted={self.manifest.records_accepted}, "
            f"rejected={self.manifest.records_rejected})"
        )
        return df

    # ------------------------------------------------------------------
    # Step loaders
    # ------------------------------------------------------------------

    def _load_staging(self, source: str | None = None) -> pd.DataFrame:
        """Load staging parquet files into a single DataFrame."""
        if source:
            path = STAGING_DIR / f"{source}.parquet"
            if not path.exists():
                self.logger.error(f"Staging file not found: {path}")
                return pd.DataFrame()
            return pd.read_parquet(path)

        frames: list[pd.DataFrame] = []
        for p in sorted(STAGING_DIR.glob("*.parquet")):
            frames.append(pd.read_parquet(p))
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate records, score them, detect duplicates, quarantine bad ones."""
        self.logger.info("Running validation...")
        start = datetime.now(UTC)

        if "source" not in df.columns:
            df["source"] = ""

        scores: list[float] = []
        all_issues: list[list[dict]] = []

        for idx in df.index:
            row = df.loc[idx]
            record = row.to_dict()

            # Derive source from filename when missing
            if not record.get("source"):
                record["source"] = self._infer_source(row, df)

            # Validate
            issues = self.validator.validate(record)
            score = self.validator.score_record(record)
            scores.append(score)
            all_issues.append(issues)

            record_id = str(record.get("source_job_id", idx))
            self.dq_report.add_record_result(record_id, issues, score)

            if issues:
                self.manifest.records_rejected += 1
            else:
                self.manifest.records_accepted += 1

        df["dq_score"] = scores

        # Duplicate detection
        df = self.dup_detector.mark_duplicates(df)

        dup_count = int(df["is_duplicate"].sum())
        self.logger.info(f"Validation: {dup_count} duplicates detected")

        # Quarantine low-quality records
        quarantine_mask = df["dq_score"] < 40
        quarantine_count = int(quarantine_mask.sum())
        if quarantine_count:
            quarantine_df = df.loc[quarantine_mask]
            ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            quarantine_path = QUARANTINE_DIR / f"quarantined_{ts}.parquet"
            quarantine_df.to_parquet(quarantine_path, index=False)
            self.logger.info(
                f"Quarantined {quarantine_count} records to {quarantine_path}"
            )

        # DQ report summary
        self._build_dq_summary(df)

        elapsed = (datetime.now(UTC) - start).total_seconds()
        self.logger.info(f"Validation complete in {elapsed:.1f}s")
        return df

    def _infer_source(self, row: pd.Series, df: pd.DataFrame) -> str:
        """Infer the source name from the parquet filename or row data."""
        source = row.get("source", "")
        if source and str(source) != "nan" and str(source).strip():
            return str(source).strip()
        return "unknown"

    def _build_dq_summary(self, df: pd.DataFrame) -> None:
        """Build and save the DQ report summary."""
        total = len(df)
        valid = int(((df["dq_score"] >= 70) & (~df["is_duplicate"])).sum())
        flagged = int((df["dq_score"] < 70).sum())
        duplicates = int(df["is_duplicate"].sum())
        invalid = total - valid

        by_severity: dict[str, int] = {}
        by_check: dict[str, int] = {}

        for record_data in self.dq_report.records.values():
            for issue in record_data["issues"]:
                sev = issue.get("severity", "unknown")
                chk = issue.get("check", "unknown")
                by_severity[sev] = by_severity.get(sev, 0) + 1
                by_check[chk] = by_check.get(chk, 0) + 1

        self.dq_report.generate_summary(
            total=total,
            valid=valid,
            invalid=invalid,
            flagged=flagged,
            duplicates=duplicates,
            by_severity_count=by_severity,
            by_check_count=by_check,
        )

        self.dq_report.save_json(self.manifest.quality_report_path())
        self.dq_report.save_markdown(self.manifest.quality_report_md_path())
        self.logger.info(f"DQ report saved to {self.manifest.quality_report_path()}")

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply text cleaning to relevant fields."""
        self.logger.info("Running text cleaning...")
        start = datetime.now(UTC)
        df = df.copy()

        for idx, row in df.iterrows():
            record = row.to_dict()
            cleaned = self.cleaner.clean_all(record)
            if "description_cleaned" in cleaned:
                df.at[idx, "description_cleaned"] = cleaned["description_cleaned"]
            # TextCleaner also cleans job_title and company_name in-place
            df.at[idx, "job_title"] = cleaned.get("job_title", row.get("job_title", ""))
            df.at[idx, "company_name"] = cleaned.get("company_name", row.get("company_name", ""))

        elapsed = (datetime.now(UTC) - start).total_seconds()
        self.logger.info(f"Cleaning complete in {elapsed:.1f}s")
        return df

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize titles, locations, and salaries."""
        self.logger.info("Running normalisation...")
        start = datetime.now(UTC)

        df = self.title_normalizer.normalize_batch(df)
        df = self.location_normalizer.normalize_batch(df)
        df = self.salary_normalizer.normalize_batch(df)

        now = datetime.now(UTC)
        df["collected_at"] = df["collected_at"].fillna(now)

        elapsed = (datetime.now(UTC) - start).total_seconds()
        self.logger.info(f"Normalisation complete in {elapsed:.1f}s")
        return df

    # ------------------------------------------------------------------
    # Skill extraction
    # ------------------------------------------------------------------

    def _extract_skills(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract and normalise skills for each record."""
        self.logger.info("Extracting skills...")
        start = datetime.now(UTC)
        df = df.copy()

        skills_per_row: list[list[dict]] = []

        for _idx, row in df.iterrows():
            record = row.to_dict()
            raw_skills = self.skill_extractor.extract_from_record(record)
            normalised = self.skill_normalizer.normalize_batch(raw_skills)
            skills_per_row.append(normalised)

        df["skills_list"] = skills_per_row

        total_skills = sum(len(s) for s in skills_per_row)
        unique_skills: set[str] = set()
        for skills in skills_per_row:
            for s in skills:
                unique_skills.add(s.get("normalized_skill", ""))

        elapsed = (datetime.now(UTC) - start).total_seconds()
        self.logger.info(
            f"Skill extraction complete in {elapsed:.1f}s: "
            f"{total_skills} total mentions, {len(unique_skills)} unique skills"
        )
        return df

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _save_outputs(self, df: pd.DataFrame) -> None:
        """Save processed parquet and skills summary."""
        self.logger.info("Saving processed outputs...")
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

        # Full processed parquet
        out_path = PROCESSED_DIR / "processed.parquet"
        df.to_parquet(out_path, index=False)
        self.logger.info(f"Saved processed parquet: {out_path} ({len(df)} rows)")

        # Per-source parquets
        if "source" in df.columns:
            for source_name, group in df.groupby("source"):
                src_path = PROCESSED_DIR / f"{source_name}.parquet"
                group.to_parquet(src_path, index=False)
                self.logger.info(f"  -> {src_path} ({len(group)} rows)")

        # Skills summary JSON
        skills_summary: dict[str, int] = {}
        if "skills_list" in df.columns:
            for skills in df["skills_list"]:
                if isinstance(skills, list):
                    for s in skills:
                        name = s.get("normalized_skill", "unknown")
                        skills_summary[name] = skills_summary.get(name, 0) + 1

        skills_path = PROCESSED_DIR / "extracted_skills.json"
        with open(skills_path, "w", encoding="utf-8") as f:
            json.dump(skills_summary, f, indent=2, ensure_ascii=False)
        self.logger.info(
            f"Skills summary saved: {skills_path}"
            f" ({len(skills_summary)} unique skills)"
        )
