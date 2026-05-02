import pytest
from pathlib import Path

from src.corpusforge.cleaners.heuristic_cleaner import CleaningResult
from src.corpusforge.filters import (
    FilterResult,
    QualityFilter,
    detect_language,
    passes_language,
    passes_length,
    passes_repetition,
    repetition_ratio,
)


# ── Helpers ──────────────────────────────────────────────────────────────

def make_result(text: str, doc_id: str = "doc_00000000") -> CleaningResult:
    """Quick CleaningResult factory for tests."""
    return CleaningResult(
        doc_id=doc_id,
        original_length=len(text),
        cleaned_length=len(text),
        cleaned_text=text,
        format_type="txt",
    )


LONG_EN = (
    "Natural language processing enables computers to understand "
    "human language. Researchers have developed many techniques "
    "for parsing, tagging, and generating text. These methods are "
    "now applied in search engines, chatbots, and translation services."
)

SHORT_TEXT   = "Hi."
REPEAT_TEXT  = "the " * 100      # extremely repetitive, single word
FRENCH_TEXT  = (
    "Les modèles de traitement automatique du langage naturel permettent "
    "aux ordinateurs de comprendre la langue humaine avec une précision "
    "croissante grâce aux réseaux de neurones profonds."
)


# ════════════════════════════════════════════════════════════════════════
# length_filter
# ════════════════════════════════════════════════════════════════════════

class TestPassesLength:

    @pytest.mark.parametrize("text,min_c,expected", [
        ("a" * 100, 100, True),
        ("a" * 99,  100, False),
        ("a" * 200, 100, True),
        ("",        100, False),
        ("  \n  ",  100, False),   # only whitespace
    ])
    def test_parametrised(self, text: str, min_c: int, expected: bool) -> None:
        assert passes_length(text, min_c) is expected

    def test_default_threshold(self) -> None:
        assert passes_length("a" * 100) is True
        assert passes_length("a" * 99)  is False


# ════════════════════════════════════════════════════════════════════════
# language_filter
# ════════════════════════════════════════════════════════════════════════

class TestDetectLanguage:

    def test_english_detected(self) -> None:
        assert detect_language(LONG_EN) == "en"

    def test_french_detected(self) -> None:
        assert detect_language(FRENCH_TEXT) == "fr"

    def test_empty_returns_none(self) -> None:
        assert detect_language("") is None

    def test_no_features_returns_none(self) -> None:
        # Numbers only have no letter features; result is None
        result = detect_language("12345")
        assert result is None


class TestPassesLanguage:

    def test_english_passes_en(self) -> None:
        assert passes_language(LONG_EN, "en") is True

    def test_french_fails_en(self) -> None:
        assert passes_language(FRENCH_TEXT, "en") is False

    def test_unknown_allowed_by_default(self) -> None:
        # No letter features → None language → allowed by default
        result = passes_language("12345", "en", allow_unknown=True)
        assert result is True

    def test_unknown_rejected_when_flag_false(self) -> None:
        # None detection + allow_unknown=False → rejected
        result = passes_language("", "en", allow_unknown=False)
        assert result is False


# ════════════════════════════════════════════════════════════════════════
# repetition_filter
# ════════════════════════════════════════════════════════════════════════

class TestRepetitionRatio:

    def test_zero_for_unique_text(self) -> None:
        assert repetition_ratio(LONG_EN) < 0.10

    def test_high_for_repeated_text(self) -> None:
        assert repetition_ratio(REPEAT_TEXT) > 0.80

    def test_short_text_returns_zero(self) -> None:
        assert repetition_ratio("one two") == 0.0

    def test_range(self) -> None:
        ratio = repetition_ratio(LONG_EN)
        assert 0.0 <= ratio <= 1.0


class TestPassesRepetition:

    def test_clean_text_passes(self) -> None:
        assert passes_repetition(LONG_EN) is True

    def test_spam_fails(self) -> None:
        assert passes_repetition(REPEAT_TEXT) is False

    def test_custom_threshold(self) -> None:
        # Very strict: 0 % repetition allowed → clean text still fails rarely
        assert passes_repetition(LONG_EN, max_ratio=0.99) is True
        assert passes_repetition(REPEAT_TEXT, max_ratio=0.01) is False


# ════════════════════════════════════════════════════════════════════════
# QualityFilter — integration
# ════════════════════════════════════════════════════════════════════════

class TestQualityFilter:

    def setup_method(self) -> None:
        self.filter = QualityFilter(min_chars=100, target_lang="en", max_rep=0.20)

    def test_good_document_accepted(self) -> None:
        result = self.filter.evaluate(make_result(LONG_EN))
        assert result.status == "accept"
        assert result.reject_reason == ""

    def test_short_document_rejected(self) -> None:
        result = self.filter.evaluate(make_result(SHORT_TEXT))
        assert result.status == "reject"
        assert "short" in result.reject_reason

    def test_wrong_language_rejected(self) -> None:
        result = self.filter.evaluate(make_result(FRENCH_TEXT))
        assert result.status == "reject"
        assert "language" in result.reject_reason

    def test_repetitive_document_rejected(self) -> None:
        result = self.filter.evaluate(make_result(REPEAT_TEXT))
        assert result.status == "reject"
        assert "repetitive" in result.reject_reason

    def test_returns_filter_result(self) -> None:
        result = self.filter.evaluate(make_result(LONG_EN))
        assert isinstance(result, FilterResult)

    def test_doc_id_preserved(self) -> None:
        result = self.filter.evaluate(make_result(LONG_EN, doc_id="myid_abc12345"))
        assert result.doc_id == "myid_abc12345"

    def test_char_count_set(self) -> None:
        result = self.filter.evaluate(make_result(LONG_EN))
        assert result.char_count == len(LONG_EN)

    def test_language_set_on_accept(self) -> None:
        result = self.filter.evaluate(make_result(LONG_EN))
        assert result.language == "en"

    def test_repetition_set_on_accept(self) -> None:
        result = self.filter.evaluate(make_result(LONG_EN))
        assert isinstance(result.repetition, float)

    def test_custom_min_chars(self) -> None:
        strict = QualityFilter(min_chars=1000)
        result = strict.evaluate(make_result(LONG_EN))
        assert result.status == "reject"