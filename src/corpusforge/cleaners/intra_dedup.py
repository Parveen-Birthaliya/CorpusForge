"""
Intra-document deduplication — removes duplicate content within a single
document at both line and paragraph level.

Strategy:
  1. Line-level dedup within each paragraph (removes repeated lines).
  2. Paragraph-level dedup across the entire document.
  3. Sentence-level dedup: if a standalone paragraph is a substring of
     an earlier longer paragraph, drop the standalone repeat.
"""

import re

_SENTENCE_MIN_LEN = 40  # Only dedup sentences longer than this


def _normalize(text: str) -> str:
    """Collapse whitespace for comparison."""
    return re.sub(r"\s+", " ", text).strip().lower()


def remove_intra_doc_duplicates(text: str) -> str:
    """Remove duplicate paragraphs and lines within a single document."""

    paragraphs = text.split("\n\n")
    seen_paragraph_norms: set[str] = set()
    # Collect all long normalised paragraphs for substring checks
    long_paragraph_norms: list[str] = []
    unique_paragraphs: list[str] = []

    for p in paragraphs:
        # ── Step 1: line-level dedup within the paragraph ────────────
        lines = p.split("\n")
        seen_lines: set[str] = set()
        unique_lines: list[str] = []
        for line in lines:
            ln = _normalize(line)
            if not ln:
                unique_lines.append(line)
                continue
            if ln not in seen_lines:
                seen_lines.add(ln)
                unique_lines.append(line)

        deduped_p = "\n".join(unique_lines)

        # ── Step 2: paragraph-level exact dedup ──────────────────────
        p_norm = _normalize(deduped_p)
        if not p_norm:
            unique_paragraphs.append(deduped_p)
            continue

        if p_norm in seen_paragraph_norms:
            continue  # exact duplicate paragraph — skip

        # ── Step 3: sentence-level near-dedup ────────────────────────
        # If this paragraph is short (likely a standalone repetition)
        # and its normalised text is a substring of a previously seen
        # longer paragraph, skip it.
        is_substring_of_earlier = False
        if len(p_norm) >= _SENTENCE_MIN_LEN:
            for earlier in long_paragraph_norms:
                if len(p_norm) < len(earlier) and p_norm in earlier:
                    is_substring_of_earlier = True
                    break

        if is_substring_of_earlier:
            continue

        seen_paragraph_norms.add(p_norm)
        long_paragraph_norms.append(p_norm)
        unique_paragraphs.append(deduped_p)

    return "\n\n".join(unique_paragraphs)
