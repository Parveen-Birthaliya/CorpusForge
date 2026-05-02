"""
CorpusForge CLI — command-line interface.

Usage
-----
    # After pip install -e .
    corpusforge --input data/raw --output data/cleaned

    # With options
    corpusforge --input data/raw --output data/cleaned \
                --lang en --min-chars 200 --no-near-dedup
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="corpusforge",
        description=(
            "CorpusForge — clean messy text corpora for AI applications.\n"
            "Runs: Load → Clean → Filter → Dedup → Output"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ── Required ─────────────────────────────────────────────────────────
    parser.add_argument(
        "--input", "-i",
        required=True,
        type=Path,
        metavar="DIR",
        help="Directory containing raw input files (TXT, PDF).",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        type=Path,
        metavar="DIR",
        help="Directory to write cleaned_corpus.jsonl and cleaning_report.json.",
    )

    # ── Filter options ───────────────────────────────────────────────────
    parser.add_argument(
        "--lang",
        default="en",
        metavar="CODE",
        help="Target language ISO 639-1 code (default: en).",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=100,
        metavar="N",
        help="Minimum character count after cleaning (default: 100).",
    )
    parser.add_argument(
        "--max-rep",
        type=float,
        default=0.20,
        metavar="RATIO",
        help="Maximum repetition ratio 0–1 (default: 0.20).",
    )

    # ── Dedup options ────────────────────────────────────────────────────
    parser.add_argument(
        "--no-near-dedup",
        action="store_true",
        help="Skip near-deduplication (MinHash). Faster but less thorough.",
    )
    parser.add_argument(
        "--near-threshold",
        type=float,
        default=0.85,
        metavar="RATIO",
        help="Jaccard similarity threshold for near-dedup (default: 0.85).",
    )

    # ── Misc ─────────────────────────────────────────────────────────────
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    return parser


def _discover_files(input_dir: Path) -> list[Path]:
    """Return all TXT and PDF files found in input_dir (recursive)."""
    supported = {".txt", ".pdf"}
    files = [
        p for p in input_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in supported
    ]
    return sorted(files)


def run_pipeline(args: argparse.Namespace) -> int:
    """Run the full pipeline. Return exit code (0 = success, 1 = error)."""
    # Late imports — keep startup fast for --help / --version
    from tqdm import tqdm

    from src.corpusforge.cleaners import HeuristicCleaner
    from src.corpusforge.dedup import Deduplicator
    from src.corpusforge.filters import QualityFilter
    from src.corpusforge.loaders import PdfLoader, TxtLoader
    from src.corpusforge.output import CorpusFormatter

    # ── Validate input ────────────────────────────────────────────────────
    if not args.input.exists():
        print(f"[ERROR] Input directory not found: {args.input}", file=sys.stderr)
        return 1

    if not args.input.is_dir():
        print(f"[ERROR] --input must be a directory: {args.input}", file=sys.stderr)
        return 1

    # ── Discover files ────────────────────────────────────────────────────
    files = _discover_files(args.input)
    if not files:
        print(f"[ERROR] No TXT or PDF files found in: {args.input}", file=sys.stderr)
        return 1

    print(f"\n╔═══════════════════════════════════════╗")
    print(f"║           CorpusForge v0.1.0          ║")
    print(f"╚═══════════════════════════════════════╝")
    print(f"\n  Input  : {args.input}")
    print(f"  Output : {args.output}")
    print(f"  Files  : {len(files)}")
    print()

    start = time.perf_counter()

    loaders      = [TxtLoader(), PdfLoader()]
    cleaner      = HeuristicCleaner()
    quality      = QualityFilter(
        min_chars=args.min_chars,
        target_lang=args.lang,
        max_rep=args.max_rep,
    )
    deduplicator = Deduplicator(
        near_threshold=args.near_threshold,
        skip_near=args.no_near_dedup,
    )
    formatter    = CorpusFormatter(args.output)

    # ── Stage 1: Load ─────────────────────────────────────────────────────
    print("── Stage 1/4  Loading files ──")
    from src.corpusforge.models import Document
    docs: list[Document] = []
    load_errors = 0

    for fpath in tqdm(files, unit="file"):
        handled = False
        for loader in loaders:
            if loader.can_handle(fpath):
                try:
                    docs.append(loader.load(fpath))
                    handled = True
                except Exception as exc:
                    print(f"  [SKIP] {fpath.name}: {exc}", file=sys.stderr)
                    load_errors += 1
                    handled = True
                break
        if not handled:
            print(f"  [SKIP] {fpath.name}: no loader available", file=sys.stderr)

    print(f"  Loaded {len(docs)} / {len(files)} files  ({load_errors} errors)\n")

    # ── Stage 2: Clean ────────────────────────────────────────────────────
    print("── Stage 2/4  Cleaning text ──")
    from src.corpusforge.cleaners.heuristic_cleaner import CleaningResult
    cleaning_results: list[CleaningResult] = []

    for doc in tqdm(docs, unit="doc"):
        cleaning_results.append(cleaner.clean(doc))

    print(f"  Cleaned {len(cleaning_results)} documents\n")

    # ── Stage 3: Filter ───────────────────────────────────────────────────
    print("── Stage 3/4  Quality filtering ──")
    from src.corpusforge.filters.quality_filter import FilterResult
    filter_results: list[FilterResult] = []
    texts: dict[str, str] = {}

    for cr in tqdm(cleaning_results, unit="doc"):
        fr = quality.evaluate(cr)
        filter_results.append(fr)
        if fr.status == "accept":
            texts[cr.doc_id] = cr.cleaned_text

    accepted = [fr for fr in filter_results if fr.status == "accept"]
    rejected = [fr for fr in filter_results if fr.status == "reject"]
    print(f"  Accepted {len(accepted)}  Rejected {len(rejected)}\n")

    # ── Stage 4: Dedup ────────────────────────────────────────────────────
    print("── Stage 4/4  Deduplication ──")
    dedup_result = deduplicator.run(accepted, texts)
    print(
        f"  Exact removed : {dedup_result.exact_removed}\n"
        f"  Near  removed : {dedup_result.near_removed}\n"
        f"  Final corpus  : {dedup_result.after_near} documents\n"
    )

    # ── Output ────────────────────────────────────────────────────────────
    source_paths = {doc.doc_id: str(doc.source_path) for doc in docs}
    report = formatter.write(cleaning_results, filter_results, dedup_result, source_paths)

    elapsed = time.perf_counter() - start

    print("═" * 45)
    print(f"  Done in {elapsed:.1f}s")
    print(f"  Acceptance rate : {report.acceptance_rate:.1%}")
    print(f"  Dedup rate      : {report.dedup_rate:.1%}")
    print(f"  Output          : {args.output / 'cleaned_corpus.jsonl'}")
    print(f"  Report          : {args.output / 'cleaning_report.json'}")
    print("═" * 45)

    return 0


def main() -> None:
    """Entry point registered in pyproject.toml [project.scripts]."""
    parser = build_parser()
    args   = parser.parse_args()
    sys.exit(run_pipeline(args))


if __name__ == "__main__":
    main()
