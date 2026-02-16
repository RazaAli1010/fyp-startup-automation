"""Competitor Discovery Agent.

Uses the Exa API to discover potential competitors via semantic search,
extracts structured attributes, and computes numeric competitor signals.

Rules
-----
- NO LLM calls
- NO text summarisation
- NO scoring / judging
- NO funding guessing
- Pure signal extraction
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

import httpx

from ..schemas.query_schema import QueryBundle
from ..schemas.competitor_schema import CompetitorSignals
from .competitor_normalizer import normalize_competitor_list

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exa API configuration
# ---------------------------------------------------------------------------
_EXA_API_URL = "https://api.exa.ai/search"
_REQUEST_TIMEOUT = 10.0  # seconds per request
_MAX_RETRIES = 1
_INITIAL_BACKOFF = 1.0  # seconds
_RESULTS_PER_QUERY = 10  # top results per query

# ---------------------------------------------------------------------------
# Stop-words for noun extraction (feature overlap computation).
# ---------------------------------------------------------------------------
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "be", "been",
        "this", "that", "it", "its", "we", "our", "they", "their", "my", "me",
        "i", "you", "your", "he", "she", "him", "her", "us", "them",
        "do", "does", "did", "has", "have", "had", "not", "no", "so",
        "very", "just", "also", "about", "into", "over", "such", "than",
        "then", "each", "every", "all", "both", "few", "more", "most",
        "some", "any", "other", "what", "which", "who", "how", "where",
        "when", "will", "can", "would", "could", "should", "if", "up",
        "out", "get", "got", "like", "know", "think", "want", "need",
        "use", "using", "used", "one", "even", "still", "really", "much",
        "way", "going", "been", "being", "there", "here", "new", "best",
        "top", "www", "com", "http", "https", "org", "net",
    }
)

# Domains that are directories / aggregators / media — never a competitor.
_EXCLUDED_DOMAINS: frozenset[str] = frozenset(
    {
        "capterra.com", "g2.com", "g2crowd.com", "crunchbase.com",
        "yelp.com", "alternativeto.net", "slant.co", "getapp.com",
        "softwareadvice.com", "trustradius.com", "sourceforge.net",
        "softwaresuggest.com", "financesonline.com", "saasworthy.com",
        "goodfirms.co", "medium.com", "substack.com", "wordpress.com",
        "blogspot.com", "techcrunch.com", "forbes.com", "entrepreneur.com",
        "inc.com", "producthunt.com", "news.ycombinator.com", "reddit.com",
        "twitter.com", "x.com", "linkedin.com", "quora.com",
        "wikipedia.org", "youtube.com", "facebook.com", "instagram.com",
        "tiktok.com", "pinterest.com",
    }
)


# ===================================================================== #
#  Internal helpers                                                       #
# ===================================================================== #

def _get_exa_key() -> str:
    """Read the Exa API key from the environment."""
    key = os.getenv("EXA_API_KEY")
    if not key:
        print("❌ [EXA] API key missing (EXA_API_KEY) — skipping competitor discovery")
        raise EnvironmentError("EXA_API_KEY environment variable not set")
    print("✅ [EXA] API key loaded")
    return key


def _extract_domain(url: str) -> str:
    """Return the bare domain from a URL (e.g. 'example.com')."""
    match = re.search(r"https?://(?:www\.)?([^/]+)", url.lower())
    return match.group(1) if match else ""


def _is_excluded(url: str) -> bool:
    """Return True if the URL belongs to an excluded domain."""
    domain = _extract_domain(url)
    return any(excl in domain for excl in _EXCLUDED_DOMAINS)


def _extract_company_name(title: str, url: str) -> str:
    """Best-effort company name from the page title or domain."""
    if title:
        # Take the first segment before common separators
        parts = re.split(r"[\|\-\u2013\u2014:]", title)
        if parts:
            name = parts[0].strip()
            # Remove parenthetical suffixes
            name = re.sub(r"\s*\(.*?\)\s*", "", name)
            if 2 < len(name) < 60:
                return name

    # Fallback: capitalised domain root
    domain = _extract_domain(url)
    if domain:
        root = domain.split(".")[0]
        return root.title()

    return "Unknown"


def _extract_founding_year(text: str) -> Optional[int]:
    """Try to find a 4-digit founding year in *text*.

    Looks for patterns like "founded in 2018", "est. 2015", "since 2020".
    Returns None if nothing plausible is found.
    """
    patterns = [
        r"(?:founded|established|started|launched|est\.?)\s*(?:in\s*)?(\d{4})",
        r"since\s+(\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            current_year = datetime.now().year
            if 1990 <= year <= current_year:
                return year
    return None


def _tokenise_nouns(text: str) -> set[str]:
    """Extract a set of lowercase alpha tokens (≥ 3 chars) minus stop-words.

    This is a lightweight noun-proxy used for Jaccard overlap computation.
    """
    tokens = re.split(r"[^a-zA-Z]+", text.lower())
    return {
        t for t in tokens
        if len(t) >= 3 and t not in _STOP_WORDS
    }


# ---------------------------------------------------------------------------
# Title-based competitor validation
# ---------------------------------------------------------------------------
_TITLE_BLACKLIST_PHRASES: tuple[str, ...] = (
    "what is", "how to", "guide", "top ", "list of", "best ",
    "software development", "industry", "vs ", "versus ",
    "review", "comparison", "tutorial", "explained",
    "definition", "meaning", "overview",
)

_TITLE_BLACKLIST_SUFFIXES: tuple[str, ...] = (
    "software", "platform", "industry", "law", "legaltech",
    "solutions", "services", "tools", "apps", "companies",
)


def is_valid_competitor(title: str, domain: str) -> bool:
    """Return True only if the result looks like a real company/product.

    Filters out blog posts, listicles, guides, and generic category pages.
    """
    if not domain:
        return False

    if not title or len(title) > 40:
        return False

    title_lower = title.lower().strip()

    for phrase in _TITLE_BLACKLIST_PHRASES:
        if phrase in title_lower:
            return False

    for suffix in _TITLE_BLACKLIST_SUFFIXES:
        if title_lower.endswith(suffix):
            return False

    return True


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity between two sets, returns 0.0 if both empty."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


async def _search_exa(api_key: str, query: str) -> List[Dict[str, Any]]:
    """Run a single Exa semantic search with retry logic (async).

    Returns a list of result dicts or an empty list on failure.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "type": "auto",
        "numResults": _RESULTS_PER_QUERY,
        "contents": {
            "text": True,
            "highlights": True,
        },
    }

    print(f"🔎 [EXA] Searching: {query!r}")

    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                response = await client.post(
                    _EXA_API_URL,
                    headers=headers,
                    json=payload,
                )
            print(f"📦 [EXA] HTTP {response.status_code} for query={query!r}")
            if response.status_code == 200:
                results = response.json().get("results", [])
                print(f"📄 [EXA] Raw results count: {len(results)} for query={query!r}")
                return results

            if response.status_code in (400, 401, 402, 403, 404):
                print(f"⚠️ [EXA] Quota or access issue — skipping competitor discovery (HTTP {response.status_code})")
                logger.warning(
                    "Exa non-retryable %d for query=%r",
                    response.status_code,
                    query,
                )
                return []

        except httpx.TimeoutException:
            print(f"⚠️ [EXA] Timeout (attempt {attempt + 1}) for query={query!r}")
            logger.warning(
                "Exa timeout attempt %d for query=%r", attempt + 1, query
            )
        except Exception as exc:
            print(f"❌ [EXA] Error for query={query!r}: {exc}")
            logger.warning("Exa error for query=%r: %s", query, exc)
            return []

        if attempt < _MAX_RETRIES:
            await asyncio.sleep(_INITIAL_BACKOFF * (2 ** attempt))

    print(f"⚠️ [EXA] All retries exhausted for query={query!r}")
    return []


# ===================================================================== #
#  Public API                                                             #
# ===================================================================== #

async def fetch_competitor_signals(query_bundle: QueryBundle) -> CompetitorSignals:
    """Discover competitors via Exa and return structured signals (async).

    Parameters
    ----------
    query_bundle:
        A ``QueryBundle`` whose ``competitor_queries`` and ``industry_tags``
        drive the Exa semantic searches and feature-overlap computation.

    Returns
    -------
    CompetitorSignals
        Numeric + categorical competitor landscape metrics.
    """
    # Cap to exactly 5 queries (shared builder guarantees 5)
    queries = query_bundle.competitor_queries[:5]

    print(f"🔎 [COMP] Running {len(queries)} Exa competitor queries in parallel")

    try:
        api_key = _get_exa_key()
    except EnvironmentError as exc:
        logger.error("Competitor agent init failed: %s", exc)
        return _empty_signals()

    # ------------------------------------------------------------------ #
    #  1. Fetch results for all competitor queries in parallel            #
    # ------------------------------------------------------------------ #
    tasks = [_search_exa(api_key, q) for q in queries]
    query_results = await asyncio.gather(*tasks, return_exceptions=True)

    raw_results: List[Dict[str, Any]] = []
    for i, result in enumerate(query_results):
        if isinstance(result, Exception):
            print(f"⚠️ [EXA] Query {i+1} failed: {result}")
            continue
        if result is None:
            continue
        raw_results.extend(result)

    print(f"📄 [EXA] Total raw results across all queries: {len(raw_results)}")

    # ------------------------------------------------------------------ #
    #  2. Deduplicate by domain, filter excluded sites, validate titles   #
    # ------------------------------------------------------------------ #
    seen_domains: set[str] = set()
    competitors: List[Dict[str, Any]] = []
    filtered_titles: List[str] = []

    for result in raw_results:
        url = result.get("url", "")
        if not url:
            continue

        if _is_excluded(url):
            filtered_titles.append(result.get("title", "<no title>") + " [excluded domain]")
            continue

        domain = _extract_domain(url)
        if domain in seen_domains:
            continue
        seen_domains.add(domain)

        title = result.get("title", "")

        if not is_valid_competitor(title, domain):
            filtered_titles.append(title or "<no title>")
            continue

        text = result.get("text", "")
        highlights = result.get("highlights", [])
        description = (text[:500] if text else "") + " " + " ".join(highlights or [])

        name = _extract_company_name(title, url)
        founding_year = _extract_founding_year(description)

        competitors.append(
            {
                "name": name,
                "domain": domain,
                "description": description.strip(),
                "founding_year": founding_year,
            }
        )

    if filtered_titles:
        print(f"🚫 [EXA] Filtered out {len(filtered_titles)} results:")
        for ft in filtered_titles[:10]:
            print(f"   • {ft}")

    if not competitors:
        print("⚠️ [EXA] No valid competitors after filtering — query may be too broad")
        logger.info("No competitors discovered for the given queries.")
        return _empty_signals()

    # ------------------------------------------------------------------ #
    #  3. Compute metrics                                                 #
    # ------------------------------------------------------------------ #
    total_competitors = len(competitors)

    # Unique names — normalize to max 2 words, dedupe, cap at 8
    raw_names: List[str] = []
    for comp in competitors:
        name = comp["name"].strip()
        if name.lower() != "unknown":
            raw_names.append(name)
    unique_names = normalize_competitor_list(raw_names)

    # avg_company_age — only from competitors with a detected founding year
    current_year = datetime.now().year
    ages: List[float] = []
    for comp in competitors:
        if comp["founding_year"] is not None:
            age = current_year - comp["founding_year"]
            if age >= 0:
                ages.append(float(age))
    avg_age = sum(ages) / len(ages) if ages else 0.0

    # competitor_density_score
    density = min(total_competitors / 20.0, 1.0)

    # feature_overlap_score — Jaccard of competitor description nouns
    # vs. the union of industry_tags + core_keywords
    reference_tokens: set[str] = set()
    for tag in query_bundle.industry_tags:
        reference_tokens.update(_tokenise_nouns(tag))
    for kw in query_bundle.core_keywords:
        reference_tokens.update(_tokenise_nouns(kw))

    overlaps: List[float] = []
    for comp in competitors:
        comp_tokens = _tokenise_nouns(comp["description"])
        if comp_tokens:
            overlaps.append(_jaccard(comp_tokens, reference_tokens))

    avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
    feature_overlap = max(0.0, min(1.0, avg_overlap))

    print(f"🏢 [COMP] Competitors normalized: {len(unique_names)} — {unique_names}")
    print(f"📊 [COMP] Density: {round(density, 4)}, Overlap: {round(feature_overlap, 4)}, Avg age: {round(avg_age, 2)}")
    print("=" * 60 + "\n")

    return CompetitorSignals(
        total_competitors=total_competitors,
        competitor_names=unique_names,
        avg_company_age=round(avg_age, 2),
        competitor_density_score=round(density, 4),
        feature_overlap_score=round(feature_overlap, 4),
    )


def _empty_signals() -> CompetitorSignals:
    """Return zero-value signals for graceful degradation."""
    return CompetitorSignals(
        total_competitors=0,
        competitor_names=[],
        avg_company_age=0.0,
        competitor_density_score=0.0,
        feature_overlap_score=0.0,
    )
