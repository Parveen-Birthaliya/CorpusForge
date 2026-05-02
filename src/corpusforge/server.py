"""
CorpusForge FastAPI Backend

Exposes the core NLP cleaning pipeline as REST endpoints, decoupling it
from Gradio to allow for a custom UIland-style frontend.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.corpusforge.cleaners import HeuristicCleaner
from src.corpusforge.dedup import Deduplicator
from src.corpusforge.filters import QualityFilter
from src.corpusforge.loaders import PdfLoader, TxtLoader
from src.corpusforge.models import Document
from src.corpusforge.output import CorpusFormatter

app = FastAPI(title="CorpusForge API")


@app.post("/api/clean")
async def clean_corpus(
    files: List[UploadFile] = File(...),
):
    """Run the CorpusForge pipeline on uploaded files."""

    # Hardcoded defaults — sidebar settings removed from UI
    # Advanced ML cleaners are ALWAYS ON (no UI toggle needed)
    target_lang         = "en"
    min_chars           = 100
    max_rep             = 0.20
    skip_near_dedup     = False
    enable_advanced_pii = True   # spaCy NER — always redact PII
    enable_ocr          = True   # SymSpell OCR correction — always on

    # ── Stage 0: Save uploaded files to temp directory ────────────────────
    input_dir = Path(tempfile.mkdtemp(prefix="corpusforge_in_"))
    file_paths: list[Path] = []
    
    for uploaded_file in files:
        if uploaded_file.filename:
            file_path = input_dir / uploaded_file.filename
            with file_path.open("wb") as f:
                f.write(await uploaded_file.read())
            file_paths.append(file_path)

    if not file_paths:
        return JSONResponse(status_code=400, content={"error": "No valid files uploaded."})

    # Initialize components
    loaders = [TxtLoader(), PdfLoader()]
    cleaner = HeuristicCleaner(enable_advanced_pii=enable_advanced_pii, enable_ocr=enable_ocr)
    quality = QualityFilter(min_chars=min_chars, target_lang=target_lang, max_rep=max_rep)
    deduplicator = Deduplicator(skip_near=skip_near_dedup)

    out_dir = Path(tempfile.mkdtemp(prefix="corpusforge_out_"))
    formatter = CorpusFormatter(out_dir)

    # ── Stage 1: Load ────────────────────────────────────────────────────
    docs: list[Document] = []
    errors: list[str] = []

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
        return JSONResponse(status_code=400, content={"error": "No files could be loaded."})

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

    # Create ZIP archive
    zip_path = str(out_dir / "corpusforge_results")
    shutil.make_archive(zip_path, 'zip', out_dir)
    final_zip_name = "corpusforge_results.zip"
    
    # ── Build preview / inspection data ──────────────────────────────────
    raw_preview     = ""
    cleaned_preview = ""
    garbage_lines   = []

    # Always use the FIRST document for the Before/After view
    if cleaning_results:
        first_cr  = cleaning_results[0]
        first_doc = next((d for d in docs if d.doc_id == first_cr.doc_id), None)

        raw_full     = (first_doc.text if first_doc else "").strip()
        cleaned_full = first_cr.cleaned_text.strip()

        LIMIT = 5000
        raw_preview     = raw_full[:LIMIT]     + ("\n\n…(truncated)" if len(raw_full)     > LIMIT else "")
        cleaned_preview = cleaned_full[:LIMIT]  + ("\n\n…(truncated)" if len(cleaned_full) > LIMIT else "")

        # Garbage = lines in raw that vanished after cleaning
        cleaned_line_set = {ln.strip() for ln in cleaned_full.splitlines() if ln.strip()}
        for line in raw_full.splitlines():
            stripped = line.strip()
            if stripped and stripped not in cleaned_line_set:
                garbage_lines.append(stripped)
                if len(garbage_lines) >= 100:
                    break

    # Duplicates: collect removed doc snippets from the correct list field
    duplicate_previews = []
    removed_ids = getattr(dedup_result, "removed_ids", [])
    for doc_id in removed_ids:
        orig = next((d for d in docs if d.doc_id == doc_id), None)
        if orig:
            duplicate_previews.append({
                "id":   doc_id,
                "text": orig.text[:500] + ("…" if len(orig.text) > 500 else ""),
            })
        if len(duplicate_previews) >= 10:
            break

    # ── Final response ────────────────────────────────────────────────────
    return JSONResponse(content={
        "status":             "success",
        "raw_preview":        raw_preview,
        "cleaned_preview":    cleaned_preview,
        "garbage_lines":      garbage_lines,
        "duplicate_previews": duplicate_previews,
        "report": {
            "total_loaded":      report.total_loaded,
            "total_accepted":    report.total_accepted,
            "total_rejected":    report.total_rejected,
            "exact_removed":     report.exact_removed,
            "near_removed":      report.near_removed,
            "total_after_dedup": report.total_after_dedup,
            "acceptance_rate":   f"{report.acceptance_rate:.1%}",
            "avg_compression":   f"{report.avg_compression:.1%}",
        },
        "errors":             errors,
        "download_zip_url":   f"/api/download/{out_dir.name}/{final_zip_name}",
        "download_jsonl_url": f"/api/download/{out_dir.name}/cleaned_corpus.jsonl",
    })


@app.get("/api/download/{folder}/{filename}")
async def download_file(folder: str, filename: str):
    """Serve the generated files for download."""
    # Ensure no directory traversal
    if ".." in folder or ".." in filename:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
        
    file_path = Path(tempfile.gettempdir()) / folder / filename
    if not file_path.exists():
        return JSONResponse(status_code=404, content={"error": "File not found"})
        
    return FileResponse(path=file_path, filename=filename)


# Mount the frontend static files at the root
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    @app.get("/")
    def index():
        return {"message": "Frontend not found. Please run the frontend build step."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.corpusforge.server:app", host="0.0.0.0", port=7860, reload=True)
