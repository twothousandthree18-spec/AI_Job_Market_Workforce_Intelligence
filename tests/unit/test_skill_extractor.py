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


class TestRFalsePositivePrevention:
    """Tests that R programming language is not falsely detected in general English text."""

    def test_r_not_in_randd(self, extractor):
        results = extractor.extract_from_text("The R&D department is hiring")
        norm_names = [r["normalized_skill"] for r in results]
        assert "R" not in norm_names

    def test_r_not_in_ampersand(self, extractor):
        results = extractor.extract_from_text("From A&R to finance, legal to digital")
        norm_names = [r["normalized_skill"] for r in results]
        assert "R" not in norm_names

    def test_r_not_in_regular_sentences(self, extractor):
        text = "The candidate will be responsible for managing the team and reporting results."
        results = extractor.extract_from_text(text)
        norm_names = [r["normalized_skill"] for r in results]
        assert "R" not in norm_names

    def test_r_not_in_role_context(self, extractor):
        results = extractor.extract_from_text("This role requires strong analytical skills")
        norm_names = [r["normalized_skill"] for r in results]
        assert "R" not in norm_names

    def test_r_detected_in_programming_context(self, extractor):
        results = extractor.extract_from_text(
            "Experience in R programming and Python"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "R" in norm_names

    def test_r_detected_with_other_languages(self, extractor):
        results = extractor.extract_from_text(
            "Required: Python, R, SQL for data analysis"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "R" in norm_names

    def test_r_detected_with_explicit_context(self, extractor):
        results = extractor.extract_from_text(
            "coding (e.g., Python, R, SQL), querying databases"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "R" in norm_names

    def test_r_high_confidence_when_explicit(self, extractor):
        results = extractor.extract_from_text(
            "Experience in R programming and Python"
        )
        r_skill = next(r for r in results if r["normalized_skill"] == "R")
        assert r_skill["confidence"] == "high"


class TestGoFalsePositivePrevention:
    """Tests that Go programming language is not falsely detected in general English text."""

    def test_go_not_in_go_to(self, extractor):
        results = extractor.extract_from_text(
            "The candidate will go to the office daily"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "Go" not in norm_names

    def test_go_not_in_go_through(self, extractor):
        results = extractor.extract_from_text(
            "BPSS but will go through SC when in post"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "Go" not in norm_names

    def test_go_not_in_going(self, extractor):
        results = extractor.extract_from_text("We are going to implement new processes")
        norm_names = [r["normalized_skill"] for r in results]
        assert "Go" not in norm_names

    def test_go_not_in_go_to_person(self, extractor):
        results = extractor.extract_from_text(
            "The successful candidate will become the go-to person"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "Go" not in norm_names

    def test_go_detected_in_programming_context(self, extractor):
        results = extractor.extract_from_text(
            "Go programming experience required for backend services"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "Go" in norm_names

    def test_go_detected_with_golang(self, extractor):
        results = extractor.extract_from_text("Golang microservices development")
        norm_names = [r["normalized_skill"] for r in results]
        assert "Go" in norm_names


class TestScalaFalsePositivePrevention:
    """Tests that Scala programming language is not falsely detected."""

    def test_scala_not_in_scalable(self, extractor):
        results = extractor.extract_from_text(
            "Build scalable data pipelines using modern tools"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "Scala" not in norm_names

    def test_scala_not_in_scalability(self, extractor):
        results = extractor.extract_from_text(
            "Ensure the scalability of our data infrastructure"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "Scala" not in norm_names

    def test_scala_detected_in_programming_context(self, extractor):
        results = extractor.extract_from_text(
            "Scala and Spark for big data processing"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "Scala" in norm_names


class TestSASFalsePositivePrevention:
    """Tests that SAS tool is not falsely detected in unrelated text."""

    def test_sas_not_in_disaster(self, extractor):
        results = extractor.extract_from_text(
            "Business continuity and disaster recovery planning"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "SAS" not in norm_names

    def test_sas_detected_in_tool_context(self, extractor):
        results = extractor.extract_from_text(
            "SAS Viya experience preferred for statistical analysis"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "SAS" in norm_names


class TestCSharpDetection:
    """Tests that C# is properly detected."""

    def test_csharp_with_dotnet(self, extractor):
        results = extractor.extract_from_text(
            "C# and .NET developer with ASP.NET experience"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "C#" in norm_names

    def test_csharp_standalone(self, extractor):
        results = extractor.extract_from_text(
            "Proficiency in C# programming language"
        )
        norm_names = [r["normalized_skill"] for r in results]
        assert "C#" in norm_names


class TestProvenance:
    """Tests that skill extraction includes proper provenance metadata."""

    def test_has_confidence_field(self, extractor):
        results = extractor.extract_from_text("Python programming")
        assert len(results) > 0
        assert "confidence" in results[0]

    def test_has_source_field(self, extractor):
        record = {
            "job_title": "Data Analyst",
            "description": "Must know Python.",
        }
        results = extractor.extract_from_record(record)
        assert len(results) > 0
        assert "source_field" in results[0]
        assert results[0]["source_field"] in ("job_title", "description", "education_requirement")

    def test_has_context_field(self, extractor):
        results = extractor.extract_from_text(
            "We need a Python developer for our team"
        )
        assert len(results) > 0
        assert "context" in results[0]
        assert len(results[0]["context"]) > 0

    def test_has_method_field(self, extractor):
        results = extractor.extract_from_text("Python programming")
        assert len(results) > 0
        assert results[0]["method"] in ("lexicon", "regex")
