"""
corpusforge.dedup
~~~~~~~~~~~~~~~~~
Two-pass deduplication: exact (MD5) then near-dedup (MinHash).

Usage
-----
    from src.corpusforge.dedup import Deduplicator, DedupResult
    result = Deduplicator().run(accepted_results, texts)
"""

from src.corpusforge.dedup.deduplicator import DedupResult, Deduplicator
from src.corpusforge.dedup.exact_dedup import content_hash, exact_deduplicate
from src.corpusforge.dedup.minhash_dedup import NearDupResult, near_deduplicate

__all__ = [
    "Deduplicator",
    "DedupResult",
    "content_hash",
    "exact_deduplicate",
    "NearDupResult",
    "near_deduplicate",
]
