"""Exa integration — semantic competitor discovery for market research.

Uses Exa's semantic search to find companies similar to the startup idea.
Returns structured competitor list with names and descriptions.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

import httpx

from ...services.competitor_normalizer import normalize_competitor_list, normalize_competitor_name

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


def _is_excluded(url: str) -> bool:
    domain = _extract_domain(url)
    return any(excl in domain for excl in _EXCLUDED_DOMAINS)


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


def _search_exa(api_key: str, query: str) -> List[Dict[str, Any]]:
    """Run a single Exa semantic search. Returns result dicts or []."""
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

    print(f"🔎 [EXA-MR] Searching: {query!r}")

    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = httpx.post(
                _EXA_API_URL,
                headers=headers,
                json=payload,
                timeout=_REQUEST_TIMEOUT,
            )
            print(f"📦 [EXA-MR] HTTP {response.status_code} for query={query!r}")

            if response.status_code == 200:
                results = response.json().get("results", [])
                print(f"📄 [EXA-MR] Got {len(results)} results")
                return results

            if response.status_code in (400, 401, 402, 403, 404):
                print(f"⚠️  [EXA-MR] Quota or access issue — skipping competitor discovery (HTTP {response.status_code})")
                return []

        except httpx.TimeoutException:
            print(f"⚠️  [EXA-MR] Timeout (attempt {attempt + 1})")
        except Exception as exc:
            print(f"❌ [EXA-MR] Error: {exc}")
            return []

        if attempt < _MAX_RETRIES:
            import time as _time
            _time.sleep(_INITIAL_BACKOFF * (2 ** attempt))

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


def fetch_competitors(query_bundle: dict) -> dict:
    """Discover competitors via Exa semantic search.

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
    print("🔎 [EXA-MR] Discovering semantic competitors")

    try:
        api_key = _get_exa_key()
    except EnvironmentError:
        print("⚠️  [EXA-MR] Skipping — no API key. Returning empty competitors.")
        return {"competitors": [], "competitor_count": 0}

    queries = _build_queries(query_bundle)

    raw_results: List[Dict[str, Any]] = []
    for i, query in enumerate(queries, 1):
        print(f"\n🔎 [EXA-MR] Executing query {i}/{len(queries)}...")
        results = _search_exa(api_key, query)
        raw_results.extend(results)
        # If first query returns empty due to quota, skip remaining
        if i == 1 and len(results) == 0:
            print("⚠️  [EXA-MR] First query returned 0 results — likely quota issue, skipping remaining")
            break

    print(f"📄 [EXA-MR] Total raw results: {len(raw_results)}")

    # Deduplicate & filter
    seen_domains: set[str] = set()
    competitors: list[dict] = []

    for result in raw_results:
        url = result.get("url", "")
        if not url or _is_excluded(url):
            continue

        domain = _extract_domain(url)
        if domain in seen_domains:
            continue
        seen_domains.add(domain)

        title = result.get("title", "")
        if not title or len(title) > 80:
            continue

        name = _extract_company_name(title, url)
        if name.lower() == "unknown":
            continue

        # Build short description from text/highlights
        text = result.get("text", "")
        highlights = result.get("highlights", [])
        desc_parts = []
        if text:
            desc_parts.append(text[:300])
        if highlights:
            desc_parts.append(" ".join(highlights[:2]))
        description = " ".join(desc_parts).strip()[:400]

        competitors.append({
            "name": name,
            "description": description if description else f"Competitor in {query_bundle['industry']} space",
        })

    # Normalize competitor names: dedupe, strip suffixes, max 2 words, cap 8
    raw_names = [c["name"] for c in competitors]
    normalized_names = normalize_competitor_list(raw_names)

    # Rebuild competitor list with normalized names
    name_set = {n.lower() for n in normalized_names}
    final_competitors = []
    seen_normalized: set[str] = set()
    for c in competitors:
        norm = normalize_competitor_name(c["name"])
        if norm and norm.lower() in name_set and norm.lower() not in seen_normalized:
            seen_normalized.add(norm.lower())
            final_competitors.append({"name": norm, "description": c["description"]})

    count = len(final_competitors)
    print(f"🏢 [COMP] Competitors normalized: {count} — {[c['name'] for c in final_competitors]}")

    return {
        "competitors": final_competitors,
        "competitor_count": count,
    }
