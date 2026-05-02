"""
corpusforge.output
~~~~~~~~~~~~~~~~~~
Writes the cleaned corpus and pipeline report to disk.

Usage
-----
    from src.corpusforge.output import CorpusFormatter, PipelineReport
    report = CorpusFormatter("data/cleaned").write(
        cleaning_results, filter_results, dedup_result, source_paths
    )
"""

from src.corpusforge.output.formatter import CorpusFormatter, PipelineReport

__all__ = ["CorpusFormatter", "PipelineReport"]
