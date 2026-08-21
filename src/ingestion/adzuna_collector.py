"""
Adzuna UK collector — fetches jobs from the Adzuna API (gb search).

Requires ADZUNA_APP_ID and ADZUNA_APP_KEY in .env.

Features:
  - configurable page size, max pages, max records per query
  - retry with exponential backoff
  - rate-limit compliance (configurable requests/second)
  - request timeout handling
  - graceful error handling per page/query
  - search query logging in ingestion metadata
"""

from __future__ import annotations

import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ingestion.base_collector import BaseCollector
from pipeline.config import (
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    RunManifest,
    load_source_config,
)


class AdzunaCollector(BaseCollector):
    """Collect UK jobs from Adzuna API (api.adzuna.com/v1/api/jobs/gb/search)."""

    source_name = "adzuna_uk"

    def __init__(self, manifest: RunManifest) -> None:
        super().__init__(manifest)
        cfg = load_source_config().get("sources", {}).get("adzuna_uk", {})
        self.api_base: str = cfg.get(
            "api_base", "https://api.adzuna.com/v1/api/jobs/gb/search"
        )
        self.max_results_per_page: int = cfg.get("max_results_per_page", 50)
        self.max_pages: int = cfg.get("max_pages", 20)
        self.max_records: int = cfg.get("max_records", 5000)
        self.rate_limit_per_second: float = cfg.get("rate_limit_per_second", 2)
        self.request_timeout: int = cfg.get("request_timeout", 30)
        self.retry_count: int = cfg.get("retry_count", 3)
        self.search_terms: list[str] = cfg.get("search_terms", ["data analyst"])
        self.location: str = cfg.get("location", "london")

        self._session = self._build_session()
        self._total_fetched = 0

    def _build_session(self) -> requests.Session:
        """Build a requests session with retry strategy."""
        session = requests.Session()
        retry = Retry(
            total=self.retry_count,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def collect(self) -> None:
        if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
            self.logger.warning(
                "Skipping Adzuna: ADZUNA_APP_ID/ADZUNA_APP_KEY not set in .env"
            )
            self.manifest.add_error(
                "adzuna", "API credentials not configured"
            )
            return

        self.logger.info(
            f"Adzuna collect: {len(self.search_terms)} terms, "
            f"location={self.location}, max_pages={self.max_pages}, "
            f"max_records={self.max_records}"
        )
        all_records: list[dict[str, Any]] = []
        interval = 1.0 / self.rate_limit_per_second

        for term in self.search_terms:
            if self._total_fetched >= self.max_records:
                self.logger.info(
                    f"Reached max_records limit ({self.max_records}), "
                    "stopping collection"
                )
                break

            self.logger.info(f"  Fetching: '{term}'")
            term_records = 0

            for page in range(1, self.max_pages + 1):
                if self._total_fetched >= self.max_records:
                    break

                records = self._fetch_page(term, page)
                if not records:
                    self.logger.info(
                        f"    Page {page}: empty, moving to next term"
                    )
                    break

                all_records.extend(records)
                term_records += len(records)
                self._total_fetched += len(records)
                self.manifest.increment("records_read", len(records))

                self.logger.info(
                    f"    Page {page}: {len(records)} results "
                    f"(term total: {term_records}, "
                    f"grand total: {self._total_fetched})"
                )

                time.sleep(interval)

            self.logger.info(
                f"  Term '{term}': {term_records} records collected"
            )

        if all_records:
            self._save_raw(all_records, tag="uk")
            self.manifest.records_accepted = len(all_records)
            self.logger.info(
                f"Adzuna collected {len(all_records)} jobs total"
            )
        else:
            self.logger.warning("Adzuna returned 0 jobs")
            self.manifest.add_error(
                "adzuna", "No jobs returned for any search term"
            )

    def _fetch_page(self, what: str, page: int) -> list[dict[str, Any]]:
        """Fetch a single page with timeout and error handling."""
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
            resp = self._session.get(
                url, params=params, timeout=self.request_timeout
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                self.logger.warning(
                    f"    Rate limited, waiting {retry_after}s..."
                )
                time.sleep(retry_after)
                return []

            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            return [self._normalize(r) for r in results]

        except requests.Timeout:
            self.manifest.add_error(
                "adzuna",
                f"Timeout on page {page} term='{what}'",
            )
            return []
        except requests.RequestException as exc:
            self.manifest.add_error(
                "adzuna",
                f"Request failed page={page} term='{what}'",
                str(exc),
            )
            return []

    @staticmethod
    def _normalize(result: dict[str, Any]) -> dict[str, Any]:
        """Map Adzuna API response fields to canonical schema."""
        loc = result.get("location", {})
        display_name = (
            loc.get("display_name", "") if isinstance(loc, dict) else str(loc)
        )
        salary_min = result.get("salary_min")
        salary_max = result.get("salary_max")

        description_lower = (result.get("description") or "").lower()
        if "remote" in description_lower:
            work_mode = "remote"
        elif "hybrid" in description_lower:
            work_mode = "hybrid"
        else:
            work_mode = "on_site"

        contract_type = result.get("contract_type", "")
        emp_type_map = {
            "permanent": "permanent",
            "contract": "contract",
            "temporary": "temporary",
            "part_time": "part_time",
            "full_time": "full_time",
        }
        employment_type = emp_type_map.get(contract_type, contract_type)

        created = result.get("created")
        posting_date = None
        if created:
            posting_date = (
                str(created)[:10] if isinstance(created, str) else None
            )

        company_raw = result.get("company", "")
        company_name = (
            company_raw.get("display_name", "")
            if isinstance(company_raw, dict)
            else str(company_raw)
        )

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

        cat_raw = result.get("category", {})
        industry = cat_raw.get("label", "") if isinstance(cat_raw, dict) else ""

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
