"""
CorpusForge Gradio Web UI.

Users upload TXT/PDF files → pipeline runs → cleaned JSONL downloads.

Run locally:
    PYTHONPATH=/path/to/CorpusForge python -m src.corpusforge.app
    # → open http://localhost:7860
"""

from __future__ import annotations

import tempfile
from pathlib import Path


def _run_pipeline_on_files(
    uploaded_files,          # Gradio 6 passes list[dict] or list[str] depending on version
    target_lang: str,
    min_chars: int,
    max_rep: float,
    skip_near_dedup: bool,
    enable_advanced_pii: bool,
    enable_ocr: bool,
) -> tuple[str, str, str, str]:
    """Run the full CorpusForge pipeline on uploaded files.

    Returns
    -------
    (zip_path, jsonl_path, report_text, preview_text)
    """
    from src.corpusforge.cleaners import HeuristicCleaner
    from src.corpusforge.dedup import Deduplicator
    from src.corpusforge.filters import QualityFilter
    from src.corpusforge.loaders import PdfLoader, TxtLoader
    from src.corpusforge.models import Document
    from src.corpusforge.output import CorpusFormatter

    # ── Normalise Gradio file input ───────────────────────────────────────
    # Gradio ≥6 returns a list of dicts with 'path' key (or NamedString).
    # Older versions return plain file-path strings.
    if not uploaded_files:
        return "", "", "❌ No files uploaded.", ""

    file_paths: list[Path] = []
    for f in uploaded_files:
        if isinstance(f, dict):
            file_paths.append(Path(f["path"]))
        elif hasattr(f, "name"):          # NamedString / TemporaryFile
            file_paths.append(Path(f.name))
        else:
            file_paths.append(Path(str(f)))

    loaders      = [TxtLoader(), PdfLoader()]
    cleaner      = HeuristicCleaner(enable_advanced_pii=enable_advanced_pii, enable_ocr=enable_ocr)
    quality      = QualityFilter(
        min_chars=min_chars,
        target_lang=target_lang,
        max_rep=max_rep,
    )
    deduplicator = Deduplicator(skip_near=skip_near_dedup)

    out_dir   = Path(tempfile.mkdtemp())
    formatter = CorpusFormatter(out_dir)

    # ── Stage 1: Load ────────────────────────────────────────────────────
    docs:   list[Document] = []
    errors: list[str]      = []

    for fpath in file_paths:
        handled = False
        for loader in loaders:
            if loader.can_handle(fpath):
                handled = True
                try:
                    docs.append(loader.load(fpath))
                except Exception as exc:
                    errors.append(f"• {fpath.name}: {exc}")
                break
        if not handled:
            errors.append(f"• {fpath.name}: unsupported format")

    if not docs:
        msg = "❌ No files could be loaded."
        if errors:
            msg += "\n\nErrors:\n" + "\n".join(errors)
        return "", "", msg, ""

    # ── Stage 2: Clean ───────────────────────────────────────────────────
    cleaning_results = [cleaner.clean(doc) for doc in docs]

    # ── Stage 3: Filter ──────────────────────────────────────────────────
    filter_results = [quality.evaluate(cr) for cr in cleaning_results]
    accepted = [fr for fr in filter_results if fr.status == "accept"]
    texts = {
        cr.doc_id: cr.cleaned_text
        for cr, fr in zip(cleaning_results, filter_results)
        if fr.status == "accept"
    }

    # ── Stage 4: Dedup ───────────────────────────────────────────────────
    dedup_result = deduplicator.run(accepted, texts)

    # ── Stage 5: Output ──────────────────────────────────────────────────
    source_paths = {doc.doc_id: str(doc.source_path) for doc in docs}
    report = formatter.write(cleaning_results, filter_results, dedup_result, source_paths)

    import shutil
    zip_path = str(out_dir / "corpusforge_results")
    shutil.make_archive(zip_path, 'zip', out_dir)
    final_zip_path = f"{zip_path}.zip"
    final_jsonl_path = str(out_dir / "cleaned_corpus.jsonl")
    
    # ── Get Preview Text ──────────────────────────────────────────────────
    preview_text = ""
    if texts:
        first_doc_id = list(texts.keys())[0]
        preview_text = texts[first_doc_id]
        if len(preview_text) > 2000:
            preview_text = preview_text[:2000] + "\n\n... (truncated for preview)"

    # ── Human-readable report ─────────────────────────────────────────────
    lines = [
        "✅  Pipeline complete!",
        "─" * 42,
        f"  Files loaded       :  {report.total_loaded}",
        f"  Accepted           :  {report.total_accepted}  ({report.acceptance_rate:.1%})",
        f"  Rejected           :  {report.total_rejected}",
        f"  Exact duplicates   :  {report.exact_removed}",
        f"  Near  duplicates   :  {report.near_removed}",
        f"  Final corpus size  :  {report.total_after_dedup} documents",
        f"  Avg compression    :  {report.avg_compression:.1%}",
        "─" * 42,
    ]

    if errors:
        lines += ["", "⚠️  Load warnings:"] + errors

    if report.reject_reasons:
        lines += ["", "  Rejection breakdown:"]
        for reason, count in sorted(report.reject_reasons.items(), key=lambda x: -x[1]):
            lines.append(f"    {reason:<16} : {count}")

    return final_zip_path, final_jsonl_path, "\n".join(lines), preview_text


def create_ui():
    """Build and return the Gradio Blocks UI."""
    try:
        import gradio as gr
    except ImportError as exc:
        raise ImportError(
            "Gradio is required for the web UI.\n"
            "Install: pip install 'gradio>=4.15'"
        ) from exc

    with gr.Blocks(title="CorpusForge — Corpus Cleaner") as demo:

        gr.Markdown(
            """
# ⚡ CorpusForge
**Clean messy text corpora for AI/NLP pipelines.**

Upload `.txt` or `.pdf` files → the 5-stage pipeline runs automatically → download a ZIP archive with your cleaned `.txt` files.

> **Pipeline:** Load → Heuristic Clean → Quality Filter → Deduplication (MD5 + MinHash) → Export
"""
        )

        with gr.Row(equal_height=False):
            # ── LEFT COLUMN: Input ────────────────────────────────────────
            with gr.Column(scale=1):
                gr.Markdown("### 📂 Upload Files")
                file_input = gr.File(
                    label="Drop files here (TXT · PDF)",
                    file_count="multiple",
                    file_types=[".txt", ".pdf"],
                )

                with gr.Accordion("⚙️ Pipeline Settings", open=True):
                    lang_input = gr.Dropdown(
                        choices=["en", "fr", "de", "es", "it", "pt", "nl", "ru", "zh", "ja"],
                        value="en",
                        label="🌐 Target Language",
                        info="Documents not matching this language will be rejected.",
                    )
                    min_chars_input = gr.Slider(
                        minimum=0,
                        maximum=1000,
                        value=100,
                        step=50,
                        label="📏 Minimum Characters",
                        info="Documents shorter than this (after cleaning) are rejected.",
                    )
                    max_rep_input = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        value=0.20,
                        step=0.05,
                        label="🔁 Max Repetition Ratio",
                        info="Documents with more repetition than this are rejected.",
                    )
                    skip_near_input = gr.Checkbox(
                        value=False,
                        label="⚡ Skip Near-Deduplication (MinHash)",
                        info="Faster — skips the MinHash LSH near-dedup pass.",
                    )
                
                with gr.Accordion("🤖 Advanced ML Cleaners (Slower)", open=False):
                    enable_pii_input = gr.Checkbox(
                        value=False,
                        label="🕵️ Advanced PII Redaction (spaCy NER)",
                        info="Detects and redacts human names, organizations, and locations.",
                    )
                    enable_ocr_input = gr.Checkbox(
                        value=False,
                        label="📖 OCR Auto-Correction (SymSpell)",
                        info="Detects and auto-corrects corrupted words like 'awes0me' -> 'awesome'.",
                    )

                with gr.Row():
                    run_btn   = gr.Button("🚀 Run Pipeline", variant="primary", scale=3)
                    clear_btn = gr.ClearButton(scale=1)

            # ── RIGHT COLUMN: Results ─────────────────────────────────────
            with gr.Column(scale=1):
                gr.Markdown("### 📊 Results")
                
                with gr.Tabs():
                    with gr.Tab("📝 Preview (First File)"):
                        preview_output = gr.Textbox(
                            label="Cleaned Text Preview",
                            lines=12,
                            max_lines=20,
                            interactive=False,
                            show_copy_button=True,
                        )
                    with gr.Tab("📈 Report"):
                        report_output = gr.Textbox(
                            label="Pipeline Report",
                            lines=12,
                            max_lines=20,
                            interactive=False,
                        )
                        
                with gr.Row():
                    jsonl_output = gr.File(
                        label="📄 Download .jsonl",
                        interactive=False,
                    )
                    file_output = gr.File(
                        label="📦 Download .zip (All Files)",
                        interactive=False,
                    )

        # ── Wire up events ────────────────────────────────────────────────
        run_btn.click(
            fn=_run_pipeline_on_files,
            inputs=[
                file_input,
                lang_input,
                min_chars_input,
                max_rep_input,
                skip_near_input,
                enable_pii_input,
                enable_ocr_input,
            ],
            outputs=[file_output, jsonl_output, report_output, preview_output],
        )

        clear_btn.add([file_input, file_output, jsonl_output, report_output, preview_output])

        # ── Footer ────────────────────────────────────────────────────────
        gr.Markdown(
            """
---
**CorpusForge v0.1.0** — 8-component NLP corpus cleaning pipeline.  
Components: `Loaders` · `HeuristicCleaner` · `QualityFilter` · `Deduplicator` · `CorpusFormatter` · `CLI` · `Web UI`
"""
        )

    return demo


def main() -> None:
    """Entry point — run with: PYTHONPATH=. python -m src.corpusforge.app"""
    import gradio as gr

    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        theme=gr.themes.Soft(),
        show_error=True,       # surface Python tracebacks in the UI
    )


if __name__ == "__main__":
    main()
