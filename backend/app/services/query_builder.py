"""Deterministic Query & Keyword Builder.

Converts a structured Idea ORM instance into a reusable QueryBundle consumed
by every downstream data agent (trends, reddit, competitors).

Rules
-----
- NO LLM calls
- NO randomness
- NO external API calls
- Pure transformation: same input → same output
"""

from __future__ import annotations

import re
from typing import List

from ..models.idea import Idea
from ..schemas.query_schema import QueryBundle
from .exa_queries import build_exa_queries

# ---------------------------------------------------------------------------
# Stop-words stripped when tokenising free-text fields.  Kept intentionally
# small so that domain-specific words are never accidentally removed.
# ---------------------------------------------------------------------------
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "be", "been",
        "this", "that", "it", "its", "we", "our", "they", "their", "using",
        "based", "which", "who", "how", "what", "where", "when", "will",
        "can", "do", "does", "has", "have", "had", "not", "no", "so",
        "very", "just", "also", "about", "into", "over", "such", "than",
        "then", "each", "every", "all", "both", "few", "more", "most",
        "some", "any", "other",
    }
)

# ---------------------------------------------------------------------------
# Revenue-model → market-level descriptors used in core & trend keywords.
# ---------------------------------------------------------------------------
_REVENUE_DESCRIPTORS: dict[str, list[str]] = {
    "Subscription": ["subscription", "saas"],
    "One-time": ["purchase", "one-time"],
    "Marketplace Fee": ["marketplace", "platform"],
    "Ads": ["ad-supported", "free platform"],
}

# ---------------------------------------------------------------------------
# Customer-size → audience descriptors used in reddit & competitor queries.
# ---------------------------------------------------------------------------
_CUSTOMER_LABELS: dict[str, str] = {
    "Individual": "individuals",
    "SMB": "small businesses",
    "Mid-Market": "mid-market companies",
    "Enterprise": "enterprises",
}

# ---------------------------------------------------------------------------
# Pain-signal phrases appended to reddit queries.
# ---------------------------------------------------------------------------
_PAIN_PHRASES: list[str] = [
    "problem",
    "pain",
    "issue",
    "frustration",
    "struggling with",
    "hate",
]



# ===================================================================== #
#  Internal helpers                                                       #
# ===================================================================== #

def _tokenise(text: str) -> List[str]:
    """Split *text* into lowercase alpha tokens, removing stop-words.

    Returns only tokens with length > 2 so single-letter and very short
    fragments are discarded.
    """
    tokens = re.split(r"[\s\-_,;:\.!?'\"()\[\]{}]+", text.lower())
    return [
        t for t in tokens
        if t.isalpha() and len(t) > 2 and t not in _STOP_WORDS
    ]


def _dedupe(items: List[str]) -> List[str]:
    """Return *items* with duplicates removed, preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _safe(value: str) -> str:
    """Return a stripped, lowered string; empty string if None."""
    return (value or "").strip().lower()


# ===================================================================== #
#  Public API                                                             #
# ===================================================================== #

def build_query_bundle(idea: Idea) -> QueryBundle:
    """Build a deterministic :class:`QueryBundle` from a structured Idea.

    Parameters
    ----------
    idea:
        A fully-populated SQLAlchemy ``Idea`` instance (no DB access occurs
        inside this function).

    Returns
    -------
    QueryBundle
        Pydantic model ready for consumption by any downstream agent.
    """

    industry = _safe(idea.industry)
    description = _safe(idea.one_line_description)
    startup_name = _safe(idea.startup_name)
    geography = _safe(idea.geography)
    customer_type = idea.target_customer_type or ""
    customer_size = idea.customer_size or "SMB"
    revenue_model = idea.revenue_model or "Subscription"

    desc_tokens = _tokenise(description)
    industry_tokens = _tokenise(industry)

    # Audience label for query phrasing (e.g. "small businesses")
    audience = _CUSTOMER_LABELS.get(customer_size, customer_size.lower())

    # Revenue descriptors (e.g. ["subscription", "saas"])
    rev_tags = _REVENUE_DESCRIPTORS.get(revenue_model, [revenue_model.lower()])

    # ------------------------------------------------------------------ #
    #  1. Core keywords                                                    #
    # ------------------------------------------------------------------ #
    core: list[str] = []

    # industry + first meaningful description token  ("ai accounting")
    if industry_tokens and desc_tokens:
        core.append(f"{industry_tokens[0]} {desc_tokens[0]}")

    # audience + industry phrase  ("freelancer accounting software")
    if audience and industry:
        core.append(f"{audience} {industry}")

    # revenue descriptor + industry  ("subscription accounting")
    for tag in rev_tags[:1]:
        core.append(f"{tag} {industry}")

    # two-token description combo  ("automated bookkeeping")
    if len(desc_tokens) >= 2:
        core.append(f"{desc_tokens[0]} {desc_tokens[1]}")

    # full industry as-is if multi-word
    if len(industry_tokens) >= 2:
        core.append(industry)

    core = _dedupe(core)

    # ------------------------------------------------------------------ #
    #  2. Trend keywords  (short, 1-3 words, market-level)                 #
    # ------------------------------------------------------------------ #
    trend: list[str] = []

    # industry alone or first token
    trend.append(industry if len(industry.split()) <= 3 else industry_tokens[0] if industry_tokens else industry)

    # first desc token + "automation" / "software" if applicable
    if desc_tokens:
        trend.append(f"{desc_tokens[0]} software")
        if len(desc_tokens) >= 2:
            trend.append(f"{desc_tokens[0]} {desc_tokens[1]}")

    # revenue-model market phrase
    for tag in rev_tags[:1]:
        trend.append(f"{tag} market")

    # audience + industry short form
    if audience and industry_tokens:
        trend.append(f"{audience} {industry_tokens[0]}")

    trend = _dedupe(trend)

    # ------------------------------------------------------------------ #
    #  3. Reddit queries  (pain-focused)                                   #
    # ------------------------------------------------------------------ #
    reddit: list[str] = []

    # "{audience} struggling with {industry}"
    for pain in _PAIN_PHRASES[:3]:
        reddit.append(f"{audience} {pain} {industry}")

    # "{industry} {pain} for {audience}"
    for pain in _PAIN_PHRASES[3:5]:
        reddit.append(f"{industry} {pain} for {audience}")

    # geography-scoped pain query
    if geography and geography not in ("global", "worldwide"):
        reddit.append(f"{industry} problems in {geography}")

    # customer-type scoped query
    if customer_type:
        reddit.append(f"{customer_type.lower()} {industry} complaints")

    reddit = _dedupe(reddit)

    # ------------------------------------------------------------------ #
    #  4. Competitor queries  (exactly 5, shared builder)                  #
    # ------------------------------------------------------------------ #
    competitor = build_exa_queries(
        one_line_description=description,
        industry=industry,
        target_customer_type=customer_type,
        revenue_model=revenue_model,
        current_solution="",
    )

    # ------------------------------------------------------------------ #
    #  5. Industry tags  (short lowercase labels)                          #
    # ------------------------------------------------------------------ #
    tags: list[str] = []
    tags.extend(industry_tokens)
    tags.extend(rev_tags)
    # Add customer-type as tag
    if customer_type:
        tags.append(customer_type.lower())
    # Add first two description tokens as tags if novel
    for tok in desc_tokens[:2]:
        tags.append(tok)
    tags = _dedupe(tags)

    # ------------------------------------------------------------------ #
    #  2b. Trend keywords — Tier 2 (category-level fallback)              #
    # ------------------------------------------------------------------ #
    trend_tier2: list[str] = []

    # industry + "software" / "market"
    if industry:
        trend_tier2.append(f"{industry} software")
        trend_tier2.append(f"{industry} market")

    # first desc token + industry token combo
    if desc_tokens and industry_tokens:
        trend_tier2.append(f"{desc_tokens[0]} {industry_tokens[0]}")

    # revenue tag + industry
    for tag in rev_tags[:1]:
        if industry:
            trend_tier2.append(f"{tag} {industry}")

    trend_tier2 = _dedupe(trend_tier2)

    # ------------------------------------------------------------------ #
    #  2c. Trend keywords — Tier 3 (broad market fallback)                #
    # ------------------------------------------------------------------ #
    trend_tier3: list[str] = []

    # bare industry
    if industry:
        trend_tier3.append(industry)

    # industry + "technology"
    if industry_tokens:
        trend_tier3.append(f"{industry_tokens[0]} technology")

    # broad revenue-model market phrase
    for tag in rev_tags[:1]:
        trend_tier3.append(f"{tag} market")

    # "enterprise SaaS" / "B2B software" style
    if customer_type:
        trend_tier3.append(f"{customer_type.lower()} software")

    trend_tier3 = _dedupe(trend_tier3)

    # ------------------------------------------------------------------ #
    #  Defensive guarantee: every list has at least one entry              #
    # ------------------------------------------------------------------ #
    if not core:
        core = [industry or description or startup_name or "startup"]
    if not trend:
        trend = [industry or description or "market trends"]
    if not reddit:
        reddit = [f"{industry or description or 'startup'} problems"]
    if not competitor:
        competitor = [f"{industry or description or 'startup'} competitors"]
    if not tags:
        tags = [industry_tokens[0] if industry_tokens else "startup"]

    return QueryBundle(
        core_keywords=core,
        trend_keywords=trend,
        trend_keywords_tier2=trend_tier2 if trend_tier2 else None,
        trend_keywords_tier3=trend_tier3 if trend_tier3 else None,
        reddit_queries=reddit,
        competitor_queries=competitor,
        industry_tags=tags,
    )
