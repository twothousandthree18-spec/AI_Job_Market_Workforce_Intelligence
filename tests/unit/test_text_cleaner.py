from __future__ import annotations

import pytest
from src.cleaning.text_cleaner import TextCleaner


@pytest.fixture
def cleaner():
    return TextCleaner()


class TestStripHtmlTags:
    def test_bold_tag(self, cleaner):
        assert cleaner.clean_description("<b>text</b>") == "text"

    def test_nested_tags(self, cleaner):
        assert cleaner.clean_description("<p><b>hello</b></p>") == "hello"

    def test_self_closing_tag(self, cleaner):
        assert cleaner.clean_description("line<br/>break") == "linebreak"


class TestCollapseWhitespace:
    def test_multiple_spaces(self, cleaner):
        assert cleaner.clean_description("hello   world") == "hello world"

    def test_tabs_and_spaces(self, cleaner):
        assert cleaner.clean_description("hello\t  world") == "hello world"


class TestRemoveControlChars:
    def test_null_bytes(self, cleaner):
        result = cleaner.clean_description("hello\x00world")
        assert "\x00" not in result
        assert "helloworld" in result

    def test_other_control_chars(self, cleaner):
        result = cleaner.clean_description("hello\x08\x0bworld")
        assert "\x08" not in result
        assert "\x0b" not in result


class TestUnicodeNormalization:
    def test_composed_to_decomposed(self, cleaner):
        raw = "\u00e9"  # é (single codepoint)
        result = cleaner.clean_description(raw)
        assert result  # should not raise, NFKD applied


class TestCleanAllAddsDescriptionCleaned:
    def test_adds_field(self, cleaner):
        record = {
            "description": "This is a valid description with enough text to pass.",
            "job_title": "Data Analyst",
            "company_name": "Acme Corp",
        }
        result = cleaner.clean_all(record)
        assert "description_cleaned" in result
        assert result["description_cleaned"] == record["description"]

    def test_html_in_description(self, cleaner):
        record = {"description": "<p>Clean <b>this</b> text.</p>    extra   spaces"}
        result = cleaner.clean_all(record)
        assert "<p>" not in result["description_cleaned"]
        assert "Clean this text." in result["description_cleaned"]


class TestPreservesOriginal:
    def test_original_not_mutated(self, cleaner):
        original = {"description": "<b>hello</b>   world", "job_title": "  Dev  "}
        original_desc = original["description"]
        original_title = original["job_title"]
        cleaner.clean_all(original)
        assert original["description"] == original_desc
        assert original["job_title"] == original_title


class TestEmptyInput:
    def test_empty_string(self, cleaner):
        assert cleaner.clean_description("") == ""

    def test_none_like(self, cleaner):
        assert cleaner.clean_title("") == ""
        assert cleaner.clean_company("") == ""
