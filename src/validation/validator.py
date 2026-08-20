from __future__ import annotations

from datetime import date, datetime
from typing import Any

REQUIRED_FIELDS = ("source", "source_job_id", "job_title", "company_name", "country", "description")

KNOWN_CURRENCIES = {"PKR", "GBP", "USD", "EUR", "INR"}
KNOWN_PERIODS = {"annual", "monthly", "hourly"}

SEVERITY_WEIGHTS = {"critical": -40, "major": -15, "minor": -3}

MIN_DESCRIPTION_LEN = 20
MIN_TITLE_LEN = 2
MIN_DATE = date(2020, 1, 1)


class RecordValidator:
    """Validates a single job-posting record and computes a DQ score."""

    def validate(self, record: dict[str, Any]) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []
        self._check_required(record, issues)
        self._check_dates(record, issues)
        self._check_salary(record, issues)
        self._check_text_quality(record, issues)
        self._check_urls(record, issues)
        return issues

    def score_record(self, record: dict[str, Any]) -> float:
        issues = self.validate(record)
        penalty = sum(SEVERITY_WEIGHTS[i["severity"]] for i in issues)
        return max(0.0, min(100.0, 100.0 + penalty))

    # ------------------------------------------------------------------
    # Internal checks
    # ------------------------------------------------------------------

    def _check_required(self, record: dict[str, Any], issues: list[dict[str, str]]) -> None:
        for field in REQUIRED_FIELDS:
            value = record.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append({
                    "field": field,
                    "check": "required",
                    "severity": "critical",
                    "message": f"Field '{field}' is missing or empty",
                })

    def _check_dates(self, record: dict[str, Any], issues: list[dict[str, str]]) -> None:
        posting = record.get("posting_date")
        if posting is not None:
            parsed = self._parse_date(posting)
            if parsed is None:
                issues.append({
                    "field": "posting_date",
                    "check": "date_parse",
                    "severity": "major",
                    "message": f"Cannot parse posting_date: {posting!r}",
                })
            else:
                today = date.today()
                if parsed > today:
                    issues.append({
                        "field": "posting_date",
                        "check": "date_future",
                        "severity": "major",
                        "message": f"posting_date {parsed} is in the future",
                    })
                if parsed < MIN_DATE:
                    issues.append({
                        "field": "posting_date",
                        "check": "date_too_old",
                        "severity": "minor",
                        "message": f"posting_date {parsed} is before {MIN_DATE}",
                    })

        closing = record.get("closing_date")
        if closing is not None:
            parsed = self._parse_date(closing)
            if parsed is None:
                issues.append({
                    "field": "closing_date",
                    "check": "date_parse",
                    "severity": "major",
                    "message": f"Cannot parse closing_date: {closing!r}",
                })

    def _check_salary(self, record: dict[str, Any], issues: list[dict[str, str]]) -> None:
        sal_min = record.get("salary_min")
        sal_max = record.get("salary_max")

        for label, value in [("salary_min", sal_min), ("salary_max", sal_max)]:
            if value is not None:
                if not isinstance(value, (int, float)):
                    issues.append({
                        "field": label,
                        "check": "salary_type",
                        "severity": "major",
                        "message": f"{label} must be a number, got {type(value).__name__}",
                    })
                elif value < 0:
                    issues.append({
                        "field": label,
                        "check": "salary_negative",
                        "severity": "major",
                        "message": f"{label} is negative: {value}",
                    })

        if (
            sal_min is not None
            and sal_max is not None
            and isinstance(sal_min, (int, float))
            and isinstance(sal_max, (int, float))
            and sal_min > sal_max
        ):
            issues.append({
                "field": "salary_min",
                "check": "salary_range",
                "severity": "major",
                "message": f"salary_min ({sal_min}) > salary_max ({sal_max})",
            })

        currency = record.get("salary_currency")
        if currency is not None and currency not in KNOWN_CURRENCIES:
            issues.append({
                "field": "salary_currency",
                "check": "currency_known",
                "severity": "minor",
                "message": f"Unknown salary currency: {currency}",
            })

        period = record.get("salary_period")
        if period is not None and period not in KNOWN_PERIODS:
            issues.append({
                "field": "salary_period",
                "check": "period_known",
                "severity": "minor",
                "message": f"Unknown salary period: {period}",
            })

    def _check_text_quality(self, record: dict[str, Any], issues: list[dict[str, str]]) -> None:
        desc = record.get("description")
        if isinstance(desc, str) and len(desc.strip()) < MIN_DESCRIPTION_LEN:
            issues.append({
                "field": "description",
                "check": "min_length",
                "severity": "major",
                "message": (
                    f"Description is only {len(desc.strip())} chars"
                    f" (min {MIN_DESCRIPTION_LEN})"
                ),
            })

        title = record.get("job_title")
        if isinstance(title, str) and len(title.strip()) < MIN_TITLE_LEN:
            issues.append({
                "field": "job_title",
                "check": "min_length",
                "severity": "major",
                "message": f"Job title is only {len(title.strip())} chars (min {MIN_TITLE_LEN})",
            })

    def _check_urls(self, record: dict[str, Any], issues: list[dict[str, str]]) -> None:
        url = record.get("job_url")
        if (
            url is not None
            and isinstance(url, str)
            and url.strip()
            and not url.startswith(("http://", "https://"))
        ):
            issues.append({
                "field": "job_url",
                "check": "url_scheme",
                "severity": "minor",
                    "message": f"job_url does not start with http(s)://: {url[:80]}",
                })

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except ValueError:
                    continue
        return None
