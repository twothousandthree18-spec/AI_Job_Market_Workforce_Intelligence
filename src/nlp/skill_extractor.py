from __future__ import annotations

import re
from pathlib import Path

import yaml

_LEXICON_PATH = Path(__file__).resolve().parents[2] / "configs" / "skill_lexicon.yaml"

AMBIGUOUS_SKILLS: dict[str, dict[str, list[str]]] = {
    "R": {
        "positive": [
            r"(?:experience|knowledge|proficiency|skills?|expertise)\s+(?:in|with|of)\s+R\b",
            r"\bR\s+(?:programming|language|studio|statistical|packages?|scripts?|code|environment|ecosystem)\b",
            r"\b(?:tidyverse|dplyr|ggplot2|rstudio|cran|bioconductor|rmarkdown)\b",
            r"\b(?:using|in)\s+R\b",
            r"(?:python|sas|sql|java|scala|javascript|c\+\+|excel)[,/\s]+R\b",
            r"\bR[,/\s]+(?:python|sas|sql|java|scala|javascript|c\+\+|excel)\b",
            r"\bR\s+(?:and|or)\s+(?:Python|SQL|SAS|Java|JavaScript)\b",
        ],
        "negative": [
            r"[&]\s*R\b",
            r"\bR\s*[&]\b",
            r"\bR\s+and\s+D\b",
            r"\bR\s+(?:is|are|was|were|has|have|had|will|would|can|could|should|may|might|must)\b",
            r"\bR\s+(?:role|responsibilities?|required|reporting|reports?|research|results?|reviews?|relationships?|revenue|risk|rates?|regions?|recommendations?|regulations?|requirements?|resources?|response|resolution)\b",
        ],
        "require_positive_context": True,
    },
    "Go": {
        "positive": [
            r"\b(?:Go|Golang)\s+(?:programming|language|developer|engineer|backend|microservice|experience)\b",
            r"(?:experience|knowledge|proficiency|skills?)\s+(?:in|with|of)\s+Go\b",
            r"\bGolang\b",
        ],
        "negative": [
            r"\bgo[\s-]+(?:to|through|into|over|under|up|down|out|in|on|off|back|forward|away)\b",
            r"\bgo(?:ing|es|ne)\b",
            r"\b(?:to|will|can|should|must|may|might|shall|let|help|wanna|gonna)\s+go\b",
        ],
    },
    "Scala": {
        "positive": [
            r"\bScala\s+(?:programming|language|developer|engineer|experience|spark|akka|play)\b",
            r"(?:experience|knowledge|proficiency|skills?)\s+(?:in|with|of)\s+Scala\b",
            r"(?:java|python|r|spark|kotlin)[,/\s]+Scala\b",
        ],
        "negative": [
            r"\bscalab(?:le|ility|ility)\b",
        ],
    },
    "SAS": {
        "positive": [
            r"\bSAS\s+(?:Viya|Enterprise|Base|programming|language|certified|analyst|statistical|tool|macro)\b",
            r"(?:experience|knowledge|proficiency|skills?)\s+(?:in|with|of)\s+SAS\b",
            r"(?:SAS|sas)\s+(?:and|/,)\s+(?:SQL|R|Python|Excel)\b",
        ],
        "negative": [
            r"\bdisas(?:ter|s)\b",
            r"\bpassas(?:s)\b",
        ],
    },
    "C#": {
        "positive": [
            r"\bC#\s*[/&.]?\s*(?:\.NET|dotnet|ASP|developer|programming|experience)\b",
            r"(?:experience|knowledge|proficiency|skills?)\s+(?:in|with|of)\s+C#\b",
            r"\.NET\s+(?:developer|engineer|experience|Core|framework)",
        ],
        "negative": [],
    },
    "Java": {
        "positive": [
            r"\bJava\s+(?:programming|language|developer|engineer|SE|EE|EE|experience|Spring|enterprise)\b",
            r"(?:experience|knowledge|proficiency|skills?)\s+(?:in|with|of)\s+Java\b",
        ],
        "negative": [],
    },
    "SQL": {
        "positive": [
            r"\bSQL\s+(?:queries?|scripts?|skills?|experience|database|server|development|writing|querying)\b",
            r"(?:experience|knowledge|proficiency|skills?)\s+(?:in|with|of)\s+SQL\b",
            r"\b(?:MySQL|PostgreSQL|T-SQL|PLSQL|PL\/SQL|SQL\s+Server)\b",
        ],
        "negative": [],
    },
}


class SkillExtractor:
    """Extracts skills from text using a curated lexicon with contextual disambiguation."""

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

        self._pos_patterns: dict[str, list[re.Pattern]] = {}
        self._neg_patterns: dict[str, list[re.Pattern]] = {}
        self._require_context: set[str] = set()
        for skill, rules in AMBIGUOUS_SKILLS.items():
            self._pos_patterns[skill] = [
                re.compile(p, re.IGNORECASE) for p in rules.get("positive", [])
            ]
            self._neg_patterns[skill] = [
                re.compile(p, re.IGNORECASE) for p in rules.get("negative", [])
            ]
            if rules.get("require_positive_context"):
                self._require_context.add(skill)

    def extract_from_text(self, text: str) -> list[dict[str, str]]:
        if not text:
            return []

        seen: set[str] = set()
        results: list[dict[str, str]] = []

        for alias_lower, (canonical, category) in self._alias_map.items():
            escaped = re.escape(alias_lower)
            if re.search(r"[a-z0-9]", alias_lower):
                pattern = re.compile(
                    r"(?<![a-z0-9])" + escaped + r"(?![a-z0-9])", re.IGNORECASE
                )
            else:
                pattern = re.compile(escaped, re.IGNORECASE)
            match = pattern.search(text)
            if match and canonical not in seen:
                if self._is_false_positive(canonical, text, match):
                    continue
                seen.add(canonical)
                ctx = self._extract_context(text, match.start(), match.end())
                results.append({
                    "raw_skill": match.group(0),
                    "normalized_skill": canonical,
                    "category": category,
                    "method": "lexicon",
                    "confidence": self._calc_confidence(canonical, text, "lexicon"),
                    "context": ctx,
                })

        for canonical in self._canonical_names:
            if canonical in seen:
                continue
            escaped = re.escape(canonical)
            if re.search(r"[a-z0-9]", canonical.lower()):
                pattern = re.compile(
                    r"(?<![a-z0-9])" + escaped + r"(?![a-z0-9])", re.IGNORECASE
                )
            else:
                pattern = re.compile(escaped, re.IGNORECASE)
            match = pattern.search(text)
            if match:
                if self._is_false_positive(canonical, text, match):
                    continue
                category = self._get_canonical_category(canonical)
                seen.add(canonical)
                ctx = self._extract_context(text, match.start(), match.end())
                results.append({
                    "raw_skill": match.group(0),
                    "normalized_skill": canonical,
                    "category": category,
                    "method": "regex",
                    "confidence": self._calc_confidence(canonical, text, "regex"),
                    "context": ctx,
                })

        return results

    def _is_false_positive(self, canonical: str, text: str, match: re.Match) -> bool:
        if canonical in self._neg_patterns:
            for neg in self._neg_patterns[canonical]:
                if neg.search(text):
                    return True
        if canonical in self._require_context:
            has_positive = False
            for pos in self._pos_patterns.get(canonical, []):
                if pos.search(text):
                    has_positive = True
                    break
            if not has_positive:
                return True
        return False

    def _calc_confidence(self, canonical: str, text: str, method: str) -> str:
        if canonical in self._pos_patterns:
            for pos in self._pos_patterns[canonical]:
                if pos.search(text):
                    return "high"
            if canonical in self._neg_patterns and self._neg_patterns[canonical]:
                return "medium"
        if method == "lexicon":
            return "high"
        if len(canonical) <= 2:
            return "low"
        return "medium"

    def _extract_context(self, text: str, start: int, end: int, window: int = 60) -> str:
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)
        return text[ctx_start:ctx_end].strip()

    def extract_from_record(self, record: dict) -> list[dict[str, str]]:
        parts: list[str] = []
        source_fields: dict[str, str] = {}
        for field in ("job_title", "description", "education_requirement"):
            value = record.get(field)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
                for word in value.strip().split():
                    source_fields[word.lower()] = field
        combined = " ".join(parts)
        results = self.extract_from_text(combined)

        for r in results:
            raw_lower = r["raw_skill"].lower()
            r["source_field"] = self._infer_source_field(raw_lower, record)

        return results

    def _infer_source_field(self, raw_lower: str, record: dict) -> str:
        for field in ("job_title", "description", "education_requirement"):
            value = record.get(field)
            if isinstance(value, str) and raw_lower in value.lower():
                return field
        return "unknown"

    def _get_canonical_category(self, canonical: str) -> str:
        for _, (can, cat) in self._alias_map.items():
            if can == canonical:
                return cat
        return "unknown"
