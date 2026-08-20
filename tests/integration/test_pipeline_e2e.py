from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from cleaning.text_cleaner import TextCleaner
from nlp.skill_extractor import SkillExtractor
from nlp.skill_normalizer import SkillNormalizer
from normalization.location_normalizer import LocationNormalizer
from normalization.salary_normalizer import SalaryNormalizer
from normalization.title_normalizer import TitleNormalizer
from validation.duplicate_detector import DuplicateDetector
from validation.validator import RecordValidator

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CSV = ROOT / "data" / "external" / "pakjobs_clean.csv"


def _load_sample_df() -> pd.DataFrame:
    df = pd.read_csv(SAMPLE_CSV, dtype=str, keep_default_na=False)
    df = df.rename(columns={
        "Job Title": "job_title",
        "Company": "company_name",
        "Location": "city",
        "Industry": "industry",
        "Salary": "salary_raw",
        "Job Description": "description",
        "Date Posted": "posting_date",
        "Experience Level": "experience_level",
        "Employment Type": "employment_type",
        "Education": "education_requirement",
    })
    df["source"] = "kaggle_rozee_pk"
    df["source_job_id"] = [f"test_{i}" for i in range(len(df))]
    df["location"] = df["city"]
    df["region"] = ""
    df["country"] = "PK"
    df["salary_min"] = None
    df["salary_max"] = None
    df["salary_currency"] = "PKR"
    df["salary_period"] = "monthly"
    df["work_mode"] = ""
    df["job_url"] = ""
    df["collected_at"] = "2026-08-19T20:31:17"
    return df


@pytest.fixture(scope="module")
def raw_df() -> pd.DataFrame:
    return _load_sample_df()


@pytest.fixture(scope="module")
def validated_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    validator = RecordValidator()
    detector = DuplicateDetector()
    df = detector.mark_duplicates(df)
    issues_list = []
    scores = []
    for _, row in df.iterrows():
        issues = validator.validate(row.to_dict())
        score = validator.score_record(row.to_dict())
        issues_list.append(issues)
        scores.append(score)
    df["dq_issues"] = issues_list
    df["dq_score"] = scores
    return df


@pytest.fixture(scope="module")
def cleaned_df(validated_df: pd.DataFrame) -> pd.DataFrame:
    cleaner = TextCleaner()
    records = []
    for _, row in validated_df.iterrows():
        records.append(cleaner.clean_all(row.to_dict()))
    return pd.DataFrame(records)


@pytest.fixture(scope="module")
def normalised_df(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    title_norm = TitleNormalizer()
    loc_norm = LocationNormalizer()
    sal_norm = SalaryNormalizer()
    df = title_norm.normalize_batch(cleaned_df)
    df = loc_norm.normalize_batch(df)
    df = sal_norm.normalize_batch(df)
    return df


@pytest.fixture(scope="module")
def skills_df(normalised_df: pd.DataFrame) -> pd.DataFrame:
    extractor = SkillExtractor()
    normaliser = SkillNormalizer()
    df = normalised_df.copy()
    skills_lists = []
    for _, row in df.iterrows():
        skills = extractor.extract_from_record(row.to_dict())
        skills = normaliser.normalize_batch(skills)
        skills_lists.append(skills)
    df["skills_list"] = skills_lists
    return df


class TestEndToEndPipeline:

    def test_sample_csv_exists(self):
        assert SAMPLE_CSV.exists(), f"Sample CSV not found at {SAMPLE_CSV}"

    def test_records_loaded(self, raw_df: pd.DataFrame):
        assert len(raw_df) >= 10, f"Expected >=10 records, got {len(raw_df)}"

    def test_all_records_have_titles(self, raw_df: pd.DataFrame):
        assert raw_df["job_title"].notna().all()
        assert (raw_df["job_title"] != "").all()

    def test_validation_adds_dq_columns(self, validated_df: pd.DataFrame):
        assert "dq_issues" in validated_df.columns
        assert "dq_score" in validated_df.columns
        assert validated_df["dq_score"].between(0, 100).all()

    def test_validation_scores_reasonable(self, validated_df: pd.DataFrame):
        avg_score = validated_df["dq_score"].mean()
        assert avg_score >= 50, f"Average DQ score too low: {avg_score:.1f}"

    def test_cleaning_adds_description_cleaned(self, cleaned_df: pd.DataFrame):
        assert "description_cleaned" in cleaned_df.columns
        assert cleaned_df["description_cleaned"].notna().all()

    def test_cleaning_removes_html(self, cleaned_df: pd.DataFrame):
        for desc in cleaned_df["description_cleaned"]:
            assert "<b>" not in str(desc)
            assert "</b>" not in str(desc)

    def test_title_normalisation_adds_columns(self, normalised_df: pd.DataFrame):
        assert "role_category" in normalised_df.columns
        assert "seniority" in normalised_df.columns

    def test_known_titles_normalised(self, normalised_df: pd.DataFrame):
        analyst_mask = normalised_df["job_title"].str.contains("Analyst", case=False)
        if analyst_mask.any():
            cats = normalised_df.loc[analyst_mask, "role_category"]
            assert cats.notna().all()

    def test_location_normalisation_adds_columns(self, normalised_df: pd.DataFrame):
        assert "country_code" in normalised_df.columns
        assert "country" in normalised_df.columns

    def test_salary_normalisation_adds_columns(self, normalised_df: pd.DataFrame):
        assert "salary_band" in normalised_df.columns

    def test_skill_extraction_adds_column(self, skills_df: pd.DataFrame):
        assert "skills_list" in skills_df.columns

    def test_skills_are_dicts(self, skills_df: pd.DataFrame):
        for skills in skills_df["skills_list"]:
            assert isinstance(skills, (list, tuple))
            for s in skills:
                assert isinstance(s, dict)
                assert "normalized_skill" in s
                assert "category" in s

    def test_skills_extracted(self, skills_df: pd.DataFrame):
        total_skills = sum(len(s) for s in skills_df["skills_list"])
        assert total_skills > 0, "No skills extracted from any record"

    def test_known_skills_found(self, skills_df: pd.DataFrame):
        all_skills = set()
        for skills in skills_df["skills_list"]:
            for s in skills:
                all_skills.add(s["normalized_skill"].lower())
        expected = {"python", "sql", "excel"}
        found = expected & all_skills
        assert len(found) >= 2, f"Expected at least 2 of {expected} in {all_skills}"

    def test_skill_categories_valid(self, skills_df: pd.DataFrame):
        valid_categories = {
            "technical", "analytical", "tool", "domain",
            "business_soft", "infrastructure", "education", "ai_ml",
        }
        for skills in skills_df["skills_list"]:
            for s in skills:
                assert s["category"] in valid_categories, f"Invalid category: {s['category']}"

    def test_pipeline_produces_parquet(self, skills_df: pd.DataFrame):
        out_dir = Path(tempfile.mkdtemp())
        out_path = out_dir / "integration_test.parquet"
        skills_df.to_parquet(out_path, index=False)
        assert out_path.exists()
        loaded = pd.read_parquet(out_path)
        assert len(loaded) == len(skills_df)
        shutil.rmtree(out_dir, ignore_errors=True)
