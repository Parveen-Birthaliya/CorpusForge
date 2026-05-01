import pytest
from pathlib import Path

from src.corpusforge.loaders import TxtLoader, PdfLoader
from src.corpusforge.loaders.base import BaseLoader
from src.corpusforge.models import Document

# Fixtures

@pytest.fixture
def sample_txt(tmp_path: Path) -> Path:
    """A simple, valid UTF-8 text file."""
    f = tmp_path / "sample.txt"
    f.write_text(
        "The quick brown fox jumps over the lazy dog.",
        encoding="utf-8",
    )
    return f


@pytest.fixture
def bom_txt(tmp_path: Path) -> Path:
    """UTF-8 file with BOM (common from Windows Notepad)."""
    f = tmp_path / "bom_file.txt"
    f.write_bytes(b"\xef\xbb\xbf" + "Hello BOM world.".encode("utf-8"))
    return f


@pytest.fixture
def latin1_txt(tmp_path: Path) -> Path:
    """File encoded in Latin-1 (common in older European documents)."""
    f = tmp_path / "latin1.txt"
    f.write_bytes("Ã©lÃ¨ve".encode("latin-1"))  # é l è v e
    return f

# TxtLoader — can_handle

class TestTxtLoaderCanHandle:

    @pytest.mark.parametrize("filename,expected", [
        ("file.txt",  True),
        ("file.TXT",  True),   # case-insensitive
        ("file.Txt",  True),
        ("file.pdf",  False),
        ("file.html", False),
        ("file",      False),  # no extension
    ])
    def test_extensions(self, filename: str, expected: bool) -> None:
        loader = TxtLoader()
        assert loader.can_handle(Path(filename)) is expected


# TxtLoader — load (happy paths)

class TestTxtLoaderLoad:

    def test_returns_document(self, sample_txt: Path) -> None:
        doc = TxtLoader().load(sample_txt)
        assert isinstance(doc, Document)

    def test_text_content(self, sample_txt: Path) -> None:
        doc = TxtLoader().load(sample_txt)
        assert "quick brown fox" in doc.text

    def test_format_type(self, sample_txt: Path) -> None:
        doc = TxtLoader().load(sample_txt)
        assert doc.format_type == "txt"

    def test_char_count_is_set(self, sample_txt: Path) -> None:
        doc = TxtLoader().load(sample_txt)
        assert doc.char_count == len(doc.text)
        assert doc.char_count > 0

    def test_doc_id_stem(self, sample_txt: Path) -> None:
        doc = TxtLoader().load(sample_txt)
        assert doc.doc_id.startswith("sample")

    def test_doc_id_has_hash(self, sample_txt: Path) -> None:
        doc = TxtLoader().load(sample_txt)
        parts = doc.doc_id.split("_")
        assert len(parts) == 2
        assert len(parts[1]) == 8   # 8-char hex hash

    def test_source_path_is_absolute_or_matches(self, sample_txt: Path) -> None:
        doc = TxtLoader().load(sample_txt)
        assert doc.source_path == sample_txt

    def test_metadata_has_encoding(self, sample_txt: Path) -> None:
        doc = TxtLoader().load(sample_txt)
        assert "encoding_used" in doc.metadata

    def test_metadata_has_file_size(self, sample_txt: Path) -> None:
        doc = TxtLoader().load(sample_txt)
        assert doc.metadata["file_size_bytes"] > 0

    def test_bom_file_loads_cleanly(self, bom_txt: Path) -> None:
        """BOM should be stripped — not appear in the text."""
        doc = TxtLoader().load(bom_txt)
        assert "\ufeff" not in doc.text
        assert "Hello BOM world" in doc.text

    def test_latin1_file_loads(self, latin1_txt: Path) -> None:
        """Latin-1 file should load without raising."""
        doc = TxtLoader().load(latin1_txt)
        assert isinstance(doc, Document)
        assert len(doc.text) > 0

    def test_nfc_normalisation_applied(self, tmp_path: Path) -> None:
        """NFD characters should be normalised to NFC after loading."""
        import unicodedata
        # "café" in NFD — e + combining accent (2 code points)
        nfd_text = "cafe\u0301"
        f = tmp_path / "nfd.txt"
        f.write_text(nfd_text, encoding="utf-8")
        doc = TxtLoader().load(f)
        # After loading, should be NFC (single é code point)
        assert unicodedata.is_normalized("NFC", doc.text)


# TxtLoader — load (error paths)
class TestTxtLoaderErrors:

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            TxtLoader().load(tmp_path / "ghost.txt")

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        with pytest.raises(ValueError, match="empty"):
            TxtLoader().load(f)

    def test_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            TxtLoader().load(tmp_path)   # tmp_path is a dir


# PdfLoader — can_handle

class TestPdfLoaderCanHandle:

    @pytest.mark.parametrize("filename,expected", [
        ("paper.pdf",  True),
        ("paper.PDF",  True),
        ("paper.Pdf",  True),
        ("paper.txt",  False),
        ("paper.html", False),
    ])
    def test_extensions(self, filename: str, expected: bool) -> None:
        loader = PdfLoader()
        assert loader.can_handle(Path(filename)) is expected


class TestPdfLoaderErrors:

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            PdfLoader().load(tmp_path / "ghost.pdf")

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.pdf"
        f.write_bytes(b"")
        with pytest.raises(ValueError, match="empty"):
            PdfLoader().load(f)

    def test_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            PdfLoader().load(tmp_path)

class TestLoadMany:

    def test_loads_only_compatible_files(self, tmp_path: Path) -> None:
        txt = tmp_path / "a.txt"
        txt.write_text("Some text content here for testing.", encoding="utf-8")
        pdf_path = tmp_path / "b.pdf"
        pdf_path.write_bytes(b"fake")   # TxtLoader ignores .pdf

        docs = TxtLoader().load_many([txt, pdf_path])
        assert len(docs) == 1
        assert docs[0].format_type == "txt"

    def test_empty_list(self) -> None:
        docs = TxtLoader().load_many([])
        assert docs == []

    def test_multiple_txt_files(self, tmp_path: Path) -> None:
        for i in range(3):
            (tmp_path / f"doc{i}.txt").write_text(
                f"Document number {i}.", encoding="utf-8"
            )
        paths = list(tmp_path.glob("*.txt"))
        docs = TxtLoader().load_many(paths)
        assert len(docs) == 3


class TestAbstractEnforcement:

    def test_cannot_instantiate_base_loader(self) -> None:
        with pytest.raises(TypeError):
            BaseLoader()  # type: ignore

    def test_partial_subclass_raises(self) -> None:
        class IncompleteLoader(BaseLoader):
            def load(self, file_path: Path) -> Document:  # type: ignore
                ...
            # forgot can_handle → should raise TypeError on instantiation

        with pytest.raises(TypeError):
            IncompleteLoader()