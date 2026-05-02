"""
corpusforge.filters
~~~~~~~~~~~~~~~~~~~
Quality filtering — rejects documents that are too short,
wrong language, or excessively repetitive.

Usage
-----
    from corpusforge.filters import QualityFilter, FilterResult
    filter_ = QualityFilter(min_chars=200, target_lang="en")
    result  = filter_.evaluate(cleaning_result)
"""

from src.corpusforge.filters.language_filter import detect_language, passes_language
from src.corpusforge.filters.length_filter import passes_length
from src.corpusforge.filters.quality_filter import FilterResult, QualityFilter
from src.corpusforge.filters.repetition_filter import (
    passes_repetition,
    repetition_ratio,
)

__all__ = [
    "QualityFilter",
    "FilterResult",
    "passes_length",
    "detect_language",
    "passes_language",
    "repetition_ratio",
    "passes_repetition",
]