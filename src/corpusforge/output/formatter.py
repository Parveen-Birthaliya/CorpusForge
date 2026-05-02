"""
Output Formatter — writes the cleaned, deduplicated corpus to disk.

Outputs:
    cleaned_corpus.jsonl   — one JSON object per line (JSONL format)
    cleaning_report.json   — pipeline statistics summary
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.corpusforge.cleaners.heuristic_cleaner import CleaningResult
from src.corpusforge.dedup.deduplicator import DedupResult
from src.corpusforge.filters.quality_filter import FilterResult


@dataclass
class PipelineReport:
    """End-to-end statistics for one pipeline run."""

    total_loaded:       int
    total_cleaned:      int
    total_accepted:     int
    total_rejected:     int
    total_after_dedup:  int
    exact_removed:      int
    near_removed:       int
    avg_compression:    float
    reject_reasons:     dict[str, int]  = field(default_factory=dict)

    @property
    def acceptance_rate(self) -> float:
        if self.total_cleaned == 0:
            return 0.0
        return self.total_accepted / self.total_cleaned

    @property
    def dedup_rate(self) -> float:
        if self.total_accepted == 0:
            return 0.0
        return 1.0 - (self.total_after_dedup / self.total_accepted)


class CorpusFormatter:
    """
    Writes the final cleaned corpus and a summary report to disk.

    Output files
    ------------
    {output_dir}/cleaned_corpus.jsonl   — JSONL, one record per document
    {output_dir}/cleaning_report.json   — pipeline statistics

    Each JSONL record has the shape:
        {
            "doc_id":       "thesis_a3f1b2c9",
            "text":         "...",
            "format_type":  "pdf",
            "char_count":   4821,
            "language":     "en",
            "source_path":  "data/raw/thesis.pdf"
        }
    """

    def __init__(self, output_dir: str | Path = "data/cleaned") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        cleaning_results: list[CleaningResult],
        filter_results:   list[FilterResult],
        dedup_result:     DedupResult,
        source_paths:     dict[str, str],
    ) -> PipelineReport:
        """Write JSONL corpus and JSON report. Return the report.

        Parameters
        ----------
        cleaning_results : Output of HeuristicCleaner (one per document).
        filter_results   : Output of QualityFilter (one per document).
        dedup_result     : Output of Deduplicator.
        source_paths     : Mapping of doc_id → original file path string.

        Returns
        -------
        PipelineReport with full pipeline statistics.
        """
        kept_ids  = set(dedup_result.kept_ids)

        # Build lookup maps
        clean_map:  dict[str, CleaningResult] = {r.doc_id: r for r in cleaning_results}
        filter_map: dict[str, FilterResult]   = {r.doc_id: r for r in filter_results}

        # ── Write JSONL ──────────────────────────────────────────────────
        jsonl_path = self.output_dir / "cleaned_corpus.jsonl"
        written    = 0

        with jsonl_path.open("w", encoding="utf-8") as fh:
            for doc_id in dedup_result.kept_ids:
                cr = clean_map.get(doc_id)
                fr = filter_map.get(doc_id)
                if cr is None or fr is None:
                    continue

                record = {
                    "doc_id":      doc_id,
                    "text":        cr.cleaned_text,
                    "format_type": cr.format_type,
                    "char_count":  cr.cleaned_length,
                    "language":    fr.language,
                    "source_path": source_paths.get(doc_id, ""),
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                
                # Write individual cleaned text file
                txt_dir = self.output_dir / "cleaned_texts"
                txt_dir.mkdir(exist_ok=True)
                (txt_dir / f"{doc_id}.txt").write_text(cr.cleaned_text, encoding="utf-8")
                
                written += 1

        # ── Build report ─────────────────────────────────────────────────
        total_accepted   = sum(1 for r in filter_results if r.status == "accept")
        total_rejected   = sum(1 for r in filter_results if r.status == "reject")
        reject_reasons: dict[str, int] = {}
        for r in filter_results:
            if r.status == "reject":
                # Bucket by first word of reason: "too", "wrong", "repetitive"
                bucket = r.reject_reason.split()[0] if r.reject_reason else "unknown"
                reject_reasons[bucket] = reject_reasons.get(bucket, 0) + 1

        compressions = [r.compression_ratio for r in cleaning_results]
        avg_compression = sum(compressions) / len(compressions) if compressions else 0.0

        report = PipelineReport(
            total_loaded=len(cleaning_results),
            total_cleaned=len(cleaning_results),
            total_accepted=total_accepted,
            total_rejected=total_rejected,
            total_after_dedup=written,
            exact_removed=dedup_result.exact_removed,
            near_removed=dedup_result.near_removed,
            avg_compression=round(avg_compression, 4),
            reject_reasons=reject_reasons,
        )

        # ── Write report ─────────────────────────────────────────────────
        report_path = self.output_dir / "cleaning_report.json"
        report_dict = asdict(report)
        report_dict["acceptance_rate"] = round(report.acceptance_rate, 4)
        report_dict["dedup_rate"]      = round(report.dedup_rate, 4)

        with report_path.open("w", encoding="utf-8") as fh:
            json.dump(report_dict, fh, indent=2, ensure_ascii=False)

        return report
