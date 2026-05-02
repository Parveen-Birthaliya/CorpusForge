"""
CorpusForge Gradio Web UI.

Users upload TXT/PDF files → pipeline runs → cleaned JSONL downloads.

Run locally:
    python -m src.corpusforge.app

Deploy to HuggingFace Spaces:
    Use app.py at the repo root (see File 2).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


def _run_pipeline_on_files(
    uploaded_files: list[str],
    target_lang: str,
    min_chars: int,
    max_rep: float,
    skip_near_dedup: bool,
) -> tuple[str, str]:
    """Run the full pipeline on uploaded files.

    Parameters
    ----------
    uploaded_files  : List of file paths provided by Gradio.
    target_lang     : ISO 639-1 language code.
    min_chars       : Minimum character count filter.
    max_rep         : Maximum repetition ratio filter.
    skip_near_dedup : If True, skip MinHash near-dedup.

    Returns
    -------
    (jsonl_path, report_text) — path to output file, human-readable report.
    """
    from src.corpusforge.cleaners import HeuristicCleaner
    from src.corpusforge.dedup import Deduplicator
    from src.corpusforge.filters import QualityFilter
    from src.corpusforge.loaders import PdfLoader, TxtLoader
    from src.corpusforge.output import CorpusFormatter

    if not uploaded_files:
        return "", "❌ No files uploaded."

    loaders      = [TxtLoader(), PdfLoader()]
    cleaner      = HeuristicCleaner()
    quality      = QualityFilter(
        min_chars=min_chars,
        target_lang=target_lang,
        max_rep=max_rep,
    )
    deduplicator = Deduplicator(skip_near=skip_near_dedup)

    # Use a temp dir for output
    out_dir = Path(tempfile.mkdtemp())
    formatter = CorpusFormatter(out_dir)

    # ── Load ──────────────────────────────────────────────────────────────
    from src.corpusforge.models import Document
    docs: list[Document] = []
    errors: list[str]    = []

    for fpath_str in uploaded_files:
        fpath = Path(fpath_str)
        for loader in loaders:
            if loader.can_handle(fpath):
                try:
                    docs.append(loader.load(fpath))
                except Exception as exc:
                    errors.append(f"• {fpath.name}: {exc}")
                break

    if not docs:
        return "", f"❌ No files could be loaded.\n" + "\n".join(errors)

    # ── Clean ─────────────────────────────────────────────────────────────
    cleaning_results = [cleaner.clean(doc) for doc in docs]

    # ── Filter ────────────────────────────────────────────────────────────
    filter_results = [quality.evaluate(cr) for cr in cleaning_results]
    accepted       = [fr for fr in filter_results if fr.status == "accept"]
    texts          = {
        cr.doc_id: cr.cleaned_text
        for cr, fr in zip(cleaning_results, filter_results)
        if fr.status == "accept"
    }

    # ── Dedup ─────────────────────────────────────────────────────────────
    dedup_result = deduplicator.run(accepted, texts)

    # ── Output ────────────────────────────────────────────────────────────
    source_paths = {doc.doc_id: str(doc.source_path) for doc in docs}
    report       = formatter.write(
        cleaning_results, filter_results, dedup_result, source_paths
    )

    jsonl_path = str(out_dir / "cleaned_corpus.jsonl")

    # ── Human-readable report ─────────────────────────────────────────────
    report_lines = [
        "✅  Pipeline complete!",
        "─" * 38,
        f"Files loaded      : {report.total_loaded}",
        f"Accepted          : {report.total_accepted}  ({report.acceptance_rate:.1%})",
        f"Rejected          : {report.total_rejected}",
        f"Exact duplicates  : {report.exact_removed}",
        f"Near  duplicates  : {report.near_removed}",
        f"Final corpus size : {report.total_after_dedup} documents",
        f"Avg compression   : {report.avg_compression:.1%}",
        "─" * 38,
    ]

    if errors:
        report_lines += ["", "⚠️  Load errors:"] + errors

    if report.reject_reasons:
        report_lines += ["", "Rejection breakdown:"]
        for reason, count in report.reject_reasons.items():
            report_lines.append(f"  {reason:12s} : {count}")

    return jsonl_path, "\n".join(report_lines)


def create_ui():
    """Build and return the Gradio Blocks UI."""
    try:
        import gradio as gr
    except ImportError as exc:
        raise ImportError(
            "Gradio is required for the web UI.\n"
            "Install: pip install gradio"
        ) from exc

    with gr.Blocks(
        title="CorpusForge — Corpus Cleaner",
        theme=gr.themes.Soft(),
    ) as demo:

        gr.Markdown(
            """
            # 🔧 CorpusForge
            **Clean messy text corpora for AI applications.**

            Upload TXT or PDF files → download a clean JSONL corpus.
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📂 Input")
                file_input = gr.File(
                    label="Upload files (TXT, PDF)",
                    file_count="multiple",
                    file_types=[".txt", ".pdf"],
                )

                gr.Markdown("### ⚙️ Settings")
                lang_input = gr.Dropdown(
                    choices=["en", "fr", "de", "es", "it", "pt", "nl", "ru", "zh", "ja"],
                    value="en",
                    label="Target language",
                )
                min_chars_input = gr.Slider(
                    minimum=0,
                    maximum=1000,
                    value=100,
                    step=50,
                    label="Minimum characters (after cleaning)",
                )
                max_rep_input = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.20,
                    step=0.05,
                    label="Max repetition ratio",
                )
                skip_near_input = gr.Checkbox(
                    value=False,
                    label="Skip near-dedup (faster, less thorough)",
                )
                run_btn = gr.Button("🚀 Run Pipeline", variant="primary")

            with gr.Column(scale=1):
                gr.Markdown("### 📊 Results")
                report_output = gr.Textbox(
                    label="Pipeline report",
                    lines=20,
                    interactive=False,
                )
                file_output = gr.File(
                    label="Download cleaned_corpus.jsonl",
                )

        run_btn.click(
            fn=_run_pipeline_on_files,
            inputs=[
                file_input,
                lang_input,
                min_chars_input,
                max_rep_input,
                skip_near_input,
            ],
            outputs=[file_output, report_output],
        )

        gr.Markdown(
            """
            ---
            **CorpusForge** — open-source corpus cleaning pipeline.
            [GitHub](https://github.com/your-username/CorpusForge)
            """
        )

    return demo


def main() -> None:
    """Entry point for local development."""
    demo = create_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)


if __name__ == "__main__":
    main()
