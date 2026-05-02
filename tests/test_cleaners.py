import pytest
from pathlib import Path

from src.corpusforge.cleaners import (
    HeuristicCleaner,
    CleaningResult,
    normalise_unicode,
    remove_control_characters,
    normalise_whitespace,
    remove_urls,
    remove_page_markers,
    fix_pdf_hyphenation,
)
from src.corpusforge.models import Document


# ── Helpers ───────────────────────────────────────────────────────────────

def make_doc(text: str, format_type: str = "txt") -> Document:
    """Quick Document factory for tests."""
    return Document(
        doc_id="test_00000000",
        text=text,
        source_path=Path("fake/path.txt"),
        format_type=format_type,
        char_count=len(text),
    )


# ═════════════════════════════════════════════════════════════════════════
# unicode_cleaner
# ═════════════════════════════════════════════════════════════════════════

class TestNormaliseUnicode:

    def test_nfd_becomes_nfc(self) -> None:
        import unicodedata
        nfd = "cafe\u0301"       # e + combining accent (2 code points)
        result = normalise_unicode(nfd)
        assert unicodedata.is_normalized("NFC", result)

    def test_already_nfc_unchanged(self) -> None:
        text = "Hello, world!"
        assert normalise_unicode(text) == text

    def test_empty_string(self) -> None:
        assert normalise_unicode("") == ""


class TestRemoveControlCharacters:

    def test_removes_null_bytes(self) -> None:
        assert "\x00" not in remove_control_characters("he\x00llo")

    def test_removes_form_feed(self) -> None:
        assert "\x0c" not in remove_control_characters("page\x0cbreak")

    def test_removes_escape(self) -> None:
        assert "\x1b" not in remove_control_characters("esc\x1bchar")

    def test_keeps_newlines(self) -> None:
        assert "\n" in remove_control_characters("line1\nline2")

    def test_keeps_tabs(self) -> None:
        assert "\t" in remove_control_characters("col1\tcol2")

    def test_empty_string(self) -> None:
        assert remove_control_characters("") == ""

    def test_clean_text_unchanged(self) -> None:
        text = "Hello world. Normal text."
        assert remove_control_characters(text) == text


# whitespace_cleaner

class TestNormaliseWhitespace:

    @pytest.mark.parametrize("raw,expected", [
        ("hello   world",            "hello world"),
        ("hello\n\n\n\nworld",       "hello\n\nworld"),
        ("\t\ttabs  here",           " tabs here"),
        ("  leading and trailing  ", "leading and trailing"),
        ("a\n\nb",                   "a\n\nb"),   # 2 newlines kept
    ])
    def test_parametrised(self, raw: str, expected: str) -> None:
        assert normalise_whitespace(raw) == expected

    def test_empty_string(self) -> None:
        assert normalise_whitespace("") == ""


class TestRemoveUrls:

    def test_http_removed(self) -> None:
        assert "http" not in remove_urls("Visit http://example.com for info")

    def test_https_removed(self) -> None:
        assert "https" not in remove_urls("See https://arxiv.org/abs/1234")

    def test_www_removed(self) -> None:
        assert "www" not in remove_urls("Go to www.google.com")

    def test_no_url_unchanged(self) -> None:
        text = "No URLs in this text."
        assert remove_urls(text) == text

    def test_replacement_is_space(self) -> None:
        # space prevents word merging at boundary
        result = remove_urls("visithttp://x.com.")
        assert "visit " in result

    def test_empty_string(self) -> None:
        assert remove_urls("").strip() == ""


class TestRemovePageMarkers:

    @pytest.mark.parametrize("text", [
        "Page 5 of 88",
        "page 5 of 88",
        "PAGE 5 OF 88",
        "5 / 88",
        "5/88",
    ])
    def test_page_marker_removed(self, text: str) -> None:
        result = remove_page_markers(text).strip()
        assert result == "" or "5" not in result

    def test_standalone_number_line_removed(self) -> None:
        text = "Some content\n  42  \nMore content"
        result = remove_page_markers(text)
        bare_42_lines = [l for l in result.splitlines() if l.strip() == "42"]
        assert len(bare_42_lines) == 0

    def test_inline_number_kept(self) -> None:
        # "42 researchers" — NOT a page number
        text = "42 researchers worked on this."
        result = remove_page_markers(text)
        assert "42" in result


class TestFixPdfHyphenation:

    @pytest.mark.parametrize("raw,expected", [
        ("exam-\nines",   "examines"),
        ("behav-\niour",  "behaviour"),
        ("multi-\nline",  "multiline"),
    ])
    def test_rejoins_word(self, raw: str, expected: str) -> None:
        assert expected in fix_pdf_hyphenation(raw)

    def test_normal_hyphen_untouched(self) -> None:
        text = "well-known result"
        assert fix_pdf_hyphenation(text) == text

    def test_dash_at_end_of_line_without_word_untouched(self) -> None:
        # "end-\n " — the character after hyphen+newline is a space, not \w
        text = "end-\n next line"
        result = fix_pdf_hyphenation(text)
        assert "-\n" in result   # not joined because next char is space


# HeuristicCleaner — integration
NOISY_TEXT = (
    "â€œStudy results.\n\n\n\n"
    "Page 5 of 88\n"
    "Visit https://example.com today.\n"
    "Multiple   spaces   everywhere.\x00"
)


class TestHeuristicCleaner:

    def test_returns_cleaning_result(self) -> None:
        result = HeuristicCleaner().clean(make_doc("Hello world."))
        assert isinstance(result, CleaningResult)

    def test_doc_id_preserved(self) -> None:
        result = HeuristicCleaner().clean(make_doc("Hello world."))
        assert result.doc_id == "test_00000000"

    def test_format_type_preserved(self) -> None:
        result = HeuristicCleaner().clean(make_doc("Hello.", "pdf"))
        assert result.format_type == "pdf"

    def test_no_double_spaces(self) -> None:
        result = HeuristicCleaner().clean(make_doc(NOISY_TEXT))
        assert "  " not in result.cleaned_text

    def test_no_null_bytes(self) -> None:
        result = HeuristicCleaner().clean(make_doc(NOISY_TEXT))
        assert "\x00" not in result.cleaned_text

    def test_no_url(self) -> None:
        result = HeuristicCleaner().clean(make_doc(NOISY_TEXT))
        assert "https://" not in result.cleaned_text

    def test_no_page_marker(self) -> None:
        result = HeuristicCleaner().clean(make_doc(NOISY_TEXT))
        assert "Page 5 of 88" not in result.cleaned_text

    def test_original_length_correct(self) -> None:
        result = HeuristicCleaner().clean(make_doc(NOISY_TEXT))
        assert result.original_length == len(NOISY_TEXT)

    def test_cleaned_length_matches_text(self) -> None:
        result = HeuristicCleaner().clean(make_doc(NOISY_TEXT))
        assert result.cleaned_length == len(result.cleaned_text)

    def test_compression_ratio_range(self) -> None:
        result = HeuristicCleaner().clean(make_doc(NOISY_TEXT))
        assert 0.0 <= result.compression_ratio <= 1.0

    def test_clean_text_passthrough(self) -> None:
        clean = "The quick brown fox jumps over the lazy dog."
        result = HeuristicCleaner().clean(make_doc(clean))
        assert result.cleaned_text == clean

    def test_empty_document(self) -> None:
        result = HeuristicCleaner().clean(make_doc(""))
        assert result.cleaned_text == ""
        assert result.compression_ratio == 0.0

    def test_pdf_hyphenation_applied(self) -> None:
        doc = make_doc("The study exam-\nines behaviour.", format_type="pdf")
        result = HeuristicCleaner().clean(doc)
        assert "examines" in result.cleaned_text

    def test_txt_windows_line_endings_removed(self) -> None:
        doc = make_doc("line1\r\nline2\r\nline3", format_type="txt")
        result = HeuristicCleaner().clean(doc)
        assert "\r" not in result.cleaned_text

    def test_is_significantly_reduced_true(self) -> None:
        # Very noisy text — should be significantly reduced
        noisy = "\x00" * 500 + "Hello."
        result = HeuristicCleaner().clean(make_doc(noisy))
        assert result.is_significantly_reduced is True

    def test_is_significantly_reduced_false(self) -> None:
        clean = "The quick brown fox jumps over the lazy dog."
        result = HeuristicCleaner().clean(make_doc(clean))
        assert result.is_significantly_reduced is False