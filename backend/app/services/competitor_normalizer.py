"""Competitor name normalizer — shared by Idea Validation and Market Research.

Rules:
  - Deduplicate (case-insensitive)
  - Strip common suffixes: Inc, Ltd, AI, Platform, Software, Solutions, etc.
  - Keep MAX 2 words
  - Limit list to top 8 competitors
  - Reject names that look like article titles (>3 words)
"""

from __future__ import annotations

import re
from typing import List

# Suffixes to strip from company names (case-insensitive)
_STRIP_SUFFIXES: tuple[str, ...] = (
    "inc", "ltd", "llc", "corp", "corporation", "co",
    "ai", "platform", "software", "solutions", "services",
    "tool", "tools", "app", "apps", "technology", "technologies",
    "group", "global", "labs", "studio", "studios",
    "discovery", "systems", "network", "networks",
)

# Words that indicate an article title, not a company
_ARTICLE_SIGNALS: tuple[str, ...] = (
    "top", "best", "how", "what", "why", "review", "comparison",
    "guide", "list", "ways", "things", "tips", "report",
    "february", "march", "april", "january", "may", "june",
    "july", "august", "september", "october", "november", "december",
)

_MAX_COMPETITORS = 8
_MAX_WORDS = 2


def normalize_competitor_name(raw_name: str) -> str | None:
    """Normalize a single competitor name.

    Returns None if the name is invalid (too long, article title, etc.).
    """
    name = raw_name.strip()
    if not name:
        return None

    # Reject if it looks like an article title
    lower = name.lower()
    for signal in _ARTICLE_SIGNALS:
        if signal in lower:
            return None

    # Strip parenthetical content
    name = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()

    # Split into words, strip suffixes from the end
    words = name.split()
    while words and words[-1].lower().rstrip(".,") in _STRIP_SUFFIXES:
        words.pop()

    # Also strip suffixes from the beginning if they're generic
    while words and words[0].lower().rstrip(".,") in _STRIP_SUFFIXES:
        words.pop(0)

    if not words:
        return None

    # Keep max 2 words
    words = words[:_MAX_WORDS]

    # Capitalize properly
    result = " ".join(w.capitalize() if w.islower() else w for w in words)

    # Reject if too short or too generic
    if len(result) < 2:
        return None

    return result


def normalize_competitor_list(raw_names: List[str]) -> List[str]:
    """Normalize and deduplicate a list of competitor names.

    Returns at most _MAX_COMPETITORS unique names, each ≤ 2 words.
    """
    seen: set[str] = set()
    result: list[str] = []

    for raw in raw_names:
        normalized = normalize_competitor_name(raw)
        if normalized is None:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
        if len(result) >= _MAX_COMPETITORS:
            break

    return result
