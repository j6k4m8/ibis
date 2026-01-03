"""Transcription utilities and tagging."""

from __future__ import annotations

import re
from collections import Counter


STOPWORDS = {
    "the",
    "and",
    "a",
    "an",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "that",
    "this",
    "is",
    "are",
    "it",
    "we",
    "you",
    "i",
}


def extract_tags_from_transcript(text: str, limit: int = 8) -> list[str]:
    """Extract candidate tags from transcript text.

    Args:
        text: Transcript text.
        limit: Maximum number of tags to return.

    Returns:
        list[str]: Tag list ordered by relevance.
    """

    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9-]+", text.lower())
    tokens = [token for token in tokens if token not in STOPWORDS]
    counts = Counter(tokens)
    return [token for token, _ in counts.most_common(limit)]
