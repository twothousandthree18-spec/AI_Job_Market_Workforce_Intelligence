"""
Kaggle Rozee.pk dataset importer.

Loads the Pakistan Job Market Dataset (csv) from data/external/
and writes it to data/raw/kaggle_rozee_pk/.
"""

import csv
from pathlib import Path

from ingestion.base_collector import BaseCollector
from pipeline.config import EXTERNAL_DIR, RunManifest, load_source_config


class KaggleImporter(BaseCollector):
    """Import Pakistan jobs from Kaggle Rozee.pk CSV dataset."""

    source_name = "kaggle_rozee_pk"

    def __init__(self, manifest: RunManifest):
        super().__init__(manifest)
        cfg = load_source_config().get("sources", {}).get("kaggle_rozee_pk", {})
        self.expected_filename: str = cfg.get("expected_filename", "pakjobs_clean.csv")
        self.field_map: dict = load_source_config().get("schema_overrides", {}).get(
            "kaggle_rozee_pk", {}
        ).get("field_map", {})

    def collect(self) -> None:
        self.import_dataset()

    def import_dataset(self) -> None:
        csv_path = EXTERNAL_DIR / self.expected_filename
        if not csv_path.exists():
            self.logger.warning(
                f"Dataset not found: {csv_path}\n"
                f"  → Download from: https://www.kaggle.com/datasets/zincly/pakistan-job-market-dataset-rozee-pk\n"
                f"  → Place the CSV as: {csv_path}"
            )
            self.manifest.add_error(
                "kaggle_import",
                f"Dataset file not found: {csv_path.name}",
                "Download manually from Kaggle and place in data/external/",
            )
            return

        self.logger.info(f"Importing dataset: {csv_path}")
        records = self._read_csv(csv_path)
        if records:
            self._save_raw(records, tag="pk")
            self.manifest.records_read = len(records)
            self.manifest.records_accepted = len(records)
            self.logger.info(f"Imported {len(records)} Pakistan job records")
        else:
            self.logger.warning("Dataset was empty or unreadable")

    def _read_csv(self, path: Path) -> list[dict]:
        records = []
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.logger.info(f"CSV columns: {reader.fieldnames}")
            for row in reader:
                records.append(self._normalize(row))
        return records

    def _normalize(self, row: dict) -> dict:
        """Map Kaggle CSV columns to canonical schema."""
        # Handle salary parsing — may be "PKR 50,000 - PKR 80,000" or similar
        salary_raw = row.get("Salary", "") or row.get("salary", "") or ""
        salary_min, salary_max, currency = self._parse_salary(salary_raw)

        # Handle location — extract city
        location_raw = row.get("Location", "") or row.get("location", "") or ""
        city = self._extract_city(location_raw)

        # Posting date
        posting_date = row.get("Date Posted", "") or row.get("date_posted", "") or ""
        posting_date = posting_date[:10] if posting_date else None

        return {
            "source_job_id": f"rozee_{row.get('Job Title', '')}_{row.get('Company', '')}_{city}",
            "job_title": row.get("Job Title", "") or row.get("job_title", ""),
            "company_name": row.get("Company", "") or row.get("company", ""),
            "location": location_raw,
            "city": city,
            "region": "",
            "country": "pk",
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": currency,
            "salary_period": "monthly",
            "employment_type": row.get("Employment Type", "") or row.get("employment_type", ""),
            "work_mode": "on_site",
            "experience_level": row.get("Experience Level", "") or row.get("experience_level", ""),
            "industry": row.get("Industry", "") or row.get("industry", ""),
            "education_requirement": row.get("Education", "") or row.get("education", ""),
            "description": row.get("Job Description", "") or row.get("description", ""),
            "posting_date": posting_date,
            "closing_date": None,
            "job_url": row.get("Job URL", "") or row.get("url", ""),
            "collected_at": None,
        }

    @staticmethod
    def _parse_salary(raw: str) -> tuple[float | None, float | None, str]:
        """Attempt to parse salary string into min/max/currency."""
        if not raw or raw.strip().lower() in ("", "negotiable", "n/a", "na", "none"):
            return None, None, "PKR"

        currency = "PKR"
        text = raw.strip()
        if "pkr" in text.lower():
            currency = "PKR"
            text = text.lower().replace("pkr", "").strip()
        elif "usd" in text.lower() or "$" in text:
            currency = "USD"
            text = text.replace("$", "").replace("usd", "").strip()
        elif "gbp" in text.lower() or "£" in text:
            currency = "GBP"
            text = text.replace("£", "").replace("gbp", "").strip()

        # Remove commas, try to split on "-" or "to"
        text = text.replace(",", "")
        parts = [p.strip() for p in text.replace("to", "-").split("-") if p.strip()]

        nums = []
        for part in parts:
            cleaned = "".join(c for c in part if c.isdigit() or c == ".")
            try:
                nums.append(float(cleaned))
            except ValueError:
                continue

        if len(nums) >= 2:
            return nums[0], nums[1], currency
        elif len(nums) == 1:
            return nums[0], nums[0], currency
        return None, None, currency

    @staticmethod
    def _extract_city(location: str) -> str:
        """Extract city name from location string."""
        if not location:
            return ""
        # Common Pakistan city names
        cities = [
            "Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad",
            "Multan", "Peshawar", "Quetta", "Sialkot", "Gujranwala",
            "Hyderabad", " Abbottabad", "Sargodha", "Bahawalpur", "Mardan",
        ]
        for city in cities:
            if city.lower().strip() in location.lower():
                return city.strip()
        return location.split(",")[0].strip()
