from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import yaml

_TITLE_MAP_PATH = Path(__file__).resolve().parents[2] / "configs" / "title_map.yaml"

_CHISEL_PREFIX = re.compile(
    r"^(?:online\s+)?(?:full\s+time|part\s+time|remote)\s+", re.IGNORECASE
)
_CHISEL_SUFFIX = re.compile(r"\s+jobs?\s+in\s+pakistan$", re.IGNORECASE)


class TitleNormalizer:
    """Normalise raw job titles to canonical names, role categories and seniority."""

    def __init__(self, title_map_path: Path | str | None = None) -> None:
        path = Path(title_map_path) if title_map_path else _TITLE_MAP_PATH
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._alias_map: dict[str, tuple[str, str]] = {}
        self._keyword_map: dict[str, list[str]] = {}

        for category, cfg in data.get("role_categories", {}).items():
            self._keyword_map[category] = [kw.lower() for kw in cfg.get("keywords", [])]
            for alias in cfg.get("aliases", []):
                self._alias_map[alias.lower().strip()] = (alias.strip(), category)

        seniority = data.get("seniority_levels", {})
        self._seniority_keywords: dict[str, list[str]] = {
            level: [kw.lower() for kw in keywords]
            for level, keywords in seniority.items()
        }

    def _clean_title(self, raw_title: str) -> str:
        cleaned = _CHISEL_PREFIX.sub("", raw_title.strip())
        cleaned = _CHISEL_SUFFIX.sub("", cleaned)
        return cleaned.strip()

    def normalize(self, raw_title: str, experience_level: str | None = None) -> dict[str, str]:
        lower = raw_title.lower().strip()
        cleaned = self._clean_title(raw_title)
        cleaned_lower = cleaned.lower()

        normalized_title = raw_title
        role_category = "other"

        exact = self._alias_map.get(lower)
        if exact:
            normalized_title, role_category = exact
        else:
            exact_cleaned = self._alias_map.get(cleaned_lower)
            if exact_cleaned:
                normalized_title, role_category = exact_cleaned
            else:
                for category, keywords in self._keyword_map.items():
                    if any(kw in cleaned_lower for kw in keywords):
                        role_category = category
                        break

        seniority = self._detect_seniority(cleaned_lower, experience_level)

        return {
            "normalized_title": normalized_title,
            "role_category": role_category,
            "seniority": seniority,
        }

    def _detect_seniority(self, lower_title: str, experience_level: str | None = None) -> str:
        if experience_level:
            exp_lower = experience_level.lower().strip()
            for level, keywords in self._seniority_keywords.items():
                if exp_lower in keywords or any(kw in exp_lower for kw in keywords):
                    return level

        for level, keywords in self._seniority_keywords.items():
            if any(kw in lower_title for kw in keywords):
                return level

        return "unknown"

    def normalize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        results = df.apply(
            lambda row: self.normalize(
                str(row.get("job_title", "")),
                experience_level=row.get("experience_level"),
            ),
            axis=1,
            result_type="expand",
        )

        df["normalized_title"] = results["normalized_title"]
        df["role_category"] = results["role_category"]
        df["seniority"] = results["seniority"]
        return df
