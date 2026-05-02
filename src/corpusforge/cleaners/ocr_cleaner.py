"""
OCR Artifact Cleaner — Uses SymSpell to correct words corrupted with numbers (e.g., l0rem -> lorem).
"""
import re
from typing import Optional

try:
    from symspellpy import SymSpell
    import importlib.resources
    _HAS_SYMSPELL = True
except ImportError:
    _HAS_SYMSPELL = False

class OcrCleaner:
    def __init__(self, enable: bool = True):
        self.enable = enable
        self.sym_spell: Optional[SymSpell] = None
        self._numeric_word_pattern = re.compile(r'\b[a-zA-Z]*\d+[a-zA-Z0-9]*\b')
        
        if self.enable and _HAS_SYMSPELL:
            self._init_symspell()
            
    def _init_symspell(self):
        # max_dictionary_edit_distance=2 is standard
        self.sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        try:
            dictionary_path = importlib.resources.files("symspellpy") / "frequency_dictionary_en_82_765.txt"
            self.sym_spell.load_dictionary(str(dictionary_path), term_index=0, count_index=1)
        except Exception:
            self.sym_spell = None

    def _correct_word(self, word: str) -> str:
        if not self.sym_spell:
            return word
            
        # We only want to correct words that contain numbers but aren't pure numbers
        if word.isdigit():
            return word
            
        # Convert leetspeak numbers back to common letters for better SymSpell chances
        # e.g., 0->o, 1->i, 3->e, 4->a, 5->s
        normalized = word.lower()
        normalized = normalized.replace('0', 'o').replace('1', 'i').replace('3', 'e')
        normalized = normalized.replace('4', 'a').replace('5', 's').replace('7', 't')
        
        suggestions = self.sym_spell.lookup(
            normalized, verbosity=1, max_edit_distance=2
        )
        if suggestions:
            # Return the best suggestion
            # Preserve original casing if possible, but for simplicity we return lower
            return suggestions[0].term
        return word

    def correct_ocr_artifacts(self, text: str) -> str:
        """
        Finds words with numbers embedded in them (e.g. "awes0me") and tries to correct them.
        """
        if not self.enable or not self.sym_spell:
            return text

        def replace_match(match):
            original = match.group(0)
            corrected = self._correct_word(original)
            # Match original case if title
            if original.istitle():
                return corrected.capitalize()
            elif original.isupper():
                return corrected.upper()
            return corrected

        # Find words containing at least one digit and replace them
        return self._numeric_word_pattern.sub(replace_match, text)
