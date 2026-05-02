"""
Advanced PII Cleaner — Uses spaCy NER to redact human names, locations, and organizations.
"""
import re

try:
    import spacy
    _HAS_SPACY = True
except ImportError:
    _HAS_SPACY = False

class AdvancedPiiCleaner:
    def __init__(self, enable: bool = True):
        self.enable = enable
        self.nlp = None
        if self.enable and _HAS_SPACY:
            try:
                # Disable unnecessary pipeline components for speed
                self.nlp = spacy.load("en_core_web_sm", disable=["parser", "attribute_ruler", "lemmatizer"])
            except OSError:
                # Model not downloaded yet
                pass

    def redact_pii(self, text: str) -> str:
        """
        Redacts PERSON, ORG, and GPE (Location) entities.
        """
        if not self.enable or not self.nlp:
            return text
            
        doc = self.nlp(text)
        
        # We need to process from back to front so replacement offsets don't shift
        replacements = []
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE"):
                start = ent.start_char
                end = ent.end_char
                text_slice = text[start:end]
                
                l_strip_len = len(text_slice) - len(text_slice.lstrip())
                r_strip_len = len(text_slice) - len(text_slice.rstrip())
                
                real_start = start + l_strip_len
                real_end = end - r_strip_len
                
                if real_start < real_end:
                    replacements.append((real_start, real_end, f"[{ent.label_}]"))
                
        # Sort in reverse order by start_char
        replacements.sort(key=lambda x: x[0], reverse=True)
        
        result_chars = list(text)
        for start, end, label in replacements:
            # Replace the slice
            result_chars[start:end] = list(label)
            
        return "".join(result_chars)
