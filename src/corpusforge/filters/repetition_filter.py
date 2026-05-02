"""Repetition-based quality filter using 5-gram frequency."""

DEFAULT_MAX_RATIO = 0.20    # reject if top 5-gram covers > 20 % of text


def repetition_ratio(text: str, n: int = 5) -> float:
    """Compute the fraction of n-grams covered by the most-repeated one.

    A ratio of 0.0 means no repetition.
    A ratio of 1.0 means the entire text is one repeated phrase.

    Parameters
    ----------
    text : Cleaned text to evaluate.
    n    : N-gram size (default 5 words).
    """
    words = text.split()
    if len(words) < n:
        return 0.0

    ngrams = [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]

    counts: dict[tuple, int] = {}
    for ng in ngrams:
        counts[ng] = counts.get(ng, 0) + 1

    max_count = max(counts.values())
    return max_count / len(ngrams)


def passes_repetition(
    text: str,
    max_ratio: float = DEFAULT_MAX_RATIO,
) -> bool:
    """Return True if text is not excessively repetitive.

    Parameters
    ----------
    text      : Cleaned text to evaluate.
    max_ratio : Maximum allowed repetition ratio (default 0.20 = 20 %).
    """
    return repetition_ratio(text) <= max_ratio