"""
CHISEL/LUMS Pakistan Job Market dataset importer.

Downloads from Open Data Pakistan (ODbL license):
  ~7,000 job openings from Dec 2019 to Mar 2021.
  Fields: Job Name, label, Company Name, Job Type, Experience Required,
          Department, JD, City, Date Posted
"""

from __future__ import annotations

import csv
from pathlib import Path

from ingestion.base_collector import BaseCollector
from pipeline.config import EXTERNAL_DIR, RunManifest, load_source_config


class ChiselImporter(BaseCollector):
    """Import Pakistan jobs from CHISEL/LUMS CSV dataset."""

    source_name = "chisel_pk"

    def __init__(self, manifest: RunManifest):
        super().__init__(manifest)
        cfg = load_source_config().get("sources", {}).get("chisel_pk", {})
        self.expected_filename: str = cfg.get(
            "expected_filename", "pakistan_jobs_chisel.csv"
        )

    def collect(self) -> None:
        csv_path = EXTERNAL_DIR / self.expected_filename
        if not csv_path.exists():
            self.logger.warning(
                f"Dataset not found: {csv_path}\n"
                f"  -> Download from: https://opendata.com.pk/dataset/pakistan-s-job-market\n"
                f"  -> Place the CSV as: {csv_path}"
            )
            self.manifest.add_error(
                "chisel_import",
                f"Dataset file not found: {csv_path.name}",
                "Download from Open Data Pakistan and place in data/external/",
            )
            return

        self.logger.info(f"Importing CHISEL dataset: {csv_path}")
        records = self._read_csv(csv_path)
        if records:
            self._save_raw(records, tag="pk")
            self.manifest.records_read = len(records)
            self.manifest.records_accepted = len(records)
            self.logger.info(f"Imported {len(records)} Pakistan job records")
        else:
            self.logger.warning("Dataset was empty or unreadable")

    def _read_csv(self, path: Path) -> list[dict]:
        records: list[dict] = []
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.logger.info(f"CSV columns: {reader.fieldnames}")
            for row in reader:
                normalized = self._normalize(row)
                if normalized.get("job_title"):
                    records.append(normalized)
        return records

    def _normalize(self, row: dict) -> dict:
        """Map CHISEL CSV columns to canonical schema."""
        city = (row.get("City") or "").strip()
        company_raw = (row.get("Company Name") or "").strip()
        company_name = company_raw.replace(", Pakistan", "").strip()

        exp_raw = (row.get("Experience Required") or "").strip()
        experience_level = self._parse_experience(exp_raw)

        posting_date = self._parse_date(row.get("Date Posted"))

        job_type_raw = (row.get("Job Type") or "").strip()
        employment_type = self._parse_job_type(job_type_raw)

        description = (row.get("JD") or "").strip()

        source_id = (
            f"chisel_{row.get('Job Name', '')}_{company_name}_{city}"
        )

        return {
            "source_job_id": source_id[:200],
            "job_title": (row.get("Job Name") or "").strip(),
            "company_name": company_name,
            "location": city,
            "city": city,
            "region": "",
            "country": "pk",
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "PKR",
            "salary_period": "monthly",
            "employment_type": employment_type,
            "work_mode": "on_site",
            "experience_level": experience_level,
            "industry": (row.get("Department") or "").strip(),
            "education_requirement": None,
            "description": description,
            "posting_date": posting_date,
            "closing_date": None,
            "job_url": "",
            "collected_at": None,
        }

    @staticmethod
    def _parse_experience(raw: str) -> str | None:
        if not raw:
            return None
        lower = raw.lower().strip()
        if "fresher" in lower or "0" in lower:
            return "entry"
        if "1" in lower and "year" in lower:
            return "junior"
        if "2" in lower and "year" in lower:
            return "junior"
        if "3" in lower and "year" in lower:
            return "mid"
        if "4" in lower and "year" in lower:
            return "mid"
        if "5" in lower and "year" in lower:
            return "mid"
        if "6" in lower or "7" in lower or "8" in lower or "9" in lower or "10" in lower:
            return "senior"
        return raw.strip() if raw.strip() else None

    @staticmethod
    def _parse_job_type(raw: str) -> str:
        lower = raw.lower()
        if "full" in lower:
            return "full_time"
        if "part" in lower:
            return "part_time"
        if "contract" in lower:
            return "contract"
        if "intern" in lower:
            return "internship"
        if "freelanc" in lower:
            return "freelance"
        return raw.strip() if raw.strip() else "unknown"

    @staticmethod
    def _parse_date(raw: str | None) -> str | None:
        if not raw:
            return None
        from datetime import datetime

        raw = raw.strip()
        for fmt in ("%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(raw, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None
