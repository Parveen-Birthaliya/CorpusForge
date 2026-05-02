"""
Tests for corpusforge.cli.

Run: pytest tests/test_cli.py -v
"""

import json
from pathlib import Path

import pytest

from src.corpusforge.cli import build_parser, _discover_files, run_pipeline


# ── Helpers ───────────────────────────────────────────────────────────────

SAMPLE_TEXT = (
    "Natural language processing enables computers to understand human "
    "language. Researchers have developed many techniques for parsing, "
    "tagging, and generating text. These methods are applied in search "
    "engines, chatbots, and translation services everywhere today."
)


@pytest.fixture
def input_dir(tmp_path: Path) -> Path:
    """A temp input dir with two TXT files."""
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "doc_a.txt").write_text(SAMPLE_TEXT, encoding="utf-8")
    (raw / "doc_b.txt").write_text(SAMPLE_TEXT + " Additional text here.", encoding="utf-8")
    return raw


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    out = tmp_path / "cleaned"
    out.mkdir()
    return out


def make_args(input_dir: Path, output_dir: Path, **kwargs):
    """Build a Namespace like argparse would produce."""
    import argparse
    defaults = dict(
        input=input_dir,
        output=output_dir,
        lang="en",
        min_chars=50,
        max_rep=0.80,
        no_near_dedup=True,
        near_threshold=0.85,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ═════════════════════════════════════════════════════════════════════════
# build_parser
# ═════════════════════════════════════════════════════════════════════════

class TestBuildParser:

    def test_returns_parser(self) -> None:
        parser = build_parser()
        assert parser is not None

    def test_required_args(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])   # missing --input and --output

    def test_parses_input_output(self, tmp_path: Path) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--input",  str(tmp_path),
            "--output", str(tmp_path),
        ])
        assert args.input == tmp_path
        assert args.output == tmp_path

    def test_defaults(self, tmp_path: Path) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--input",  str(tmp_path),
            "--output", str(tmp_path),
        ])
        assert args.lang       == "en"
        assert args.min_chars  == 100
        assert args.max_rep    == pytest.approx(0.20)
        assert args.no_near_dedup is False

    def test_custom_lang(self, tmp_path: Path) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--input",  str(tmp_path),
            "--output", str(tmp_path),
            "--lang",   "fr",
        ])
        assert args.lang == "fr"

    def test_no_near_dedup_flag(self, tmp_path: Path) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--input",  str(tmp_path),
            "--output", str(tmp_path),
            "--no-near-dedup",
        ])
        assert args.no_near_dedup is True


# ═════════════════════════════════════════════════════════════════════════
# _discover_files
# ═════════════════════════════════════════════════════════════════════════

class TestDiscoverFiles:

    def test_finds_txt_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("x")
        (tmp_path / "b.txt").write_text("x")
        files = _discover_files(tmp_path)
        assert len(files) == 2

    def test_finds_pdf_files(self, tmp_path: Path) -> None:
        (tmp_path / "paper.pdf").write_bytes(b"x")
        files = _discover_files(tmp_path)
        assert len(files) == 1

    def test_ignores_other_extensions(self, tmp_path: Path) -> None:
        (tmp_path / "data.csv").write_text("x")
        (tmp_path / "notes.md").write_text("x")
        files = _discover_files(tmp_path)
        assert files == []

    def test_recursive(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "nested.txt").write_text("x")
        files = _discover_files(tmp_path)
        assert len(files) == 1

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert _discover_files(tmp_path) == []

    def test_case_insensitive_extension(self, tmp_path: Path) -> None:
        (tmp_path / "UPPER.TXT").write_text("x")
        files = _discover_files(tmp_path)
        assert len(files) == 1


# ═════════════════════════════════════════════════════════════════════════
# run_pipeline
# ═════════════════════════════════════════════════════════════════════════

class TestRunPipeline:

    def test_returns_zero_on_success(
        self, input_dir: Path, output_dir: Path
    ) -> None:
        args = make_args(input_dir, output_dir)
        code = run_pipeline(args)
        assert code == 0

    def test_creates_jsonl(self, input_dir: Path, output_dir: Path) -> None:
        args = make_args(input_dir, output_dir)
        run_pipeline(args)
        assert (output_dir / "cleaned_corpus.jsonl").exists()

    def test_creates_report(self, input_dir: Path, output_dir: Path) -> None:
        args = make_args(input_dir, output_dir)
        run_pipeline(args)
        assert (output_dir / "cleaning_report.json").exists()

    def test_report_is_valid_json(
        self, input_dir: Path, output_dir: Path
    ) -> None:
        args = make_args(input_dir, output_dir)
        run_pipeline(args)
        report = json.loads(
            (output_dir / "cleaning_report.json").read_text()
        )
        assert "total_loaded" in report
        assert "acceptance_rate" in report

    def test_missing_input_dir_returns_one(
        self, tmp_path: Path, output_dir: Path
    ) -> None:
        args = make_args(tmp_path / "nonexistent", output_dir)
        code = run_pipeline(args)
        assert code == 1

    def test_input_is_file_returns_one(
        self, tmp_path: Path, output_dir: Path
    ) -> None:
        f = tmp_path / "file.txt"
        f.write_text("x")
        args = make_args(f, output_dir)    # passing a file, not a dir
        code = run_pipeline(args)
        assert code == 1

    def test_empty_input_dir_returns_one(
        self, tmp_path: Path, output_dir: Path
    ) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        args = make_args(empty, output_dir)
        code = run_pipeline(args)
        assert code == 1
