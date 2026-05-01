import hashlib
import unicodedata
from pathlib import Path

from src.corpusforge.loaders.base import BaseLoader
from src.corpusforge.models import Document


def _make_doc_id(file_path: Path) -> str:
    """Generate stable doc ID"""
    path_hash = hashlib.md5(
        str(file_path.resolve()).encode("utf-8")
    ).hexdigest()[:8]
    return f"{file_path.stem}_{path_hash}"


def _extract_pdf_text(file_path: Path) -> tuple[str, dict]:
    """
    Extract text from all pages of a PDF.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise ImportError(
            "PyMuPDF is required for PDF loading.\n"
            "Install it with: pip install PyMuPDF"
        ) from e

    doc = fitz.open(str(file_path))

    # Validation
    if doc.is_encrypted:
        doc.close()
        raise ValueError(f"PDF is password-protected: {file_path}")

    if doc.page_count == 0:
        doc.close()
        raise ValueError(f"PDF has no pages: {file_path}")

    # Extraction
    pages_text: list[str] = []
    for page_num in range(len(doc)):
        page_text = doc[page_num].get_text()
        if page_text.strip():               # skip blank / image-only pages
            pages_text.append(page_text)

    # Metadata
    pdf_meta = doc.metadata or {}
    metadata = {
        "page_count":   doc.page_count,
        "filled_pages": len(pages_text),
        "pdf_title":    pdf_meta.get("title", ""),
        "pdf_author":   pdf_meta.get("author", ""),
        "pdf_creator":  pdf_meta.get("creator", ""),
    }

    doc.close()

    full_text = "\n\n".join(pages_text)
    return full_text, metadata


class PdfLoader(BaseLoader):
    """Loads PDF (.pdf) files using PyMuPDF."""

    def can_handle(self, file_path: Path) -> bool:
        """Return True for .pdf files (case-insensitive)."""
        return file_path.suffix.lower() == ".pdf"

    def load(self, file_path: Path) -> Document:
        """
        Load a .pdf file into a Document.
        """
        # Guards
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        if file_path.stat().st_size == 0:
            raise ValueError(f"File is empty: {file_path}")

        # Extract
        text, metadata = _extract_pdf_text(file_path)

        # NFC normalise for consistency
        text = unicodedata.normalize("NFC", text)

        metadata["file_size_bytes"] = file_path.stat().st_size

        # Build Document
        return Document(
            doc_id=_make_doc_id(file_path),
            text=text,
            source_path=file_path,
            format_type="pdf",
            char_count=len(text),
            metadata=metadata,
        )
