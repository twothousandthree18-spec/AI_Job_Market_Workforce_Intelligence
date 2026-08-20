from __future__ import annotations

from pathlib import Path

import yaml

_LEXICON_PATH = Path(__file__).resolve().parents[2] / "configs" / "skill_lexicon.yaml"


class SkillNormalizer:
    """Normalises raw skill strings to canonical names via the lexicon."""

    def __init__(self, lexicon_path: Path | str | None = None) -> None:
        path = Path(lexicon_path) if lexicon_path else _LEXICON_PATH
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._norm_map: dict[str, str] = {}
        for _category, skills in data.get("categories", {}).items():
            for entry in skills:
                canonical = entry["canonical"]
                for alias in entry.get("aliases", []):
                    self._norm_map[alias.lower()] = canonical

    def normalize(self, raw_skill: str) -> str:
        canonical = self._norm_map.get(raw_skill.lower().strip())
        return canonical if canonical else raw_skill.title()

    def normalize_batch(self, skills: list[dict]) -> list[dict]:
        for skill in skills:
            raw = skill.get("raw_skill", "")
            skill["normalized_skill"] = self.normalize(raw)
        return skills
