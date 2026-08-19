"""
Staging converter — transforms raw JSON files into source-agnostic parquet.

Raw (per-source JSON) → Staging (parquet with canonical column names)
"""

import json
from pathlib import Path

import pandas as pd

from pipeline.config import RAW_DIR, STAGING_DIR, RunManifest, load_schema_manifest

# Canonical columns in staging output
CANONICAL_COLUMNS = [
    "source",
    "source_job_id",
    "job_title",
    "company_name",
    "location",
    "city",
    "region",
    "country",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_period",
    "employment_type",
    "work_mode",
    "experience_level",
    "industry",
    "education_requirement",
    "description",
    "posting_date",
    "closing_date",
    "job_url",
    "collected_at",
]


class StagingConverter:
    """Read raw JSON files, normalize columns, write staging parquet."""

    def __init__(self, manifest: RunManifest):
        self.manifest = manifest
        self.logger = manifest.logger
        self.schema = load_schema_manifest()

    def convert_all(self) -> None:
        raw_dirs = [d for d in RAW_DIR.iterdir() if d.is_dir()]
        if not raw_dirs:
            self.logger.warning("No raw directories found — nothing to stage")
            return

        for src_dir in raw_dirs:
            source_name = src_dir.name
            json_files = sorted(src_dir.glob("*.json"))
            if not json_files:
                self.logger.info(f"  {source_name}: no JSON files, skipping")
                continue
            self.logger.info(f"  {source_name}: {len(json_files)} raw files")
            self._convert_source(source_name, json_files)

    def _convert_source(self, source_name: str, json_files: list[Path]) -> None:
        all_records = []
        for jf in json_files:
            with open(jf, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                all_records.extend(data)
            else:
                all_records.append(data)

        if not all_records:
            self.logger.info(f"  {source_name}: 0 records in raw files")
            return

        df = pd.DataFrame(all_records)

        # Ensure all canonical columns exist
        for col in CANONICAL_COLUMNS:
            if col not in df.columns:
                df[col] = None

        # Select canonical columns only
        df = df[CANONICAL_COLUMNS]

        # Type coercion
        for col in ["salary_min", "salary_max"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["posting_date"] = pd.to_datetime(df["posting_date"], errors="coerce")
        df["closing_date"] = pd.to_datetime(df["closing_date"], errors="coerce")

        # Strip whitespace from string columns
        str_cols = df.select_dtypes(include=["object"]).columns
        df[str_cols] = df[str_cols].apply(lambda x: x.str.strip() if hasattr(x, "str") else x)

        # Drop rows with no job title or no source_job_id
        before = len(df)
        df = df.dropna(subset=["job_title", "source_job_id"])
        dropped = before - len(df)
        if dropped > 0:
            self.logger.warning(f"  Dropped {dropped} rows with missing title/source_job_id")

        # Write staging parquet
        out_path = STAGING_DIR / f"{source_name}.parquet"
        df.to_parquet(out_path, index=False)
        self.manifest.records_accepted += len(df)
        self.logger.info(
            f"  {source_name}: {len(df)} records -> {out_path}"
            f"  (schema columns: {list(df.columns)})"
        )
