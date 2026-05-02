DEFAULT_MIN_CHARS = 100


def passes_length(text: str, min_chars: int = DEFAULT_MIN_CHARS) -> bool:
    """Return True if text meets the minimum character threshold.

    Parameters
    ----------
    text      : Cleaned text to evaluate.
    min_chars : Minimum number of characters required (default 100).
    """
    return len(text.strip()) >= min_chars