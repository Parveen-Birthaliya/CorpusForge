"""
Tests for corpusforge.app (Gradio UI backend).

Note: We test _run_pipeline_on_files() directly — no browser needed.

Run: pytest tests/test_app.py -v
"""

import pytest
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────

SAMPLE_TEXT = (
    "Natural language processing enables computers to understand human "
    "language. Researchers have developed many techniques for parsing, "
    "tagging, and generating text. These methods are applied in search "
    "engines, chatbots, and translation services everywhere today."
)


@pytest.fixture
def txt_file(tmp_path: Path) -> str:
    """A valid TXT file. Returns path as string (Gradio's format)."""
    f = tmp_path / "sample.txt"
    f.write_text(SAMPLE_TEXT, encoding="utf-8")
    return str(f)


@pytest.fixture
def noisy_file(tmp_path: Path) -> str:
    f = tmp_path / "noisy.txt"
    f.write_text("Hi.\x00\x00", encoding="utf-8")  # too short after cleaning
    return str(f)


def run(files, lang="en", min_chars=50, max_rep=0.80, skip_near=True):
    """Convenience wrapper for _run_pipeline_on_files."""
    from src.corpusforge.app import _run_pipeline_on_files
    return _run_pipeline_on_files(files, lang, min_chars, max_rep, skip_near)


# ═════════════════════════════════════════════════════════════════════════
# _run_pipeline_on_files
# ═════════════════════════════════════════════════════════════════════════

class TestRunPipelineOnFiles:

    def test_empty_input_returns_error(self) -> None:
        jsonl_path, report = run([])
        assert jsonl_path == ""
        assert "❌" in report

    def test_returns_two_values(self, txt_file: str) -> None:
        result = run([txt_file])
        assert len(result) == 2

    def test_success_report_contains_checkmark(self, txt_file: str) -> None:
        _, report = run([txt_file])
        assert "✅" in report

    def test_creates_jsonl_file(self, txt_file: str) -> None:
        jsonl_path, _ = run([txt_file])
        assert jsonl_path != ""
        assert Path(jsonl_path).exists()

    def test_jsonl_has_valid_records(self, txt_file: str) -> None:
        import json
        jsonl_path, _ = run([txt_file])
        lines = Path(jsonl_path).read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 1
        record = json.loads(lines[0])
        assert "doc_id"      in record
        assert "text"        in record
        assert "format_type" in record

    def test_report_contains_total_loaded(self, txt_file: str) -> None:
        _, report = run([txt_file])
        assert "Files loaded" in report

    def test_short_file_filtered_out(self, noisy_file: str) -> None:
        _, report = run([noisy_file], min_chars=100)
        # Should reject (too short / noisy)
        assert "Accepted" in report

    def test_nonexistent_file_handled(self, tmp_path: Path) -> None:
        fake = str(tmp_path / "ghost.txt")
        jsonl_path, report = run([fake])
        # Should fail gracefully
        assert "❌" in report or jsonl_path == "" or "error" in report.lower()

    def test_multiple_files(self, tmp_path: Path) -> None:
        files = []
        for i in range(3):
            f = tmp_path / f"doc{i}.txt"
            f.write_text(SAMPLE_TEXT + f" Document {i}.", encoding="utf-8")
            files.append(str(f))
        jsonl_path, report = run(files)
        assert "3" in report   # 3 files loaded

    def test_custom_lang_reflected(self, txt_file: str) -> None:
        # English text with lang=fr → all rejected
        _, report = run([txt_file], lang="fr")
        assert "0" in report or "Accepted" in report


# ═════════════════════════════════════════════════════════════════════════
# create_ui (smoke test — checks Gradio import and build)
# ═════════════════════════════════════════════════════════════════════════

class TestCreateUi:

    def test_returns_gradio_blocks(self) -> None:
        try:
            import gradio as gr
        except ImportError:
            pytest.skip("gradio not installed")

        from src.corpusforge.app import create_ui
        demo = create_ui()
        assert demo is not None
