"""
Deduplicator — orchestrates exact then near-dedup passes.

Input  : list[FilterResult] + dict[doc_id → cleaned_text]
Output : DedupResult (which doc_ids to keep)
"""

from dataclasses import dataclass, field

from src.corpusforge.dedup.exact_dedup import exact_deduplicate
from src.corpusforge.dedup.minhash_dedup import NearDupResult, near_deduplicate
from src.corpusforge.filters.quality_filter import FilterResult


@dataclass
class DedupResult:
    """Output of Deduplicator.run()."""
    total_input:    int
    after_exact:    int
    after_near:     int
    exact_removed:  int
    near_removed:   int
    kept_ids:       list[str]       = field(default_factory=list)
    removed_ids:    list[str]       = field(default_factory=list)


class Deduplicator:
    """
    Two-pass deduplication:
        Pass 1 — Exact dedup (MD5 hash match, O(n))
        Pass 2 — Near dedup (MinHash LSH, O(n))

    Parameters
    ----------
    near_threshold : Jaccard similarity threshold for near-dedup (default 0.85).
    num_perm       : MinHash permutations (default 128).
    skip_near      : If True, only run exact dedup (faster, less thorough).
    """

    def __init__(
        self,
        near_threshold: float = 0.85,
        num_perm:       int   = 128,
        skip_near:      bool  = False,
    ) -> None:
        self.near_threshold = near_threshold
        self.num_perm       = num_perm
        self.skip_near      = skip_near

    def run(
        self,
        accepted: list[FilterResult],
        texts:    dict[str, str],
    ) -> DedupResult:
        """Run both dedup passes.

        Parameters
        ----------
        accepted : FilterResults with status='accept'.
        texts    : Mapping of doc_id → cleaned_text.

        Returns
        -------
        DedupResult with kept_ids and removed_ids.
        """
        total_input = len(accepted)

        # ── Pass 1: Exact ───────────────────────────────────────────────
        after_exact_results = exact_deduplicate(accepted, texts)
        exact_removed = total_input - len(after_exact_results)

        # ── Pass 2: Near ────────────────────────────────────────────────
        if self.skip_near or len(after_exact_results) < 2:
            near_result = NearDupResult(
                total=len(after_exact_results),
                kept=len(after_exact_results),
                removed=0,
                kept_ids=[r.doc_id for r in after_exact_results],
                removed_ids=[],
            )
        else:
            doc_ids = [r.doc_id for r in after_exact_results]
            near_result = near_deduplicate(
                doc_ids,
                texts,
                threshold=self.near_threshold,
                num_perm=self.num_perm,
            )

        kept_set    = set(near_result.kept_ids)
        removed_ids = (
            [r.doc_id for r in accepted if r.doc_id not in kept_set]
        )

        return DedupResult(
            total_input=total_input,
            after_exact=len(after_exact_results),
            after_near=near_result.kept,
            exact_removed=exact_removed,
            near_removed=near_result.removed,
            kept_ids=near_result.kept_ids,
            removed_ids=removed_ids,
        )
