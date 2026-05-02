"""
Tests for corpusforge.output.

Run: pytest tests/test_output.py -v
"""

import json
from pathlib import Path

import pytest

from src.corpusforge.cleaners.heuristic_cleaner import CleaningResult
from src.corpusforge.dedup.deduplicator import DedupResult
from src.corpusforge.filters.quality_filter import FilterResult
from src.corpusforge.output import CorpusFormatter, PipelineReport


# ── Helpers ──────────────────────────────────────────────────────────────

def make_cleaning(doc_id: str, text: str, fmt: str = "txt") -> CleaningResult:
    return CleaningResult(
        doc_id=doc_id,
        original_length=len(text) + 10,
        cleaned_length=len(text),
        cleaned_text=text,
        format_type=fmt,
    )


def make_filter(doc_id: str, status: str = "accept",
                reason: str = "") -> FilterResult:
    return FilterResult(
        doc_id=doc_id,
        status=status,
        reject_reason=reason,
        char_count=100,
        language="en" if status == "accept" else None,
        repetition=0.0,
    )


def make_dedup(kept: list[str], exact_rm: int = 0,
               near_rm: int = 0) -> DedupResult:
    return DedupResult(
        total_input=len(kept) + exact_rm + near_rm,
        after_exact=len(kept) + near_rm,
        after_near=len(kept),
        exact_removed=exact_rm,
        near_removed=near_rm,
        kept_ids=kept,
        removed_ids=[],
    )


TEXT_A = "Natural language processing enables computers to understand text."
TEXT_B = "Deep learning transformed artificial intelligence research significantly."


# ════════════════════════════════════════════════════════════════════════
# CorpusFormatter.write
# ════════════════════════════════════════════════════════════════════════

class TestCorpusFormatter:

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "results"
        CorpusFormatter(out_dir).write([], [], make_dedup([]), {})
        assert out_dir.exists()

    def test_jsonl_created(self, tmp_path: Path) -> None:
        cleanings   = [make_cleaning("a", TEXT_A)]
        filters     = [make_filter("a")]
        dedup       = make_dedup(["a"])
        sources     = {"a": "data/raw/a.txt"}

        CorpusFormatter(tmp_path).write(cleanings, filters, dedup, sources)
        assert (tmp_path / "cleaned_corpus.jsonl").exists()

    def test_report_created(self, tmp_path: Path) -> None:
        CorpusFormatter(tmp_path).write([], [], make_dedup([]), {})
        assert (tmp_path / "cleaning_report.json").exists()

    def test_jsonl_record_fields(self, tmp_path: Path) -> None:
        cleanings   = [make_cleaning("a", TEXT_A)]
        filters     = [make_filter("a")]
        dedup       = make_dedup(["a"])
        sources     = {"a": "data/raw/a.txt"}

        CorpusFormatter(tmp_path).write(cleanings, filters, dedup, sources)
        lines = (tmp_path / "cleaned_corpus.jsonl").read_text().strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["doc_id"]      == "a"
        assert record["text"]        == TEXT_A
        assert record["format_type"] == "txt"
        assert record["char_count"]  == len(TEXT_A)
        assert record["language"]    == "en"
        assert record["source_path"] == "data/raw/a.txt"

    def test_only_kept_ids_written(self, tmp_path: Path) -> None:
        cleanings = [make_cleaning("a", TEXT_A), make_cleaning("b", TEXT_B)]
        filters   = [make_filter("a"), make_filter("b")]
        dedup     = make_dedup(["a"])   # only "a" kept
        sources   = {"a": "a.txt", "b": "b.txt"}

        CorpusFormatter(tmp_path).write(cleanings, filters, dedup, sources)
        lines = (tmp_path / "cleaned_corpus.jsonl").read_text().strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["doc_id"] == "a"

    def test_report_counts(self, tmp_path: Path) -> None:
        cleanings = [make_cleaning("a", TEXT_A), make_cleaning("b", TEXT_B)]
        filters   = [make_filter("a"), make_filter("b", "reject", "too short")]
        dedup     = make_dedup(["a"])
        sources   = {"a": "a.txt", "b": "b.txt"}

        report = CorpusFormatter(tmp_path).write(cleanings, filters, dedup, sources)
        assert report.total_loaded    == 2
        assert report.total_accepted  == 1
        assert report.total_rejected  == 1
        assert report.total_after_dedup == 1

    def test_report_returns_pipeline_report(self, tmp_path: Path) -> None:
        report = CorpusFormatter(tmp_path).write([], [], make_dedup([]), {})
        assert isinstance(report, PipelineReport)

    def test_acceptance_rate(self, tmp_path: Path) -> None:
        cleanings = [make_cleaning("a", TEXT_A), make_cleaning("b", TEXT_B)]
        filters   = [make_filter("a"), make_filter("b", "reject", "too short")]
        dedup     = make_dedup(["a"])
        sources   = {"a": "a.txt", "b": "b.txt"}

        report = CorpusFormatter(tmp_path).write(cleanings, filters, dedup, sources)
        assert report.acceptance_rate == pytest.approx(0.5)

    def test_utf8_text_in_jsonl(self, tmp_path: Path) -> None:
        """Non-ASCII characters must be preserved in JSONL output."""
        text      = "Héllo wörld — naïve résumé"
        cleanings = [make_cleaning("a", text)]
        filters   = [make_filter("a")]
        dedup     = make_dedup(["a"])

        CorpusFormatter(tmp_path).write(cleanings, filters, dedup, {"a": "a.txt"})
        line   = (tmp_path / "cleaned_corpus.jsonl").read_text(encoding="utf-8").strip()
        record = json.loads(line)
        assert record["text"] == text

    def test_empty_pipeline(self, tmp_path: Path) -> None:
        """Empty input should not crash; creates valid empty JSONL."""
        report = CorpusFormatter(tmp_path).write([], [], make_dedup([]), {})
        assert report.total_loaded == 0
        content = (tmp_path / "cleaned_corpus.jsonl").read_text().strip()
        assert content == ""
