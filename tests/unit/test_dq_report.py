from __future__ import annotations

import json

import pytest
from src.validation.dq_report import DQReport


@pytest.fixture
def report():
    return DQReport()


@pytest.fixture
def populated_report():
    r = DQReport()
    issue_a = [
        {"field": "job_title", "check": "required",
         "severity": "critical", "message": "missing"},
    ]
    issue_b = [
        {"field": "salary_min", "check": "salary_negative",
         "severity": "major", "message": "neg"},
    ]
    r.add_record_result("rec_001", issue_a, 60.0)
    r.add_record_result("rec_002", [], 100.0)
    r.add_record_result("rec_003", issue_b, 85.0)
    return r


class TestAddRecordResult:
    def test_stores_result(self, report):
        issue = [
            {"field": "x", "severity": "minor",
             "check": "c", "message": "m"},
        ]
        report.add_record_result("r1", issue, 97.0)
        assert "r1" in report.records
        assert report.records["r1"]["score"] == 97.0
        assert report.records["r1"]["issue_count"] == 1

    def test_empty_issues(self, report):
        report.add_record_result("r2", [], 100.0)
        assert report.records["r2"]["issue_count"] == 0


class TestGenerateSummary:
    def test_summary_fields(self, populated_report):
        summary = populated_report.generate_summary(
            total=3,
            valid=1,
            invalid=2,
            flagged=0,
            duplicates=0,
            by_severity_count={"critical": 1, "major": 1},
            by_check_count={"required": 1, "salary_negative": 1},
        )
        assert summary["total_records"] == 3
        assert summary["valid_records"] == 1
        assert summary["pass_rate"] == pytest.approx(33.33, abs=0.01)
        assert summary["avg_score"] == pytest.approx(81.67, abs=0.01)

    def test_empty_records_zero_pass_rate(self, report):
        summary = report.generate_summary(
            total=0, valid=0, invalid=0, flagged=0, duplicates=0,
            by_severity_count={}, by_check_count={},
        )
        assert summary["pass_rate"] == 0.0
        assert summary["avg_score"] == 0.0


class TestSaveJsonCreatesFile:
    def test_creates_valid_json(self, populated_report, tmp_path):
        populated_report.generate_summary(
            total=3, valid=1, invalid=2, flagged=0, duplicates=0,
            by_severity_count={"critical": 1}, by_check_count={"required": 1},
        )
        out = tmp_path / "report.json"
        populated_report.save_json(out)
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "summary" in data
        assert "records" in data
        assert len(data["records"]) == 3


class TestSaveMarkdownCreatesFile:
    def test_creates_valid_markdown(self, populated_report, tmp_path):
        populated_report.generate_summary(
            total=3, valid=1, invalid=2, flagged=0, duplicates=0,
            by_severity_count={"critical": 1}, by_check_count={"required": 1},
        )
        out = tmp_path / "report.md"
        populated_report.save_markdown(out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "# Data Quality Report" in content
        assert "Total records" in content
        assert "rec_001" in content
