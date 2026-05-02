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
    fix_hyphenation,
    normalise_whitespace,
    remove_page_markers,
    remove_urls,
)
from src.corpusforge.cleaners.intra_dedup import remove_intra_doc_duplicates
from src.corpusforge.cleaners.structural_cleaner import remove_structural_noise

__all__ = [
    "HeuristicCleaner",
    "CleaningResult",
    "normalise_unicode",
    "remove_control_characters",
    "normalise_whitespace",
    "remove_urls",
    "remove_page_markers",
    "fix_hyphenation",
    "remove_intra_doc_duplicates",
    "remove_structural_noise",
]