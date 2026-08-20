from __future__ import annotations

import pandas as pd
import pytest
from src.validation.duplicate_detector import DuplicateDetector


@pytest.fixture
def detector():
    return DuplicateDetector()


class TestDetectExactDuplicates:
    def test_same_source_and_id(self, detector):
        df = pd.DataFrame({
            "source": ["linkedin", "linkedin", "indeed"],
            "source_job_id": ["abc", "abc", "xyz"],
            "job_title": ["Dev", "Dev", "Dev"],
        })
        dups = detector.detect_exact(df)
        assert len(dups) == 1
        key = "linkedin::abc"
        assert key in dups
        assert len(dups[key]) == 2

    def test_no_exact_duplicates(self, detector):
        df = pd.DataFrame({
            "source": ["linkedin", "indeed"],
            "source_job_id": ["abc", "def"],
            "job_title": ["Dev", "Dev"],
        })
        dups = detector.detect_exact(df)
        assert dups == {}


class TestDetectUrlDuplicates:
    def test_same_url_detected(self, detector):
        df = pd.DataFrame({
            "source": ["a", "b"],
            "source_job_id": ["1", "2"],
            "job_url": ["https://example.com/job", "https://example.com/job"],
        })
        dups = detector.detect_url_duplicates(df)
        assert len(dups) == 1
        assert len(dups["https://example.com/job"]) == 2

    def test_different_urls_not_flagged(self, detector):
        df = pd.DataFrame({
            "source": ["a", "b"],
            "source_job_id": ["1", "2"],
            "job_url": ["https://a.com", "https://b.com"],
        })
        dups = detector.detect_url_duplicates(df)
        assert dups == {}


class TestDetectContentDuplicates:
    def test_similar_content_detected(self, detector):
        df = pd.DataFrame({
            "source": ["a", "b"],
            "source_job_id": ["1", "2"],
            "company_name": ["Acme Corp", "Acme Corp"],
            "job_title": ["Data Analyst", "Data Analyst"],
            "city": ["Karachi", "Karachi"],
        })
        pairs = detector.detect_content_duplicates(df, threshold=85)
        assert len(pairs) >= 1
        assert pairs[0][2] >= 85.0

    def test_different_content_not_flagged(self, detector):
        df = pd.DataFrame({
            "source": ["a", "b"],
            "source_job_id": ["1", "2"],
            "company_name": ["Acme Corp", "Totally Different Inc"],
            "job_title": ["Data Analyst", "Senior Software Engineer"],
            "city": ["Karachi", "London"],
        })
        pairs = detector.detect_content_duplicates(df, threshold=85)
        assert pairs == []


class TestMarkDuplicatesAddsColumns:
    def test_columns_added(self, detector):
        df = pd.DataFrame({
            "source": ["linkedin", "linkedin", "indeed"],
            "source_job_id": ["1", "1", "2"],
            "job_title": ["Dev", "Dev", "Dev"],
            "company_name": ["Acme", "Acme", "Beta"],
            "city": ["Karachi", "Karachi", "Lahore"],
        })
        result = detector.mark_duplicates(df)
        assert "is_duplicate" in result.columns
        assert "dup_group" in result.columns
        assert "dup_reason" in result.columns

    def test_exact_dups_marked(self, detector):
        df = pd.DataFrame({
            "source": ["linkedin", "linkedin", "indeed"],
            "source_job_id": ["1", "1", "2"],
            "job_title": ["Dev", "Dev", "Dev"],
            "company_name": ["Acme", "Acme", "Beta"],
            "city": ["Karachi", "Karachi", "Lahore"],
        })
        result = detector.mark_duplicates(df)
        assert result.loc[0, "is_duplicate"] == True  # noqa: E712
        assert result.loc[1, "is_duplicate"] == True  # noqa: E712
        assert result.loc[0, "dup_reason"] == "exact_source_id"
        assert result.loc[2, "is_duplicate"] == False  # noqa: E712
