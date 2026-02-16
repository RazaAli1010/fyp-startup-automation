"""Tavily integration — primary research substrate for market data.

Fetches market size, growth rates, CAGR, and adoption trend paragraphs
using Tavily's advanced search. Returns clean text passages only.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Tavily API configuration
# ---------------------------------------------------------------------------
_TAVILY_API_URL = "https://api.tavily.com/search"
_REQUEST_TIMEOUT = 15.0  # seconds
_MAX_RESULTS_PER_QUERY = 5


def _get_tavily_key() -> str:
    """Read the Tavily API key from the environment."""
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if not key:
        print("⚠️  [TAVILY] API key missing (TAVILY_API_KEY)")
        raise EnvironmentError("TAVILY_API_KEY environment variable not set")
    return key


def _clean_passage(text: str) -> str:
    """Remove ads, navigation fragments, and collapse whitespace."""
    # Strip common boilerplate patterns
    text = re.sub(r"(Subscribe|Sign up|Log in|Cookie|Advertisement)[\s\S]{0,80}", "", text, flags=re.IGNORECASE)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _has_numeric_signals(text: str) -> bool:
    """Return True if text contains market-relevant numeric data.

    Looks for: dollar amounts, percentages, billions/millions, CAGR,
    year references (2020-2030), or large numbers with commas.
    """
    patterns = [
        r"\$[\d,.]+",           # Dollar amounts
        r"\d+(\.\d+)?%",        # Percentages
        r"\d+(\.\d+)?\s*(billion|million|trillion|bn|mn|B|M|T)\b",  # Revenue figures
        r"CAGR",                # Compound annual growth rate
        r"20[12]\d",            # Year references 2010-2029
        r"\d{1,3}(,\d{3})+",   # Large numbers with commas
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _build_queries(
    *,
    industry: str,
    one_line_description: str,
    geography: str,
    startup_name: str,
    target_customer_type: str = "",
) -> list[str]:
    """Build numeric-seeking Tavily queries for market research.

    Uses all available input fields: industry, one_line_description,
    geography, target_customer_type. Each query targets passages
    with revenue figures, CAGR, market size in USD, company counts.

    NOT for competitors (that's Exa's job).
    """
    geo_suffix = f" in {geography}" if geography and geography.lower() != "global" else ""
    customer = (target_customer_type or "").strip()
    desc = (one_line_description or "").strip()

    queries = [
        # Market size query — anchored on industry + geography
        f"market size of {industry}{geo_suffix} revenue USD 2024 2025",
        # Growth rate query — CAGR focused
        f"growth rate of {industry} market CAGR last 5 years",
        # Description-aware query — surfaces problem-specific market data
        f"{desc} market size revenue{geo_suffix}" if desc else f"{industry} market report annual revenue forecast billion",
        # Customer-aware query — targets spending data for the customer type
        f"{customer} spending on {industry} solutions{geo_suffix}" if customer else f"number of companies operating in {industry} market{geo_suffix}",
        # Pain & friction query — cost of current workflows
        f"cost of {industry} inefficiency for {customer}{geo_suffix}" if customer else f"{industry} market inefficiency cost",
    ]
    return queries


def _search_tavily(api_key: str, query: str) -> list[dict[str, Any]]:
    """Execute a single Tavily advanced search. Returns result dicts or []."""
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": _MAX_RESULTS_PER_QUERY,
        "include_answer": True,
    }

    try:
        print(f"🔍 [TAVILY] Searching: {query!r}")
        response = httpx.post(
            _TAVILY_API_URL,
            json=payload,
            timeout=_REQUEST_TIMEOUT,
        )
        print(f"📦 [TAVILY] HTTP {response.status_code} for query={query!r}")

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"📄 [TAVILY] Got {len(results)} results for query={query!r}")
            return results
        else:
            print(f"⚠️  [TAVILY] Non-200 response: {response.status_code}")
            return []

    except httpx.TimeoutException:
        print(f"⚠️  [TAVILY] Timeout for query={query!r}")
        return []
    except Exception as exc:
        print(f"❌ [TAVILY] Error for query={query!r}: {exc}")
        return []


def fetch_market_research_text(query_bundle: dict) -> list[str]:
    """Fetch market research passages via Tavily advanced search.

    Parameters
    ----------
    query_bundle : dict
        Must contain: industry, one_line_description, geography, startup_name

    Returns
    -------
    list[str]
        Clean research passages. Empty list if Tavily fails or key is missing.
    """
    print("🔍 [TAVILY] Querying market size & growth")

    try:
        api_key = _get_tavily_key()
    except EnvironmentError:
        print("⚠️  [TAVILY] Skipping — no API key. Agent will continue with low confidence.")
        return []

    queries = _build_queries(
        industry=query_bundle["industry"],
        one_line_description=query_bundle["one_line_description"],
        geography=query_bundle["geography"],
        startup_name=query_bundle["startup_name"],
        target_customer_type=query_bundle.get("target_customer_type", ""),
    )

    all_passages: list[str] = []
    seen_urls: set[str] = set()
    numeric_passage_count = 0

    for query in queries:
        results = _search_tavily(api_key, query)
        for result in results:
            url = result.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)

            content = result.get("content", "")
            if not content or len(content) < 50:
                continue

            cleaned = _clean_passage(content)
            if len(cleaned) >= 50:
                all_passages.append(cleaned)
                # Check if passage contains numeric anchors
                if _has_numeric_signals(cleaned):
                    numeric_passage_count += 1

    total = len(all_passages)
    print(f"✅ [TAVILY] Retrieved {total} research passages")
    print(f"📊 [TAVILY] Passages with numeric data: {numeric_passage_count}/{total}")
    if total > 0 and numeric_passage_count == 0:
        print("⚠️  [TAVILY] No passages contain numeric market data — signal is WEAK")
    return all_passages
