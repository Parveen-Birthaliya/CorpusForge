from dataclasses import dataclass

from src.corpusforge.models import Document
from src.corpusforge.cleaners.unicode_cleaner import (
    normalise_unicode,
    remove_control_characters,
)
from src.corpusforge.cleaners.whitespace_cleaner import (
    normalise_whitespace,
    remove_urls,
    remove_page_markers,
    fix_hyphenation,
)
from src.corpusforge.cleaners.structural_cleaner import remove_structural_noise
from src.corpusforge.cleaners.intra_dedup import remove_intra_doc_duplicates
from src.corpusforge.cleaners.advanced_pii_cleaner import AdvancedPiiCleaner
from src.corpusforge.cleaners.ocr_cleaner import OcrCleaner


@dataclass
class CleaningResult:
    """Output of HeuristicCleaner.clean()."""

    doc_id:          str
    original_length: int
    cleaned_length:  int
    cleaned_text:    str
    format_type:     str

    @property
    def compression_ratio(self) -> float:
        """Fraction of text removed. 0.0 = nothing removed."""
        if self.original_length == 0:
            return 0.0
        return 1.0 - (self.cleaned_length / self.original_length)

    @property
    def is_significantly_reduced(self) -> bool:
        """True if more than 30% of original text was removed."""
        return self.compression_ratio > 0.30


class HeuristicCleaner:
    """
    Text cleaner pipeline.
    Combines fast regex heuristics with optional advanced ML cleaners (NER, OCR).
    """

    def __init__(self, enable_advanced_pii: bool = False, enable_ocr: bool = False):
        self.advanced_pii = AdvancedPiiCleaner(enable=enable_advanced_pii)
        self.ocr = OcrCleaner(enable=enable_ocr)

    def clean(self, doc: Document) -> CleaningResult:
        """Clean a Document and return a CleaningResult.
        """
        original_length = len(doc.text)
        text = doc.text

        # Step 1 — Unicode (must be first)
        text = normalise_unicode(text)

        # Step 2 — Control characters
        text = remove_control_characters(text)

        # Step 3 — Format-specific & Hyphenation
        text = fix_hyphenation(text)
        if doc.format_type == "txt":
            text = text.replace("\r\n", "\n")   # Windows line endings
            
        # Step 4 — URLs & Structural Noise
        text = remove_urls(text)
        text = remove_page_markers(text)
        text = remove_structural_noise(text)
        
        # Step 5 — Advanced ML Cleaners (Optional)
        text = self.advanced_pii.redact_pii(text)
        text = self.ocr.correct_ocr_artifacts(text)
        
        # Step 6 — Intra-document Deduplication
        text = remove_intra_doc_duplicates(text)

        # Step 7 — Whitespace (must be last to collapse everything)
        text = normalise_whitespace(text)

        return CleaningResult(
            doc_id=doc.doc_id,
            original_length=original_length,
            cleaned_length=len(text),
            cleaned_text=text,
            format_type=doc.format_type,
        )