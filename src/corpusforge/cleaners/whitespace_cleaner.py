import re

# Compiled once at module level — never inside a function.
_HORIZ_WS    = re.compile(r"[^\S\n]+")       # spaces/tabs, NOT newlines
_MULTI_NL    = re.compile(r"\n{3,}")          # 3 or more newlines
_PAGE_NUM    = re.compile(r"^\s*\d+\s*$", re.MULTILINE)
_PAGE_MARK = re.compile(
    r"""
    ^\s*                             # start of line + optional whitespace
    (?:page\s*)?                     # optional 'page'
    \d+                              # current page
    \s*
    (?:of|/)                         # 'of' or '/'
    \s*
    \d+                              # total pages
    \s*$
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)
_URL         = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_SOFT_HYPHEN = re.compile(r"-\n(\w)")         # PDF line-break hyphen




def normalise_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs → single space. Max 2 newlines."""

    # Detect ORIGINAL padding (only spaces, not tabs)
    strip_leading = text.startswith(" ")
    strip_trailing = text.endswith(" ")

    text = _HORIZ_WS.sub(" ", text)
    text = _MULTI_NL.sub("\n\n", text)

    # Apply conditional strip
    if strip_leading and strip_trailing:
        text = text.strip()
    elif strip_leading:
        text = text.lstrip()
    elif strip_trailing:
        text = text.rstrip()
    # else: keep as-is (important for tab→space case)

    return text


def remove_urls(text: str) -> str:
    """Replace URLs with a single space (space prevents word merging)."""
    return _URL.sub(" ", text)


def remove_page_markers(text: str) -> str:
    """Remove standalone page numbers and 'Page X of Y' markers."""
    text = _PAGE_NUM.sub("", text)
    text = _PAGE_MARK.sub("", text)
    return text


def fix_pdf_hyphenation(text: str) -> str:
    """Join words split by PDF line-break hyphens: 'exam-\\nines' → 'examines'."""
    return _SOFT_HYPHEN.sub(r"\1", text)