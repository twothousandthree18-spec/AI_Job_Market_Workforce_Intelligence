from __future__ import annotations

from pathlib import Path

import pytest
from src.nlp.skill_extractor import SkillExtractor

LEXICON = Path(__file__).resolve().parents[2] / "configs" / "skill_lexicon.yaml"


@pytest.fixture
def extractor():
    return SkillExtractor(lexicon_path=LEXICON)


class TestExtractPython:
    def test_python_programming(self, extractor):
        results = extractor.extract_from_text("Python programming is required")
        norm_names = [r["normalized_skill"] for r in results]
        assert "Python" in norm_names
        py = next(r for r in results if r["normalized_skill"] == "Python")
        assert py["category"] == "technical"


class TestExtractSql:
    def test_sql_databases(self, extractor):
        results = extractor.extract_from_text("SQL databases are used")
        norm_names = [r["normalized_skill"] for r in results]
        assert "SQL" in norm_names


class TestExtractPowerBi:
    def test_power_bi(self, extractor):
        results = extractor.extract_from_text("Power BI dashboards")
        norm_names = [r["normalized_skill"] for r in results]
        assert "Power BI" in norm_names
        pbi = next(r for r in results if r["normalized_skill"] == "Power BI")
        assert pbi["category"] == "tool"


class TestExtractMultipleSkills:
    def test_python_and_sql(self, extractor):
        results = extractor.extract_from_text(
            "We need Python and SQL for data analysis"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "Python" in norm_names
        assert "SQL" in norm_names


class TestExtractFromRecord:
    def test_uses_title_and_description(self, extractor):
        record = {
            "job_title": "Data Analyst",
            "description": "Must know Python and SQL databases.",
        }
        results = extractor.extract_from_record(record)
        norm_names = [r["normalized_skill"] for r in results]
        assert "Python" in norm_names
        assert "SQL" in norm_names


class TestDeduplication:
    def test_same_skill_once(self, extractor):
        results = extractor.extract_from_text(
            "Python is needed. You should know Python well."
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert norm_names.count("Python") == 1


class TestEmptyText:
    def test_empty_string(self, extractor):
        assert extractor.extract_from_text("") == []


class TestUnknownTextNoMatch:
    def test_no_skills(self, extractor):
        results = extractor.extract_from_text("A quick fox jumps high and the lazy dog sleeps.")
        assert results == []
