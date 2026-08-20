from __future__ import annotations

import pytest
from src.validation.validator import RecordValidator


@pytest.fixture
def validator():
    return RecordValidator()


@pytest.fixture
def valid_record():
    return {
        "source": "linkedin",
        "source_job_id": "12345",
        "job_title": "Data Analyst",
        "company_name": "Acme Corp",
        "country": "Pakistan",
        "description": "We are looking for a skilled data analyst to join our team.",
        "posting_date": "2024-06-15",
    }


class TestValidRecordPasses:
    def test_zero_issues(self, validator, valid_record):
        issues = validator.validate(valid_record)
        assert issues == []

    def test_score_100(self, validator, valid_record):
        score = validator.score_record(valid_record)
        assert score == 100.0


class TestMissingRequiredField:
    def test_missing_job_title(self, validator, valid_record):
        del valid_record["job_title"]
        issues = validator.validate(valid_record)
        critical = [i for i in issues if i["field"] == "job_title" and i["severity"] == "critical"]
        assert len(critical) == 1

    def test_empty_job_title(self, validator, valid_record):
        valid_record["job_title"] = "   "
        issues = validator.validate(valid_record)
        critical = [i for i in issues if i["field"] == "job_title" and i["severity"] == "critical"]
        assert len(critical) == 1


class TestEmptyDescription:
    def test_empty_string(self, validator, valid_record):
        valid_record["description"] = ""
        issues = validator.validate(valid_record)
        desc_issues = [
            i for i in issues
            if i["field"] == "description" and i["severity"] == "critical"
        ]
        assert len(desc_issues) == 1

    def test_none_description(self, validator, valid_record):
        valid_record["description"] = None
        issues = validator.validate(valid_record)
        desc_issues = [
            i for i in issues
            if i["field"] == "description" and i["severity"] == "critical"
        ]
        assert len(desc_issues) == 1


class TestShortDescription:
    def test_below_minimum(self, validator, valid_record):
        valid_record["description"] = "short"
        issues = validator.validate(valid_record)
        desc_issues = [
            i for i in issues
            if i["field"] == "description" and i["check"] == "min_length"
        ]
        assert len(desc_issues) == 1
        assert desc_issues[0]["severity"] == "major"


class TestShortTitle:
    def test_single_char(self, validator, valid_record):
        valid_record["job_title"] = "X"
        issues = validator.validate(valid_record)
        title_issues = [
            i for i in issues
            if i["field"] == "job_title" and i["check"] == "min_length"
        ]
        assert len(title_issues) == 1
        assert title_issues[0]["severity"] == "major"


class TestFutureDate:
    def test_future_posting_date(self, validator, valid_record):
        valid_record["posting_date"] = "2099-01-01"
        issues = validator.validate(valid_record)
        future = [i for i in issues if i["check"] == "date_future"]
        assert len(future) == 1
        assert future[0]["severity"] == "major"


class TestOldDate:
    def test_before_2020(self, validator, valid_record):
        valid_record["posting_date"] = "2019-06-15"
        issues = validator.validate(valid_record)
        old = [i for i in issues if i["check"] == "date_too_old"]
        assert len(old) == 1
        assert old[0]["severity"] == "minor"


class TestNegativeSalary:
    def test_negative_min(self, validator, valid_record):
        valid_record["salary_min"] = -5000
        issues = validator.validate(valid_record)
        neg = [i for i in issues if i["check"] == "salary_negative"]
        assert len(neg) == 1
        assert neg[0]["severity"] == "major"


class TestSalaryMinGreaterThanMax:
    def test_inverted_range(self, validator, valid_record):
        valid_record["salary_min"] = 100000
        valid_record["salary_max"] = 50000
        issues = validator.validate(valid_record)
        range_issues = [i for i in issues if i["check"] == "salary_range"]
        assert len(range_issues) == 1
        assert range_issues[0]["severity"] == "major"


class TestUnknownCurrency:
    def test_unknown_currency(self, validator, valid_record):
        valid_record["salary_currency"] = "XYZ"
        issues = validator.validate(valid_record)
        curr = [i for i in issues if i["check"] == "currency_known"]
        assert len(curr) == 1
        assert curr[0]["severity"] == "minor"


class TestUnknownPeriod:
    def test_unknown_period(self, validator, valid_record):
        valid_record["salary_period"] = "weekly"
        issues = validator.validate(valid_record)
        period = [i for i in issues if i["check"] == "period_known"]
        assert len(period) == 1
        assert period[0]["severity"] == "minor"


class TestInvalidUrl:
    def test_missing_scheme(self, validator, valid_record):
        valid_record["job_url"] = "www.example.com/job"
        issues = validator.validate(valid_record)
        url_issues = [i for i in issues if i["check"] == "url_scheme"]
        assert len(url_issues) == 1
        assert url_issues[0]["severity"] == "minor"


class TestScoreDecreasesWithIssues:
    def test_more_issues_lower_score(self, validator, valid_record):
        score_clean = validator.score_record(valid_record)

        valid_record["job_url"] = "ftp://bad-url"
        valid_record["salary_currency"] = "ZZZ"
        score_dirty = validator.score_record(valid_record)

        assert score_dirty < score_clean


class TestScoreNeverNegative:
    def test_score_floors_at_zero(self, validator):
        record = {
            "source": "",
            "source_job_id": "",
            "job_title": "",
            "company_name": "",
            "country": "",
            "description": "",
            "salary_min": -1,
            "salary_max": -2,
            "salary_currency": "ZZZ",
            "salary_period": "weekly",
            "job_url": "ftp://bad",
            "posting_date": "2099-12-31",
        }
        score = validator.score_record(record)
        assert score >= 0.0
