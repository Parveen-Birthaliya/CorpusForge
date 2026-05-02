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
    target_lang: str = Form("en"),
    min_chars: int = Form(100),
    max_rep: float = Form(0.20),
    skip_near_dedup: bool = Form(False),
    enable_advanced_pii: bool = Form(False),
    enable_ocr: bool = Form(False),
):
    """Run the CorpusForge pipeline on uploaded files."""
    
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
    
    # Extract preview text
    preview_text = ""
    if texts:
        first_doc_id = list(texts.keys())[0]
        preview_text = texts[first_doc_id]
        if len(preview_text) > 3000:
            preview_text = preview_text[:3000] + "\n\n... (truncated for preview)"

    # Build response payload
    response_data = {
        "status": "success",
        "preview_text": preview_text,
        "report": {
            "total_loaded": report.total_loaded,
            "total_accepted": report.total_accepted,
            "total_rejected": report.total_rejected,
            "exact_removed": report.exact_removed,
            "near_removed": report.near_removed,
            "total_after_dedup": report.total_after_dedup,
            "acceptance_rate": f"{report.acceptance_rate:.1%}",
            "avg_compression": f"{report.avg_compression:.1%}",
        },
        "errors": errors,
        "download_zip_url": f"/api/download/{out_dir.name}/{final_zip_name}",
        "download_jsonl_url": f"/api/download/{out_dir.name}/cleaned_corpus.jsonl"
    }

    return JSONResponse(content=response_data)


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
