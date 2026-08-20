from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from src.normalization.location_normalizer import LocationNormalizer
from src.normalization.salary_normalizer import SalaryNormalizer
from src.normalization.title_normalizer import TitleNormalizer

TITLE_MAP = Path(__file__).resolve().parents[2] / "configs" / "title_map.yaml"


# ---------------------------------------------------------------------------
# TitleNormalizer
# ---------------------------------------------------------------------------

@pytest.fixture
def title_norm():
    return TitleNormalizer(title_map_path=TITLE_MAP)


class TestNormalizeExactMatch:
    def test_data_analyst(self, title_norm):
        result = title_norm.normalize("data analyst")
        assert result["role_category"] == "data_analyst"


class TestNormalizeSeniorityJunior:
    def test_junior_data_analyst(self, title_norm):
        result = title_norm.normalize("Junior Data Analyst")
        assert result["seniority"] == "junior"


class TestNormalizeSenioritySenior:
    def test_senior_data_scientist(self, title_norm):
        result = title_norm.normalize("Senior Data Scientist")
        assert result["seniority"] == "senior"


class TestNormalizeUnknownTitle:
    def test_random_title(self, title_norm):
        result = title_norm.normalize("Random Title")
        assert result["role_category"] == "other"


class TestNormalizeBatch:
    def test_adds_columns(self, title_norm):
        df = pd.DataFrame({"job_title": ["data analyst", "senior data scientist"]})
        result = title_norm.normalize_batch(df)
        assert "normalized_title" in result.columns
        assert "role_category" in result.columns
        assert "seniority" in result.columns
        assert result.loc[0, "role_category"] == "data_analyst"
        assert result.loc[1, "seniority"] == "senior"


# ---------------------------------------------------------------------------
# LocationNormalizer
# ---------------------------------------------------------------------------

@pytest.fixture
def loc_norm():
    return LocationNormalizer()


class TestNormalizeCountryPk:
    def test_pk_uppercase(self, loc_norm):
        assert loc_norm.normalize_country("pk") == "PK"

    def test_country_name(self, loc_norm):
        assert loc_norm.normalize_country_name("pk") == "Pakistan"


class TestNormalizeCityKarachi:
    def test_karachi(self, loc_norm):
        assert loc_norm.normalize_city("karachi", "pk") == "Karachi"


class TestNormalizeCityUnknown:
    def test_unknown_city_title_cased(self, loc_norm):
        result = loc_norm.normalize_city("unknown city", "pk")
        assert result == "Unknown City"


# ---------------------------------------------------------------------------
# SalaryNormalizer
# ---------------------------------------------------------------------------

@pytest.fixture
def sal_norm():
    return SalaryNormalizer()


class TestSalaryMinMaxSwap:
    def test_min_greater_than_max(self, sal_norm):
        record = {"salary_min": 100000, "salary_max": 50000}
        result = sal_norm.normalize_record(record)
        assert result["salary_min"] == 50000
        assert result["salary_max"] == 100000


class TestSalaryCurrencyUppercase:
    def test_lowercase_to_uppercase(self, sal_norm):
        record = {"salary_currency": "pkr"}
        result = sal_norm.normalize_record(record)
        assert result["salary_currency"] == "PKR"


class TestSalaryPeriodLowercase:
    def test_mixed_case_to_lower(self, sal_norm):
        record = {"salary_period": "Monthly"}
        result = sal_norm.normalize_record(record)
        assert result["salary_period"] == "monthly"


class TestSalaryBandPkrLow:
    def test_below_50000(self, sal_norm):
        df = pd.DataFrame({
            "salary_min": [30000],
            "salary_max": [40000],
            "salary_currency": ["PKR"],
            "salary_period": ["monthly"],
            "country": ["Pakistan"],
        })
        result = sal_norm.normalize_batch(df)
        assert result.loc[0, "salary_band"] == "low"


class TestSalaryBandPkrMid:
    def test_50000_to_100000(self, sal_norm):
        df = pd.DataFrame({
            "salary_min": [60000],
            "salary_max": [80000],
            "salary_currency": ["PKR"],
            "salary_period": ["monthly"],
            "country": ["Pakistan"],
        })
        result = sal_norm.normalize_batch(df)
        assert result.loc[0, "salary_band"] == "mid"


class TestSalaryBandPkrHigh:
    def test_above_100000(self, sal_norm):
        df = pd.DataFrame({
            "salary_min": [120000],
            "salary_max": [150000],
            "salary_currency": ["PKR"],
            "salary_period": ["monthly"],
            "country": ["Pakistan"],
        })
        result = sal_norm.normalize_batch(df)
        assert result.loc[0, "salary_band"] == "high"
