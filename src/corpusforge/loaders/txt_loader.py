import hashlib
import unicodedata
from pathlib import Path

from src.corpusforge.loaders.base import BaseLoader
from src.corpusforge.models import Document

# Encodings to try, in priority order.
# latin-1 is the guaranteed fallback: every byte 0-255 is valid.

_ENCODING_CHAIN: list[str] = ["utf-8-sig", "utf-8", "latin-1"]


def _make_doc_id(file_path: Path) -> str:
    """
    Generate a stable, human-readable document ID.
    """
    path_hash = hashlib.md5(
        str(file_path.resolve()).encode("utf-8")
    ).hexdigest()[:8]
    return f"{file_path.stem}_{path_hash}"


def _read_with_fallback(file_path: Path) -> tuple[str, str]:
    """
    Read file text, trying each encoding in _ENCODING_CHAIN.
    """
    for encoding in _ENCODING_CHAIN:
        try:
            text = file_path.read_text(encoding=encoding)
            return text, encoding
        except UnicodeDecodeError:
            continue
    raise RuntimeError(
        f"All encodings {_ENCODING_CHAIN} failed for: {file_path}"
    )


class TxtLoader(BaseLoader):
    """Loads plain text (.txt) files."""

    def can_handle(self, file_path: Path) -> bool:
        """Return True for .txt files (case-insensitive)."""
        return file_path.suffix.lower() == ".txt"

    def load(self, file_path: Path) -> Document:
        """
        Load a .txt file into a Document.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        if file_path.stat().st_size == 0:
            raise ValueError(f"File is empty: {file_path}")

        text, encoding_used = _read_with_fallback(file_path)

        text = unicodedata.normalize("NFC", text)

        # Build Document
        stat = file_path.stat()
        return Document(
            doc_id=_make_doc_id(file_path),
            text=text,
            source_path=file_path,
            format_type="txt",
            char_count=len(text),
            metadata={
                "encoding_used":   encoding_used,
                "file_size_bytes": stat.st_size,
                "modified_at":     stat.st_mtime,
            },
        )