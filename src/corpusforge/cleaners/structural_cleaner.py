"""
Structural noise remover — strips boilerplate, headers, footers,
HTML artifacts, web noise, PII markers, disclaimers, and separators.
"""

import re

# ── PII Patterns ─────────────────────────────────────────────────────────
_PII_PATTERNS = [
    # Email: ... (standalone line)
    re.compile(r"^\s*Email:\s*\S+@\S+.*$", re.IGNORECASE | re.MULTILINE),
    # Phone: ... (handles digits, letters like 1-800-TECH, extensions)
    re.compile(r"^\s*Phone:\s*[\+\d\-\(\) \t\w\.]+$", re.IGNORECASE | re.MULTILINE),
    # Contact: ... (standalone line)
    re.compile(r"^\s*(?:Emergency\s+)?Contact:\s*.+$", re.IGNORECASE | re.MULTILINE),
    # Posted by: email@domain  (blog metadata)
    re.compile(r"^\s*Posted\s+by:\s*\S+@\S+.*$", re.IGNORECASE | re.MULTILINE),
]

# ── Document Structure Markers ───────────────────────────────────────────
_STRUCTURE_PATTERNS = [
    # CHAPTER X
    re.compile(r"^\s*CHAPTER\s+\d+\s*$", re.IGNORECASE | re.MULTILINE),
    # END OF DOCUMENT
    re.compile(r"^\s*END OF DOCUMENT\s*$", re.IGNORECASE | re.MULTILINE),
    # --- END --- (and similar markers)
    re.compile(r"^\s*-{2,}\s*END\s*-{2,}\s*$", re.IGNORECASE | re.MULTILINE),
    # TABLE OF CONTENTS (standalone header)
    re.compile(r"^\s*TABLE OF CONTENTS\s*$", re.IGNORECASE | re.MULTILINE),
]

# ── Footer / Header Boilerplate ──────────────────────────────────────────
_BOILERPLATE_PATTERNS = [
    # "Footer" at start of line followed by anything (catches all Footer variants):
    #   Footer text - Confidential
    #   Footer - Page 10
    #   Footer Confidential
    #   Footer - Confidential Medical Record
    re.compile(r"^\s*Footer\b.*$", re.IGNORECASE | re.MULTILINE),
    # Disclaimer lines
    re.compile(r"^\s*DISCLAIMER:?\s*.*$", re.IGNORECASE | re.MULTILINE),
    # Copyright lines: © 20XX ...
    re.compile(r"^\s*©\s*\d{4}.*$", re.MULTILINE),
    # "All rights reserved" lines
    re.compile(r"^.*All rights reserved\.?\s*$", re.IGNORECASE | re.MULTILINE),
    # "Unauthorized reproduction/disclosure" lines
    re.compile(r"^.*Unauthorized\s+(?:reproduction|disclosure|distribution).*$", re.IGNORECASE | re.MULTILINE),
    # Confidential standalone lines
    re.compile(r"^\s*Confidential\s*[-–—]?\s*.*$", re.IGNORECASE | re.MULTILINE),
    # Privacy Policy | Terms of Service lines
    re.compile(r"^\s*(?:Privacy Policy|Terms of Service|Cookie Policy)(?:\s*\|.*)*\s*$", re.IGNORECASE | re.MULTILINE),
]

# ── Web / Blog Noise ────────────────────────────────────────────────────
_WEB_NOISE_PATTERNS = [
    # HTML document structure tags (standalone lines or inline)
    re.compile(r"</?(?:!DOCTYPE|html|head|body|script|style|meta|link|br|hr)\b[^>]*>", re.IGNORECASE),
    # <title>...</title> block
    re.compile(r"<title>[^<]*</title>", re.IGNORECASE),
    # Share on Twitter | Share on LinkedIn ...
    re.compile(r"^\s*Share\s+(?:on|this|via)\s+.*$", re.IGNORECASE | re.MULTILINE),
    # Navigation: Home > ...
    re.compile(r"^\s*Navigation:.*$", re.IGNORECASE | re.MULTILINE),
    # SUBSCRIBE TO OUR NEWSLETTER
    re.compile(r"^\s*SUBSCRIBE\s+TO\s+.*$", re.IGNORECASE | re.MULTILINE),
    # Advertisement lines
    re.compile(r"^\s*Advertisement:.*$", re.IGNORECASE | re.MULTILINE),
    # Cookie notice lines
    re.compile(r"^\s*Cookie\s+(?:notice|policy|consent):?.*$", re.IGNORECASE | re.MULTILINE),
    # "Visit ... for more info" — catches both with URL and stub after URL removal
    re.compile(r"^\s*Visit\s+.*for more info\.?\s*$", re.IGNORECASE | re.MULTILINE),
    # Separator lines (=== or ---, 3+ chars, entire line)
    re.compile(r"^\s*[=\-]{3,}\s*$", re.MULTILINE),
    # Follow us: ...
    re.compile(r"^\s*Follow\s+us:?.*$", re.IGNORECASE | re.MULTILINE),
    # Stub lines left after URL removal (Read more:, See also:, Website:, etc.)
    re.compile(r"^\s*(?:Read more|See also|Share this article|Website|Source):?\s*$", re.IGNORECASE | re.MULTILINE),
    # RELATED POSTS: header
    re.compile(r"^\s*RELATED POSTS:?\s*$", re.IGNORECASE | re.MULTILINE),
    # Comments section headers
    re.compile(r"^\s*Comments\s*\(\d+\):?\s*$", re.IGNORECASE | re.MULTILINE),
    # Comment lines: user123: "..."
    re.compile(r"^\s*\w+:\s*\"[^\"]*\"\s*$", re.MULTILINE),
]

# Combine all pattern groups in order of application
_ALL_PATTERNS = (
    _PII_PATTERNS
    + _STRUCTURE_PATTERNS
    + _BOILERPLATE_PATTERNS
    + _WEB_NOISE_PATTERNS
)


def remove_structural_noise(text: str) -> str:
    """Remove known boilerplate, headers, footers, PII markers, and web noise.

    Each pattern is applied as a line-level removal (the entire matching
    line is deleted).  The caller is expected to run whitespace
    normalisation *after* this function to collapse resulting blank lines.
    """
    for pattern in _ALL_PATTERNS:
        text = pattern.sub("", text)
    return text
