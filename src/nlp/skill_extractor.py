from __future__ import annotations

import re
from pathlib import Path

import yaml

_LEXICON_PATH = Path(__file__).resolve().parents[2] / "configs" / "skill_lexicon.yaml"


class SkillExtractor:
    """Extracts skills from text using a curated lexicon."""

    def __init__(self, lexicon_path: Path | str | None = None) -> None:
        path = Path(lexicon_path) if lexicon_path else _LEXICON_PATH
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._alias_map: dict[str, tuple[str, str]] = {}
        self._canonical_names: list[str] = []

        for category, skills in data.get("categories", {}).items():
            for entry in skills:
                canonical = entry["canonical"]
                self._canonical_names.append(canonical)
                for alias in entry.get("aliases", []):
                    self._alias_map[alias.lower()] = (canonical, category)

        self._canonical_names.sort(key=len, reverse=True)

    def extract_from_text(self, text: str) -> list[dict[str, str]]:
        if not text:
            return []

        seen: set[str] = set()
        results: list[dict[str, str]] = []

        for alias_lower, (canonical, category) in self._alias_map.items():
            pattern = re.compile(r"\b" + re.escape(alias_lower) + r"\b", re.IGNORECASE)
            match = pattern.search(text)
            if match and canonical not in seen:
                seen.add(canonical)
                results.append({
                    "raw_skill": match.group(0),
                    "normalized_skill": canonical,
                    "category": category,
                    "method": "lexicon",
                })

        for canonical in self._canonical_names:
            if canonical in seen:
                continue
            pattern = re.compile(re.escape(canonical), re.IGNORECASE)
            match = pattern.search(text)
            if match:
                category = self._get_canonical_category(canonical)
                seen.add(canonical)
                results.append({
                    "raw_skill": match.group(0),
                    "normalized_skill": canonical,
                    "category": category,
                    "method": "regex",
                })

        return results

    def extract_from_record(self, record: dict) -> list[dict[str, str]]:
        parts: list[str] = []
        for field in ("job_title", "description", "education_requirement"):
            value = record.get(field)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        combined = " ".join(parts)
        return self.extract_from_text(combined)

    def _get_canonical_category(self, canonical: str) -> str:
        for _, (can, cat) in self._alias_map.items():
            if can == canonical:
                return cat
        return "unknown"
