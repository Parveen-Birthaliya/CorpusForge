from dataclasses import dataclass

from src.corpusforge.cleaners.heuristic_cleaner import CleaningResult
from src.corpusforge.filters.language_filter import detect_language, passes_language
from src.corpusforge.filters.length_filter import passes_length
from src.corpusforge.filters.repetition_filter import (
    passes_repetition,
    repetition_ratio,
)


@dataclass
class FilterResult:
    """Output of QualityFilter.evaluate()."""

    doc_id:        str
    status:        str          # "accept" or "reject"
    reject_reason: str          # empty string if accepted
    char_count:    int
    language:      str | None
    repetition:    float


class QualityFilter:
    """
    Three-rule quality gate applied in order:
        1. Length    — rejects text below min_chars
        2. Language  — rejects wrong-language text
        3. Repetition — rejects spam / boilerplate loops

    Parameters
    ----------
    min_chars    : Minimum character count after cleaning (default 100).
    target_lang  : Expected language code, e.g. 'en' (default 'en').
    max_rep      : Maximum repetition ratio allowed (default 0.20).
    allow_unknown_lang : Accept docs whose language cannot be detected.
    """

    def __init__(
        self,
        min_chars:          int   = 100,
        target_lang:        str   = "en",
        max_rep:            float = 0.20,
        allow_unknown_lang: bool  = True,
    ) -> None:
        self.min_chars           = min_chars
        self.target_lang         = target_lang
        self.max_rep             = max_rep
        self.allow_unknown_lang  = allow_unknown_lang

    def evaluate(self, result: CleaningResult) -> FilterResult:
        """Evaluate a CleaningResult and return a FilterResult.

        Parameters
        ----------
        result : Output from HeuristicCleaner.clean().

        Returns
        -------
        FilterResult with status='accept' or status='reject'.
        """
        text = result.cleaned_text

        # ── Rule 1: Length ─────────────────────────────────────────────
        if not passes_length(text, self.min_chars):
            return self._reject(
                result,
                f"too short ({len(text.strip())} chars < {self.min_chars})",
            )

        # ── Rule 2: Language ───────────────────────────────────────────
        lang = detect_language(text)
        if not passes_language(
            text,
            self.target_lang,
            self.allow_unknown_lang,
        ):
            return self._reject(
                result,
                f"wrong language (detected '{lang}', expected '{self.target_lang}')",
                lang=lang,
            )

        # ── Rule 3: Repetition ────────────────────────────────────────
        rep = repetition_ratio(text)
        if not passes_repetition(text, self.max_rep):
            return self._reject(
                result,
                f"too repetitive (ratio={rep:.2f} > {self.max_rep})",
                lang=lang,
                rep=rep,
            )

        # ── Accept ────────────────────────────────────────────────────
        return FilterResult(
            doc_id=result.doc_id,
            status="accept",
            reject_reason="",
            char_count=len(text),
            language=lang,
            repetition=rep,
        )

    def _reject(
        self,
        result: CleaningResult,
        reason: str,
        lang: str | None = None,
        rep:  float      = 0.0,
    ) -> FilterResult:
        return FilterResult(
            doc_id=result.doc_id,
            status="reject",
            reject_reason=reason,
            char_count=len(result.cleaned_text),
            language=lang,
            repetition=rep,
        )
