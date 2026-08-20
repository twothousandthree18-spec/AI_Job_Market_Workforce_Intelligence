from __future__ import annotations

import html
import re
import unicodedata

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_WHITESPACE_RE = re.compile(r"[^\S\n]+")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class TextCleaner:
    """Standardised text cleaning for job-posting fields."""

    def clean_description(self, raw_text: str) -> str:
        if not raw_text:
            return ""
        text = _HTML_TAG_RE.sub("", raw_text)
        text = html.unescape(text)
        text = unicodedata.normalize("NFKD", text)
        text = _CONTROL_CHAR_RE.sub("", text)
        text = _MULTI_WHITESPACE_RE.sub(" ", text)
        return text.strip()

    def clean_title(self, raw_title: str) -> str:
        if not raw_title:
            return ""
        text = _HTML_TAG_RE.sub("", raw_title)
        text = html.unescape(text)
        text = _MULTI_WHITESPACE_RE.sub(" ", text)
        return text.strip()

    def clean_company(self, raw_company: str) -> str:
        if not raw_company:
            return ""
        text = _HTML_TAG_RE.sub("", raw_company)
        text = html.unescape(text)
        text = _MULTI_WHITESPACE_RE.sub(" ", text)
        return text.strip()

    def clean_all(self, record: dict) -> dict:
        cleaned = dict(record)
        if "description" in record and isinstance(record["description"], str):
            cleaned["description_cleaned"] = self.clean_description(record["description"])
        if "job_title" in record and isinstance(record["job_title"], str):
            cleaned["job_title"] = self.clean_title(record["job_title"])
        if "company_name" in record and isinstance(record["company_name"], str):
            cleaned["company_name"] = self.clean_company(record["company_name"])
        return cleaned
