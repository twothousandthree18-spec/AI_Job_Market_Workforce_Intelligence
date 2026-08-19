"""
Adzuna UK collector — fetches jobs from the Adzuna API (gb search).

Requires ADZUNA_APP_ID and ADZUNA_APP_KEY in .env.

Respects:
  - rate_limit: 2 req/sec (configurable)
  - max_pages: 20 (configurable)
  - results_per_page: 50
"""

import time
from typing import Any

import requests

from ingestion.base_collector import BaseCollector
from pipeline.config import ADZUNA_APP_ID, ADZUNA_APP_KEY, RunManifest, load_source_config


class AdzunaCollector(BaseCollector):
    """Collect UK jobs from Adzuna API (api.adzuna.com/v1/api/jobs/gb/search)."""

    source_name = "adzuna_uk"

    def __init__(self, manifest: RunManifest):
        super().__init__(manifest)
        cfg = load_source_config().get("sources", {}).get("adzuna_uk", {})
        self.api_base: str = cfg.get("api_base", "https://api.adzuna.com/v1/api/jobs/gb/search")
        self.max_results_per_page: int = cfg.get("max_results_per_page", 50)
        self.max_pages: int = cfg.get("max_pages", 20)
        self.rate_limit_per_second: float = cfg.get("rate_limit_per_second", 2)
        self.search_terms: list[str] = cfg.get("search_terms", ["data analyst"])
        self.location: str = cfg.get("location", "london")

    def collect(self) -> None:
        self.logger.info(
            f"Adzuna collect: {len(self.search_terms)} terms, "
            f"location={self.location}, max_pages={self.max_pages}"
        )
        all_records: list[dict[str, Any]] = []
        interval = 1.0 / self.rate_limit_per_second

        for term in self.search_terms:
            self.logger.info(f"  Fetching: '{term}'")
            for page in range(1, self.max_pages + 1):
                records = self._fetch_page(term, page)
                if not records:
                    break
                all_records.extend(records)
                self.manifest.increment("records_read", len(records))
                time.sleep(interval)

        if all_records:
            self._save_raw(all_records, tag="uk")
            self.manifest.records_accepted = len(all_records)
            self.logger.info(f"Adzuna collected {len(all_records)} jobs total")
        else:
            self.logger.warning("Adzuna returned 0 jobs")
            self.manifest.add_error("adzuna", "No jobs returned for any search term")

    def _fetch_page(self, what: str, page: int) -> list[dict[str, Any]]:
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "results_per_page": self.max_results_per_page,
            "what": what,
            "where": self.location,
            "content-type": "application/json",
        }
        url = f"{self.api_base}/{page}"
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            self.logger.debug(f"    Page {page}: {len(results)} results")
            return [self._normalize(r) for r in results]
        except requests.RequestException as exc:
            self.manifest.add_error("adzuna", f"Request failed page={page} term='{what}'", str(exc))
            return []

    @staticmethod
    def _normalize(result: dict[str, Any]) -> dict[str, Any]:
        """Map Adzuna API response fields to canonical schema."""
        loc = result.get("location", {})
        display_name = loc.get("display_name", "") if isinstance(loc, dict) else str(loc)
        salary_min = result.get("salary_min")
        salary_max = result.get("salary_max")

        # Normalize work_mode
        description_lower = (result.get("description") or "").lower()
        if "remote" in description_lower:
            work_mode = "remote"
        elif "hybrid" in description_lower:
            work_mode = "hybrid"
        else:
            work_mode = "on_site"

        # Normalize employment_type
        contract_type = result.get("contract_type", "")
        emp_type_map = {
            "permanent": "permanent",
            "contract": "contract",
            "temporary": "temporary",
            "part_time": "part_time",
            "full_time": "full_time",
        }
        employment_type = emp_type_map.get(contract_type, contract_type)

        # Clean posting_date
        created = result.get("created")
        posting_date = None
        if created:
            posting_date = str(created)[:10] if isinstance(created, str) else None

        # Extract company name safely
        company_raw = result.get("company", "")
        company_name = (
            company_raw.get("display_name", "")
            if isinstance(company_raw, dict)
            else str(company_raw)
        )

        # Extract city safely
        city = (
            loc.get("area", [""])[-1]
            if isinstance(loc, dict) and loc.get("area")
            else display_name.split(",")[0].strip()
        )
        region = (
            loc.get("area", [""])[0]
            if isinstance(loc, dict) and loc.get("area")
            else ""
        )

        # Extract industry safely
        cat_raw = result.get("category", {})
        industry = (
            cat_raw.get("label", "")
            if isinstance(cat_raw, dict)
            else ""
        )

        return {
            "source_job_id": str(result.get("adref", "")),
            "job_title": result.get("title", ""),
            "company_name": company_name,
            "location": display_name,
            "city": city,
            "region": region,
            "country": "gb",
            "salary_min": float(salary_min) if salary_min else None,
            "salary_max": float(salary_max) if salary_max else None,
            "salary_currency": "GBP",
            "salary_period": "annual",
            "employment_type": employment_type,
            "work_mode": work_mode,
            "experience_level": None,
            "industry": industry,
            "education_requirement": None,
            "description": result.get("description", ""),
            "posting_date": posting_date,
            "closing_date": None,
            "job_url": result.get("redirect_url", ""),
            "collected_at": None,
        }
