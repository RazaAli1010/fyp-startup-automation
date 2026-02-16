"""Shared competitor cleaning pipeline — used by BOTH Idea Validation and Market Research.

Pipeline:
  1. Hard filter raw candidates (URL patterns, title patterns, excluded domains)
  2. Send survivors to OpenAI for company-name extraction
  3. Final safety check: exactly 5, ≤2 words each, deduped, proper caps
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .openai_client import call_openai_chat_async

logger = logging.getLogger(__name__)

# ── Maximum competitors to return ─────────────────────────────────────────
MAX_COMPETITORS = 5

# ── Excluded domains (directories, aggregators, media, social) ────────────
EXCLUDED_DOMAINS: frozenset[str] = frozenset({
    # Directories / review sites
    "capterra.com", "g2.com", "g2crowd.com", "crunchbase.com",
    "yelp.com", "alternativeto.net", "slant.co", "getapp.com",
    "softwareadvice.com", "trustradius.com", "sourceforge.net",
    "softwaresuggest.com", "financesonline.com", "saasworthy.com",
    "goodfirms.co",
    # Media / blogs
    "medium.com", "substack.com", "wordpress.com", "blogspot.com",
    "techcrunch.com", "forbes.com", "entrepreneur.com", "inc.com",
    "wired.com", "theverge.com", "venturebeat.com", "zdnet.com",
    "cnet.com", "mashable.com", "businessinsider.com", "cnbc.com",
    "bloomberg.com", "reuters.com", "bbc.com", "nytimes.com",
    "wsj.com", "theguardian.com", "arstechnica.com",
    # Social / forums
    "producthunt.com", "news.ycombinator.com", "reddit.com",
    "twitter.com", "x.com", "linkedin.com", "quora.com",
    "wikipedia.org", "youtube.com", "facebook.com", "instagram.com",
    "tiktok.com", "pinterest.com",
    # Other non-company
    "github.com", "stackoverflow.com", "arxiv.org",
    "digitalcommerce360.com",
})

# ── URL path patterns that indicate editorial content ─────────────────────
EXCLUDED_URL_PATTERNS: tuple[str, ...] = (
    "/blog", "/news", "/article", "/press", "/media",
    "/resources/", "/insights/", "/learn/", "/guides/",
    "/posts/", "/stories/", "/opinion/", "/editorial/",
    "/review/", "/reviews/", "/best-", "/top-",
)

# ── Title phrases that indicate editorial / listicle content ──────────────
EXCLUDED_TITLE_PHRASES: tuple[str, ...] = (
    "top ", "best ", "guide", "how to", "list of", "what is",
    "why ", "review", "comparison", "vs ", "versus ",
    "tutorial", "explained", "definition", "overview",
    "tips", "ways to", "things to", "report", "analysis",
    "forecast", "trends", "outlook", "ranking",
)


# ===================================================================== #
#  Step 1 — Extract domain                                                #
# ===================================================================== #

def _extract_domain(url: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", url.lower())
    return match.group(1) if match else ""


def _domain_root(url: str) -> str:
    """Get the root name from a domain (e.g. 'stripe' from 'stripe.com')."""
    domain = _extract_domain(url)
    if domain:
        return domain.split(".")[0].title()
    return ""


# ===================================================================== #
#  Step 2 — Hard filter (before LLM)                                      #
# ===================================================================== #

def hard_filter_candidates(
    raw_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Apply strict URL + title filtering. Returns only plausible company pages."""
    survivors: List[Dict[str, Any]] = []
    seen_domains: set[str] = set()

    for result in raw_results:
        url = result.get("url", "")
        if not url:
            continue

        # Domain exclusion
        domain = _extract_domain(url)
        if any(excl in domain for excl in EXCLUDED_DOMAINS):
            continue

        # URL path exclusion
        url_lower = url.lower()
        if any(pat in url_lower for pat in EXCLUDED_URL_PATTERNS):
            continue

        # Deduplicate by domain
        if domain in seen_domains:
            continue
        seen_domains.add(domain)

        # Title exclusion
        title = (result.get("title") or "").strip()
        title_lower = title.lower()
        if any(phrase in title_lower for phrase in EXCLUDED_TITLE_PHRASES):
            continue

        # Reject very long titles (likely article headlines)
        if len(title) > 60:
            continue

        survivors.append({
            "title": title,
            "url": url,
            "domain": domain,
            "snippet": (result.get("text") or result.get("snippet") or "")[:300],
        })

    print(f"🔍 [CLEANER] Hard filter: {len(raw_results)} raw → {len(survivors)} survivors")
    return survivors


# ===================================================================== #
#  Step 3 — OpenAI company name sanitizer                                 #
# ===================================================================== #

_SANITIZER_SYSTEM = """You are a strict company-name extractor.

Given a list of search result titles and URLs, extract ONLY actual company or product names.

Rules:
- Return ONLY real companies or startups — NO blogs, publications, directories, or news sites.
- Each name must be maximum 2 words.
- Use proper capitalization (e.g. "Stripe", "Brex", not "STRIPE" or "brex").
- Deduplicate — no repeated entries.
- Return exactly up to 5 names maximum.
- If fewer than 5 real companies exist in the list, return fewer.
- No explanations, just the JSON.

REQUIRED OUTPUT FORMAT:
{"competitors": ["Name1", "Name2", "Name3", "Name4", "Name5"]}"""


async def _openai_sanitize(
    candidates: List[Dict[str, Any]],
    industry: str = "",
) -> Optional[List[str]]:
    """Send candidate list to OpenAI for company name extraction.

    Returns a list of clean company names, or None on failure.
    """
    if not candidates:
        return None

    # Build compact candidate list for the prompt
    lines = []
    for c in candidates[:20]:  # Cap input to 20 candidates
        lines.append(f"- Title: {c['title']}  |  URL: {c['url']}")
    candidate_text = "\n".join(lines)

    user_prompt = f"""Industry context: {industry or 'Technology'}

Search results to extract company names from:
{candidate_text}

Return JSON with up to 5 real company/product names only."""

    messages = [
        {"role": "system", "content": _SANITIZER_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]

    # Attempt 1
    result = await call_openai_chat_async(
        messages=messages,
        max_completion_tokens=200,
    )

    names = _parse_competitor_json(result)
    if names is not None:
        print(f"✅ [CLEANER] OpenAI returned {len(names)} company names: {names}")
        return names

    # Retry once
    print("⚠️  [CLEANER] OpenAI returned invalid JSON — retrying once")
    result = await call_openai_chat_async(
        messages=messages,
        max_completion_tokens=200,
    )
    names = _parse_competitor_json(result)
    if names is not None:
        print(f"✅ [CLEANER] OpenAI retry returned {len(names)} company names: {names}")
        return names

    print("❌ [CLEANER] OpenAI failed twice — will use domain fallback")
    return None


def _parse_competitor_json(result: Optional[Dict[str, Any]]) -> Optional[List[str]]:
    """Parse the OpenAI response into a list of competitor names."""
    if result is None:
        return None

    competitors = result.get("competitors")
    if not isinstance(competitors, list):
        return None

    # Validate each entry is a string
    names = []
    for item in competitors:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())

    return names if names else None


# ===================================================================== #
#  Step 4 — Final safety check                                            #
# ===================================================================== #

_NAME_STRIP_SUFFIXES = {
    "inc", "ltd", "llc", "corp", "corporation", "co",
    "ai", "platform", "software", "solutions", "services",
    "tool", "tools", "app", "apps", "technology", "technologies",
    "group", "global", "labs", "studio", "studios",
}


def _clean_name(name: str) -> Optional[str]:
    """Normalize a single name: strip suffixes, max 2 words, proper caps."""
    name = name.strip()
    if not name:
        return None

    # Strip parenthetical
    name = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()

    words = name.split()

    # Strip suffix words
    while words and words[-1].lower().rstrip(".,") in _NAME_STRIP_SUFFIXES:
        words.pop()
    while words and words[0].lower().rstrip(".,") in _NAME_STRIP_SUFFIXES:
        words.pop(0)

    if not words:
        return None

    # Max 2 words
    words = words[:2]

    # Proper capitalization
    result = " ".join(w.capitalize() if w.islower() else w for w in words)

    if len(result) < 2:
        return None

    return result


def final_safety_check(names: List[str]) -> List[str]:
    """Ensure exactly ≤5 unique names, each ≤2 words, cleaned."""
    seen: set[str] = set()
    clean: List[str] = []

    for raw in names:
        cleaned = _clean_name(raw)
        if cleaned is None:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        clean.append(cleaned)
        if len(clean) >= MAX_COMPETITORS:
            break

    return clean


def _domain_fallback(candidates: List[Dict[str, Any]]) -> List[str]:
    """Fallback: extract company names from domain roots."""
    seen: set[str] = set()
    names: List[str] = []

    for c in candidates:
        root = _domain_root(c.get("url", ""))
        if not root or root.lower() in seen:
            continue
        cleaned = _clean_name(root)
        if cleaned is None:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(cleaned)
        if len(names) >= MAX_COMPETITORS:
            break

    return names


# ===================================================================== #
#  Public API — single entry point for both agents                        #
# ===================================================================== #

async def clean_competitors(
    raw_results: List[Dict[str, Any]],
    industry: str = "",
) -> List[str]:
    """Full competitor cleaning pipeline.

    Parameters
    ----------
    raw_results : list[dict]
        Raw search results with 'title', 'url', and optionally 'text'/'snippet'.
    industry : str
        Industry context for OpenAI prompt.

    Returns
    -------
    list[str]
        Exactly ≤5 clean company names, deduped, ≤2 words each.
    """
    # Step 1: Hard filter
    survivors = hard_filter_candidates(raw_results)

    if not survivors:
        print("⚠️  [CLEANER] No survivors after hard filter — returning empty")
        return []

    # Step 2: OpenAI sanitizer
    openai_names = await _openai_sanitize(survivors, industry=industry)

    if openai_names:
        # Step 3: Final safety check on OpenAI output
        result = final_safety_check(openai_names)
    else:
        # Fallback: domain root names
        print("⚠️  [CLEANER] Using domain fallback")
        result = final_safety_check(_domain_fallback(survivors))

    print(f"✅ [CLEANER] Final competitor list ({len(result)}): {result}")
    return result
