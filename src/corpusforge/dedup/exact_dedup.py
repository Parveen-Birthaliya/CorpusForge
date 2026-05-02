"""Exact deduplication using MD5 content hashing."""

import hashlib
from src.corpusforge.cleaners.heuristic_cleaner import CleaningResult
from src.corpusforge.filters.quality_filter import FilterResult


def content_hash(text: str) -> str:
    """Return MD5 hex digest of normalised text.

    Strips leading/trailing whitespace and lowercases before hashing
    so that trivial formatting differences don't create false uniques.
    """
    normalised = text.strip().lower()
    return hashlib.md5(normalised.encode("utf-8")).hexdigest()


def exact_deduplicate(results: list[FilterResult],
                      texts: dict[str, str]) -> list[FilterResult]:
    """Remove exact duplicates. Keep the first occurrence.

    Parameters
    ----------
    results : Accepted FilterResults to deduplicate.
    texts   : Mapping of doc_id → cleaned_text (from CleaningResult).

    Returns
    -------
    Deduplicated list — only the first occurrence of each unique hash.
    """
    seen:   set[str]        = set()
    unique: list[FilterResult] = []

    for result in results:
        text = texts.get(result.doc_id, "")
        h = content_hash(text)
        if h not in seen:
            seen.add(h)
            unique.append(result)

    return unique
