"""
corpusforge.cleaners
~~~~~~~~~~~~~~~~~~~~
Heuristic text cleaning — Unicode, whitespace, noise removal.

Usage
-----
    from corpusforge.cleaners import HeuristicCleaner, CleaningResult
    result = HeuristicCleaner().clean(doc)
"""

from src.corpusforge.cleaners.heuristic_cleaner import CleaningResult, HeuristicCleaner
from src.corpusforge.cleaners.unicode_cleaner import (
    normalise_unicode,
    remove_control_characters,
)
from src.corpusforge.cleaners.whitespace_cleaner import (
    fix_pdf_hyphenation,
    normalise_whitespace,
    remove_page_markers,
    remove_urls,
)

__all__ = [
    "HeuristicCleaner",
    "CleaningResult",
    "normalise_unicode",
    "remove_control_characters",
    "normalise_whitespace",
    "remove_urls",
    "remove_page_markers",
    "fix_pdf_hyphenation",
]