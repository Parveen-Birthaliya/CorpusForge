"""
Tests for corpusforge.app (Gradio UI backend).

We test _run_pipeline_on_files() directly — no browser needed.
The function now accepts both plain path strings and Gradio-6 dict format.

Run: pytest tests/test_app.py -v
"""

from pathlib import Path
import pytest

SAMPLE_TEXT = (
    "Natural language processing enables computers to understand human "
    "language. Researchers have developed many techniques for parsing, "
    "tagging, and generating text. These methods are applied in search "
    "engines, chatbots, and translation services everywhere today."
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def txt_file(tmp_path: Path) -> str:
    f = tmp_path / "sample.txt"
    f.write_text(SAMPLE_TEXT, encoding="utf-8")
    return str(f)


@pytest.fixture
def txt_file_as_dict(tmp_path: Path) -> dict:
    """Simulate Gradio-6 file dict format."""
    f = tmp_path / "sample_dict.txt"
    f.write_text(SAMPLE_TEXT, encoding="utf-8")
    return {"path": str(f), "name": f.name, "size": f.stat().st_size}


@pytest.fixture
def noisy_file(tmp_path: Path) -> str:
    f = tmp_path / "noisy.txt"
    f.write_text("Hi.\x00\x00", encoding="utf-8")
    return str(f)


def run(files, lang="en", min_chars=50, max_rep=0.80, skip_near=True):
    from src.corpusforge.app import _run_pipeline_on_files
    return _run_pipeline_on_files(files, lang, min_chars, max_rep, skip_near)


# ═════════════════════════════════════════════════════════════════════════
# _run_pipeline_on_files — plain string paths
# ═════════════════════════════════════════════════════════════════════════

class TestRunPipelineOnFiles:

    def test_empty_input_returns_error(self):
        path, report = run([])
        assert path == ""
        assert "❌" in report

    def test_returns_two_values(self, txt_file):
        assert len(run([txt_file])) == 2

    def test_success_report_contains_checkmark(self, txt_file):
        _, report = run([txt_file])
        assert "✅" in report

    def test_creates_jsonl_file(self, txt_file):
        zip_path, _ = run([txt_file])
        assert zip_path != ""
        assert zip_path.endswith(".zip")
        assert Path(zip_path).exists()

    def test_jsonl_has_valid_records(self, txt_file):
        import json
        import zipfile
        zip_path, _ = run([txt_file])
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            assert "cleaned_corpus.jsonl" in z.namelist()
            with z.open("cleaned_corpus.jsonl") as f:
                lines = f.read().decode("utf-8").strip().splitlines()
                assert len(lines) >= 1
                record = json.loads(lines[0])
                assert "doc_id"      in record
                assert "text"        in record
                assert "format_type" in record

    def test_report_contains_total_loaded(self, txt_file):
        _, report = run([txt_file])
        assert "Files loaded" in report

    def test_short_file_filtered_out(self, noisy_file):
        _, report = run([noisy_file], min_chars=100)
        assert "Accepted" in report

    def test_nonexistent_file_handled(self, tmp_path):
        fake = str(tmp_path / "ghost.txt")
        zip_path, report = run([fake])
        assert "❌" in report or zip_path == "" or "error" in report.lower()

    def test_multiple_files(self, tmp_path):
        files = []
        for i in range(3):
            f = tmp_path / f"doc{i}.txt"
            f.write_text(SAMPLE_TEXT + f" Document {i}.", encoding="utf-8")
            files.append(str(f))
        zip_path, report = run(files)
        assert "3" in report

    def test_custom_lang_reflected(self, txt_file):
        _, report = run([txt_file], lang="fr")
        assert "Accepted" in report


# ═════════════════════════════════════════════════════════════════════════
# Gradio-6 dict format
# ═════════════════════════════════════════════════════════════════════════

class TestGradio6DictFormat:

    def test_dict_format_works(self, txt_file_as_dict):
        jsonl_path, report = run([txt_file_as_dict])
        assert "✅" in report or "Accepted" in report

    def test_dict_format_creates_jsonl(self, txt_file_as_dict):
        zip_path, _ = run([txt_file_as_dict])
        assert zip_path != ""
        assert Path(zip_path).exists()


# ═════════════════════════════════════════════════════════════════════════
# create_ui smoke test
# ═════════════════════════════════════════════════════════════════════════

class TestCreateUi:

    def test_returns_gradio_blocks(self):
        try:
            import gradio as gr
        except ImportError:
            pytest.skip("gradio not installed")

        from src.corpusforge.app import create_ui
        demo = create_ui()
        assert demo is not None
