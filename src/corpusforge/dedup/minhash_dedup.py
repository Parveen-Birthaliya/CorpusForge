"""Near-duplicate detection using MinHash + Jaccard similarity.

Install: pip install datasketch
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_THRESHOLD  = 0.85   # documents with Jaccard >= this are near-dupes
DEFAULT_NUM_PERM   = 128    # more permutations = more accurate, but slower


def _shingle(text: str, k: int = 5) -> set[str]:
    """Return the set of k-character shingles from text."""
    text = text.strip().lower()
    if len(text) < k:
        return {text}
    return {text[i: i + k] for i in range(len(text) - k + 1)}


@dataclass
class NearDupResult:
    """Summary from near-dedup pass."""
    total:      int
    kept:       int
    removed:    int
    kept_ids:   list[str]
    removed_ids: list[str]


def near_deduplicate(
    doc_ids: list[str],
    texts:   dict[str, str],
    threshold:  float = DEFAULT_THRESHOLD,
    num_perm:   int   = DEFAULT_NUM_PERM,
) -> NearDupResult:
    """Identify and remove near-duplicate documents with MinHash.

    Parameters
    ----------
    doc_ids   : Ordered list of document IDs to process.
    texts     : Mapping of doc_id → cleaned_text.
    threshold : Jaccard similarity threshold (default 0.85).
    num_perm  : Number of MinHash permutations (default 128).

    Returns
    -------
    NearDupResult with kept/removed IDs.
    """
    try:
        from datasketch import MinHash, MinHashLSH
    except ImportError as exc:
        raise ImportError(
            "datasketch is required for near-dedup.\n"
            "Install: pip install datasketch"
        ) from exc

    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    minhashes: dict[str, MinHash] = {}

    # Build MinHash signatures
    for doc_id in doc_ids:
        text    = texts.get(doc_id, "")
        shingles = _shingle(text)
        m = MinHash(num_perm=num_perm)
        for s in shingles:
            m.update(s.encode("utf-8"))
        minhashes[doc_id] = m

    kept:    list[str] = []
    removed: list[str] = []

    for doc_id in doc_ids:
        m = minhashes[doc_id]
        if doc_id in removed:
            continue
        # Check if this document is similar to any already-kept document
        neighbours = lsh.query(m)
        if neighbours:
            # Similar to an existing doc — mark as near-duplicate
            removed.append(doc_id)
        else:
            lsh.insert(doc_id, m)
            kept.append(doc_id)

    return NearDupResult(
        total=len(doc_ids),
        kept=len(kept),
        removed=len(removed),
        kept_ids=kept,
        removed_ids=removed,
    )
