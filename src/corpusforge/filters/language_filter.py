"""Language detection filter using langdetect.

Install: pip install langdetect
"""
from langdetect import DetectorFactory, LangDetectException, detect

# Fix langdetect's non-determinism — must be set once at module level.
DetectorFactory.seed = 42


def detect_language(text: str) -> str | None:
    """Detect the dominant language of text.

    Returns
    -------
    ISO 639-1 language code ('en', 'fr', 'de', ...) or None if detection
    fails (text too short, ambiguous, or empty).
    """
    try:
        return detect(text)
    except LangDetectException:
        return None


def passes_language(
    text: str,
    target_lang: str = "en",
    allow_unknown: bool = True,
) -> bool:
    """Return True if text is in the target language.

    Parameters
    ----------
    text         : Cleaned text to evaluate.
    target_lang  : Expected ISO 639-1 code (default 'en').
    allow_unknown: If True, documents whose language cannot be detected
                   are accepted (not rejected). Safer for short texts.
    """
    lang = detect_language(text)
    if lang is None:
        return allow_unknown
    return lang == target_lang