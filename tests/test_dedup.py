"""
Tests for corpusforge.dedup.

Run: pytest tests/test_dedup.py -v
"""

import pytest
from pathlib import Path

from src.corpusforge.dedup import (
    Deduplicator,
    DedupResult,
    content_hash,
    exact_deduplicate,
)
from src.corpusforge.filters.quality_filter import FilterResult


# ── Helpers ──────────────────────────────────────────────────────────────

def make_filter_result(doc_id: str, text: str = "") -> FilterResult:
    return FilterResult(
        doc_id=doc_id,
        status="accept",
        reject_reason="",
        char_count=len(text),
        language="en",
        repetition=0.0,
    )


EN_A = "Natural language processing enables computers to understand human language."
EN_B = "Deep learning has transformed the field of artificial intelligence."
EN_C = "Natural language processing enables computers to understand human language."  # duplicate of A


# ════════════════════════════════════════════════════════════════════════
# content_hash
# ════════════════════════════════════════════════════════════════════════

class TestContentHash:

    def test_same_text_same_hash(self) -> None:
        assert content_hash(EN_A) == content_hash(EN_A)

    def test_different_text_different_hash(self) -> None:
        assert content_hash(EN_A) != content_hash(EN_B)

    def test_whitespace_normalised(self) -> None:
        assert content_hash("hello world") == content_hash("  hello world  ")

    def test_case_normalised(self) -> None:
        assert content_hash("Hello") == content_hash("hello")

    def test_empty_string(self) -> None:
        h = content_hash("")
        assert isinstance(h, str)
        assert len(h) == 32   # MD5 hex length


# ════════════════════════════════════════════════════════════════════════
# exact_deduplicate
# ════════════════════════════════════════════════════════════════════════

class TestExactDeduplicate:

    def test_no_duplicates_unchanged(self) -> None:
        results = [make_filter_result("a"), make_filter_result("b")]
        texts   = {"a": EN_A, "b": EN_B}
        out     = exact_deduplicate(results, texts)
        assert len(out) == 2

    def test_exact_duplicate_removed(self) -> None:
        results = [
            make_filter_result("a"),
            make_filter_result("b"),
            make_filter_result("c"),   # c has same text as a
        ]
        texts = {"a": EN_A, "b": EN_B, "c": EN_C}
        out = exact_deduplicate(results, texts)
        assert len(out) == 2
        ids = [r.doc_id for r in out]
        assert "a" in ids   # first occurrence kept
        assert "c" not in ids   # duplicate removed

    def test_first_occurrence_kept(self) -> None:
        results = [make_filter_result("first"), make_filter_result("second")]
        texts   = {"first": EN_A, "second": EN_A}
        out     = exact_deduplicate(results, texts)
        assert out[0].doc_id == "first"

    def test_empty_list(self) -> None:
        assert exact_deduplicate([], {}) == []

    def test_whitespace_variants_deduplicated(self) -> None:
        """'hello world' and '  hello world  ' are exact duplicates."""
        results = [make_filter_result("a"), make_filter_result("b")]
        texts   = {"a": "hello world", "b": "  hello world  "}
        out     = exact_deduplicate(results, texts)
        assert len(out) == 1


# ════════════════════════════════════════════════════════════════════════
# Deduplicator (exact only, skip_near=True to avoid datasketch dep)
# ════════════════════════════════════════════════════════════════════════

class TestDeduplicator:

    def setup_method(self) -> None:
        self.dedup = Deduplicator(skip_near=True)

    def test_returns_dedup_result(self) -> None:
        results = [make_filter_result("a")]
        texts   = {"a": EN_A}
        out     = self.dedup.run(results, texts)
        assert isinstance(out, DedupResult)

    def test_no_duplicates(self) -> None:
        results = [make_filter_result("a"), make_filter_result("b")]
        texts   = {"a": EN_A, "b": EN_B}
        out     = self.dedup.run(results, texts)
        assert out.kept_ids == ["a", "b"]
        assert out.exact_removed == 0

    def test_exact_duplicate_caught(self) -> None:
        results = [make_filter_result("a"), make_filter_result("c")]
        texts   = {"a": EN_A, "c": EN_C}
        out     = self.dedup.run(results, texts)
        assert out.exact_removed == 1
        assert "a" in out.kept_ids
        assert "c" in out.removed_ids

    def test_total_input_correct(self) -> None:
        results = [make_filter_result(str(i)) for i in range(5)]
        texts   = {str(i): f"Unique text for document {i}." for i in range(5)}
        out     = self.dedup.run(results, texts)
        assert out.total_input == 5

    def test_empty_input(self) -> None:
        out = self.dedup.run([], {})
        assert out.kept_ids == []
        assert out.total_input == 0
