"""Exa integration — semantic competitor discovery for market research.

Uses Exa's semantic search to find companies similar to the startup idea.
Returns structured competitor list with names and descriptions.
"""

from __future__ import annotations

import asyncio
import os
import re
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse

import httpx

from ...services.competitor_cleaner import clean_competitors

# ---------------------------------------------------------------------------
# Exa API configuration
# ---------------------------------------------------------------------------
_EXA_API_URL = "https://api.exa.ai/search"
_REQUEST_TIMEOUT = 10.0
_RESULTS_PER_QUERY = 10
_MAX_RETRIES = 1
_INITIAL_BACKOFF = 0.5

# Domains that are directories / aggregators — never a competitor.
_EXCLUDED_DOMAINS: frozenset[str] = frozenset(
    {
        "capterra.com", "g2.com", "g2crowd.com", "crunchbase.com",
        "yelp.com", "alternativeto.net", "slant.co", "getapp.com",
        "softwareadvice.com", "trustradius.com", "sourceforge.net",
        "medium.com", "substack.com", "wordpress.com", "blogspot.com",
        "techcrunch.com", "forbes.com", "entrepreneur.com", "inc.com",
        "producthunt.com", "news.ycombinator.com", "reddit.com",
        "twitter.com", "x.com", "linkedin.com", "quora.com",
        "wikipedia.org", "youtube.com", "facebook.com", "instagram.com",
    }
)


def _get_exa_key() -> str:
    """Read the Exa API key from the environment."""
    key = os.getenv("EXA_API_KEY", "").strip()
    if not key:
        print("⚠️  [EXA-MR] API key missing (EXA_API_KEY)")
        raise EnvironmentError("EXA_API_KEY environment variable not set")
    return key


def _extract_domain(url: str) -> str:
    """Return bare domain from URL."""
    match = re.search(r"https?://(?:www\.)?([^/]+)", url.lower())
    return match.group(1) if match else ""


_EXCLUDED_URL_PATTERNS: tuple[str, ...] = (
    "/blog", "/news", "/article", "/press", "/media",
    "/resources/", "/insights/", "/learn/", "/guides/",
)


def _is_excluded(url: str) -> bool:
    domain = _extract_domain(url)
    if any(excl in domain for excl in _EXCLUDED_DOMAINS):
        return True
    url_lower = url.lower()
    return any(pat in url_lower for pat in _EXCLUDED_URL_PATTERNS)


def _extract_company_name(title: str, url: str) -> str:
    """Best-effort company name from the page title or domain."""
    if title:
        parts = re.split(r"[\|\-\u2013\u2014:]", title)
        if parts:
            name = parts[0].strip()
            name = re.sub(r"\s*\(.*?\)\s*", "", name)
            if 2 < len(name) < 60:
                return name
    domain = _extract_domain(url)
    if domain:
        return domain.split(".")[0].title()
    return "Unknown"


async def _search_exa(api_key: str, query: str) -> List[Dict[str, Any]]:
    """Run a single Exa semantic search (async) and return result dicts."""
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
    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.post(
                _EXA_API_URL, headers=headers, json=payload,
            )
        if response.status_code == 200:
            results = response.json().get("results", [])
            print(f"� [MR] Exa: {len(results)} results for {query!r}")
            return results
        elif response.status_code in (400, 401, 402, 403, 404):
            print(f"⚠️  [MR] Exa non-retryable HTTP {response.status_code}")
            return []
        else:
            print(f"⚠️  [MR] Exa HTTP {response.status_code} for {query!r}")
            return []
    except httpx.TimeoutException:
        print(f"⚠️  [MR] Exa timeout for {query!r}")
        return []
    except Exception as exc:
        print(f"❌ [MR] Exa error for {query!r}: {exc}")
        return []


def _build_queries(query_bundle: dict) -> list[str]:
    """Build exactly 5 Exa queries using the shared builder."""
    from ...services.exa_queries import build_exa_queries

    return build_exa_queries(
        one_line_description=query_bundle.get("one_line_description", ""),
        industry=query_bundle.get("industry", ""),
        target_customer_type=query_bundle.get("target_customer_type", ""),
        revenue_model=query_bundle.get("revenue_model", ""),
        current_solution="",
    )


async def fetch_competitors(query_bundle: dict) -> dict:
    """Discover competitors via Exa semantic search (async, parallel).

    Parameters
    ----------
    query_bundle : dict
        Must contain: one_line_description, industry
        Optional: startup_name, revenue_model

    Returns
    -------
    dict with keys:
        competitors: list[dict] — each has name, description
        competitor_count: int
    """
    print("🔎 [EXA-MR] Discovering semantic competitors (parallel)")

    try:
        api_key = _get_exa_key()
    except EnvironmentError:
        print("⚠️  [EXA-MR] Skipping — no API key. Returning empty competitors.")
        return {"competitors": [], "competitor_count": 0}

    queries = _build_queries(query_bundle)

    # Run all Exa queries in parallel
    tasks = [_search_exa(api_key, q) for q in queries]
    query_results = await asyncio.gather(*tasks, return_exceptions=True)

    raw_results: List[Dict[str, Any]] = []
    for i, result in enumerate(query_results):
        if isinstance(result, Exception):
            print(f"⚠️  [EXA-MR] Query {i+1} failed: {result}")
            continue
        raw_results.extend(result)

    print(f"📄 [EXA-MR] Total raw results: {len(raw_results)}")

    # ── Run shared competitor cleaner (hard filter + OpenAI + safety) ──
    industry = query_bundle.get("industry", "")
    cleaned_names = await clean_competitors(raw_results, industry=industry)

    # Build final competitor list with descriptions
    # Map cleaned names back to raw results for descriptions
    seen_domains: set[str] = set()
    desc_map: dict[str, str] = {}
    for result in raw_results:
        url = result.get("url", "")
        domain = _extract_domain(url)
        if domain in seen_domains:
            continue
        seen_domains.add(domain)
        text = result.get("text", "")
        highlights = result.get("highlights", [])
        desc_parts = []
        if text:
            desc_parts.append(text[:300])
        if highlights:
            desc_parts.append(" ".join(highlights[:2]))
        description = " ".join(desc_parts).strip()[:400]
        title = result.get("title", "")
        name = _extract_company_name(title, url)
        # Store description by both title-derived name and domain root
        desc_map[name.lower()] = description
        root = domain.split(".")[0].lower() if domain else ""
        if root:
            desc_map[root] = description

    final_competitors = []
    for name in cleaned_names:
        desc = desc_map.get(name.lower(), "")
        if not desc:
            # Try partial match
            for key, val in desc_map.items():
                if name.lower() in key or key in name.lower():
                    desc = val
                    break
        if not desc:
            desc = f"Competitor in {industry} space"
        final_competitors.append({"name": name, "description": desc})

    count = len(final_competitors)
    print(f"🏢 [COMP] Competitors cleaned: {count} — {[c['name'] for c in final_competitors]}")

    return {
        "competitors": final_competitors,
        "competitor_count": count,
    }
