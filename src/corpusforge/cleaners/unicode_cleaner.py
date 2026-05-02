import unicodedata

# Control characters to remove (category "Cc"), except newline and tab.
_KEEP_CONTROL = {"\n", "\t"}
_REMOVE_CATEGORIES = {"Cc", "Cf", "Cs", "Co"}


def normalise_unicode(text: str) -> str:
    """NFC-normalise text so all characters use composed form."""
    return unicodedata.normalize("NFC", text)


def remove_control_characters(text: str) -> str:
    """Strip non-printable control characters and stray BOMs."""
    # Remove literal string BOMs often caused by bad JSON extraction
    text = text.replace(r"\ufeff", "").replace(r"\ufffe", "")
    
    return "".join(
        c for c in text
        if unicodedata.category(c) not in _REMOVE_CATEGORIES
        or c in _KEEP_CONTROL
    )