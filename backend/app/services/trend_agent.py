"""Trend & Demand Agent.

Queries SerpAPI (Google Trends engine) for each keyword in a QueryBundle,
extracts time-series interest data, and computes numeric demand metrics.

Rules
-----
- NO LLM calls
- NO text summarisation
- NO scoring / judging
- Pure signal extraction
"""

from __future__ import annotations

import logging
import os
import statistics
from typing import Dict, List, Any

import httpx

from ..schemas.query_schema import QueryBundle
from ..schemas.trend_schema import TrendDemandSignals

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SerpAPI configuration
# ---------------------------------------------------------------------------
_SERPAPI_BASE_URL = "https://serpapi.com/search"
_REQUEST_TIMEOUT = 10.0  # seconds per request
_MAX_RETRIES = 2
_INITIAL_BACKOFF = 1.5  # seconds

# Google Trends returns monthly data points.  A 5-year window gives ~60 pts.
# We use "today 5-y" as the date range for the TIMESERIES data_type.
_DATE_RANGE = "today 5-y"


# ===================================================================== #
#  Internal helpers                                                       #
# ===================================================================== #

def _get_serpapi_key() -> str:
    """Read the SerpAPI key from the environment."""
    key = os.getenv("SERPAPI_KEY")
    if not key:
        print("❌ [SerpAPI] API key missing (SERPAPI_KEY) — skipping trend analysis")
        raise EnvironmentError("SERPAPI_KEY environment variable not set")
    print("✅ [SerpAPI] API key loaded")
    return key


def _fetch_timeseries(api_key: str, keyword: str, geo: str = "") -> List[int]:
    """Fetch Google Trends TIMESERIES for *keyword* and return raw values.

    Returns an empty list on any failure so the caller can skip the keyword
    without crashing.
    """
    params: Dict[str, Any] = {
        "engine": "google_trends",
        "q": keyword,
        "data_type": "TIMESERIES",
        "date": _DATE_RANGE,
        "api_key": api_key,
    }
    if geo:
        params["geo"] = geo

    print(f"🔍 [SerpAPI] Fetching timeseries for keyword={keyword!r}, geo={geo!r}")

    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = httpx.get(
                _SERPAPI_BASE_URL,
                params=params,
                timeout=_REQUEST_TIMEOUT,
            )
            print(f"📦 [SerpAPI] HTTP {response.status_code} for keyword={keyword!r}")
            if response.status_code == 200:
                data = response.json()
                timeline = (
                    data
                    .get("interest_over_time", {})
                    .get("timeline_data", [])
                )
                values: List[int] = []
                for point in timeline:
                    entries = point.get("values", [])
                    if entries:
                        values.append(entries[0].get("extracted_value", 0))
                print(f"📦 [SerpAPI] keyword={keyword!r} → {len(values)} data points")
                return values

            # Non-retryable HTTP errors
            if response.status_code in (400, 401, 403, 404):
                print(f"⚠️ [SerpAPI] Non-retryable HTTP {response.status_code} for keyword={keyword!r}")
                logger.warning(
                    "SerpAPI non-retryable %d for keyword=%r",
                    response.status_code,
                    keyword,
                )
                return []

        except httpx.TimeoutException:
            print(f"⚠️ [SerpAPI] Timeout (attempt {attempt + 1}) for keyword={keyword!r}")
            logger.warning(
                "SerpAPI timeout attempt %d for keyword=%r",
                attempt + 1,
                keyword,
            )
        except Exception as exc:
            print(f"❌ [SerpAPI] Error for keyword={keyword!r}: {exc}")
            logger.warning("SerpAPI error for keyword=%r: %s", keyword, exc)
            return []

        # Exponential back-off before retry
        if attempt < _MAX_RETRIES:
            import time as _time
            _time.sleep(_INITIAL_BACKOFF * (2 ** attempt))

    print(f"⚠️ [SerpAPI] All retries exhausted for keyword={keyword!r}")
    return []


# ------------------------------------------------------------------ #
#  Metric computation helpers                                          #
# ------------------------------------------------------------------ #

def _avg_search_volume(all_values: List[int]) -> float:
    """Mean of all trend interest values (Google's 0-100 relative scale)."""
    if not all_values:
        return 0.0
    return sum(all_values) / len(all_values)


def _growth_rate_5y(values: List[int]) -> float:
    """(last_year_avg - first_year_avg) / first_year_avg, clamped [-1, 2].

    Assumes ~60 monthly data points for a 5-year window.
    Uses the first 12 and last 12 values as proxies for first/last year.
    """
    if len(values) < 24:
        return 0.0

    first_year = values[:12]
    last_year = values[-12:]

    first_avg = sum(first_year) / len(first_year)
    last_avg = sum(last_year) / len(last_year)

    if first_avg == 0:
        return 0.0

    rate = (last_avg - first_avg) / first_avg
    return max(-1.0, min(2.0, rate))


def _momentum_score(values: List[int]) -> float:
    """(last_6mo_avg - prev_6mo_avg) / prev_6mo_avg, normalised to [0, 1]."""
    if len(values) < 12:
        return 0.0

    prev_6 = values[-12:-6]
    last_6 = values[-6:]

    prev_avg = sum(prev_6) / len(prev_6)
    last_avg = sum(last_6) / len(last_6)

    if prev_avg == 0:
        return 0.5  # neutral when no baseline

    raw = (last_avg - prev_avg) / prev_avg
    # Map raw ratio (roughly -1..+1) into 0..1
    normalised = (raw + 1.0) / 2.0
    return max(0.0, min(1.0, normalised))


def _volatility_index(values: List[int]) -> float:
    """std_dev / mean, clamped to [0, 1]."""
    if len(values) < 2:
        return 0.0

    mean_val = sum(values) / len(values)
    if mean_val == 0:
        return 0.0

    std_dev = statistics.stdev(values)
    vol = std_dev / mean_val
    return max(0.0, min(1.0, vol))


def _demand_strength(avg_volume: float, growth_rate: float) -> float:
    """Composite demand signal from Google Trends interest + growth.

    avg_volume is on Google Trends' 0-100 relative scale.
    We normalise it to 0-1 by dividing by 100, then boost with growth.
    """
    volume_factor = max(0.0, min(avg_volume / 100.0, 1.0))
    raw = volume_factor * (1.0 + growth_rate)
    return max(0.0, min(1.0, raw))


def _fetch_search_demand_proxy(
    api_key: str, keyword: str, geo: str = ""
) -> float:
    """Fetch a demand proxy from a regular Google search via SerpAPI.

    Extraction priority:
      1. search_information.total_results  (normalised: min(total / 1e9, 1.0))
      2. Count of related_searches          (normalised: min(count / 20, 1.0))
      3. 0.0 if nothing available

    Returns a float in [0, 1].
    """
    params: Dict[str, Any] = {
        "engine": "google",
        "q": keyword,
        "api_key": api_key,
    }
    if geo:
        params["gl"] = geo

    print(f"\U0001f50d [SerpAPI] Fetching search demand proxy for keyword={keyword!r}")

    try:
        response = httpx.get(
            _SERPAPI_BASE_URL,
            params=params,
            timeout=_REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            print(f"\u26a0\ufe0f [SerpAPI] Demand proxy HTTP {response.status_code} for keyword={keyword!r}")
            return 0.0

        data = response.json()

        search_info = data.get("search_information", {})
        print(f"\U0001f4e6 [SerpAPI] search_information: {search_info}")

        # Priority 1: total_results
        total_results = search_info.get("total_results", 0)
        if total_results and total_results > 0:
            proxy = min(total_results / 1_000_000_000, 1.0)
            print(f"\U0001f4ca [SerpAPI] Raw demand proxy (total_results={total_results}): {round(proxy, 4)}")
            return proxy

        # Priority 2: related_searches count
        related = data.get("related_searches", [])
        if related:
            proxy = min(len(related) / 20.0, 1.0)
            print(f"\U0001f4ca [SerpAPI] Raw demand proxy (related_searches count={len(related)}): {round(proxy, 4)}")
            return proxy

        print(f"\u26a0\ufe0f [SerpAPI] No demand proxy data found for keyword={keyword!r}")
        return 0.0

    except Exception as exc:
        print(f"\u274c [SerpAPI] Demand proxy error for keyword={keyword!r}: {exc}")
        return 0.0


# ===================================================================== #
#  Public API                                                             #
# ===================================================================== #

def _try_keywords(api_key: str, keywords: List[str]) -> List[List[int]]:
    """Fetch timeseries for each keyword and return per-keyword value lists.

    Only keywords that return data are included in the result.
    """
    per_keyword: List[List[int]] = []
    for keyword in keywords:
        values = _fetch_timeseries(api_key, keyword)
        if values:
            per_keyword.append(values)
        else:
            print(f"⚠️ [SerpAPI] No trend data for keyword={keyword!r} — skipping")
            logger.info("No trend data for keyword=%r — skipping.", keyword)
    return per_keyword


def _aggregate_series(per_keyword_values: List[List[int]]) -> List[int]:
    """Average multiple keyword series into a single time-series."""
    max_len = max(len(v) for v in per_keyword_values)
    averaged: List[float] = []
    for i in range(max_len):
        bucket: List[int] = []
        for kw_vals in per_keyword_values:
            if i < len(kw_vals):
                bucket.append(kw_vals[i])
        averaged.append(sum(bucket) / len(bucket))
    return [int(round(v)) for v in averaged]


def _is_usable(avg_vol: float, growth: float, momentum: float) -> bool:
    """Trend data is usable if any core metric is non-zero."""
    demand = _demand_strength(avg_vol, growth)
    return demand > 0 or growth != 0.0 or momentum != 0.5


def fetch_trend_demand_signals(query_bundle: QueryBundle) -> TrendDemandSignals:
    """Query SerpAPI and return quantifiable trend & demand signals.

    Uses a multi-stage keyword fallback:
      Tier 1 — idea-specific keywords (trend_keywords)
      Tier 2 — category-level keywords (trend_keywords_tier2)
      Tier 3 — broad market keywords (trend_keywords_tier3)

    Stops at the first tier that returns usable data.

    Parameters
    ----------
    query_bundle:
        A ``QueryBundle`` whose ``trend_keywords`` (and tier 2/3 variants)
        drive the Google Trends queries.

    Returns
    -------
    TrendDemandSignals
        Structured numeric demand metrics ready for downstream consumption.
    """
    print("\n" + "=" * 60)
    print("🔍 [SerpAPI] Calling SerpAPI — multi-tier keyword fallback")
    print("=" * 60)

    try:
        api_key = _get_serpapi_key()
    except EnvironmentError as exc:
        logger.error("Trend agent init failed: %s", exc)
        return _empty_signals()

    # ------------------------------------------------------------------ #
    #  Build tier list                                                     #
    # ------------------------------------------------------------------ #
    tiers: List[tuple[str, List[str]]] = [
        ("tier_1", query_bundle.trend_keywords),
    ]
    if query_bundle.trend_keywords_tier2:
        tiers.append(("tier_2", query_bundle.trend_keywords_tier2))
    if query_bundle.trend_keywords_tier3:
        tiers.append(("tier_3", query_bundle.trend_keywords_tier3))

    # ------------------------------------------------------------------ #
    #  Try each tier in order — stop at first usable result               #
    # ------------------------------------------------------------------ #
    selected_tier: str | None = None
    int_series: List[int] = []

    for tier_name, keywords in tiers:
        print(f"🔍 [SerpAPI] Trying {tier_name.replace('_', ' ').title()} keywords: {keywords}")

        per_keyword_values = _try_keywords(api_key, keywords)

        if not per_keyword_values:
            print(f"⚠️ [SerpAPI] {tier_name} — no data returned")
            continue

        candidate_series = _aggregate_series(per_keyword_values)
        avg_vol = _avg_search_volume(candidate_series)
        growth = _growth_rate_5y(candidate_series)
        momentum = _momentum_score(candidate_series)

        if _is_usable(avg_vol, growth, momentum):
            int_series = candidate_series
            selected_tier = tier_name
            print(f"✅ [SerpAPI] Using Tier: {tier_name}")
            break
        else:
            print(f"⚠️ [SerpAPI] {tier_name} — data returned but not usable (all zeros)")

    if not int_series:
        print("⚠️ [SerpAPI] No usable trend data found across all tiers")
        logger.info("No trend data returned for any tier.")
        return _empty_signals()

    # ------------------------------------------------------------------ #
    #  Compute metrics                                                    #
    # ------------------------------------------------------------------ #
    avg_vol = _avg_search_volume(int_series)
    growth = _growth_rate_5y(int_series)
    momentum = _momentum_score(int_series)
    volatility = _volatility_index(int_series)
    demand = _demand_strength(avg_vol, growth)

    print(f"📊 [SerpAPI] Avg search volume (0-100 scale): {round(avg_vol, 2)}")
    print(f"📈 [SerpAPI] Growth rate (5y): {round(growth, 4)}")
    print(f"⚡ [SerpAPI] Momentum score: {round(momentum, 4)}")
    print(f"📉 [SerpAPI] Volatility index: {round(volatility, 4)}")
    print(f"📊 [SerpAPI] Demand strength (from trends): {round(demand, 4)}")

    # ------------------------------------------------------------------ #
    #  Demand strength enhancement: if trends-based demand is very low,   #
    #  try a secondary proxy from regular Google search results.          #
    # ------------------------------------------------------------------ #
    if demand < 0.05:
        print("⚠️ [SerpAPI] Trends-based demand very low — trying search demand proxy")
        proxies: List[float] = []
        for keyword in query_bundle.trend_keywords[:2]:
            proxy = _fetch_search_demand_proxy(api_key, keyword)
            if proxy > 0:
                proxies.append(proxy)

        if proxies:
            search_proxy = sum(proxies) / len(proxies)
            demand = max(demand, min(1.0, search_proxy))
            print(f"📊 [SerpAPI] Enhanced demand strength (search proxy): {round(demand, 4)}")
        else:
            demand = max(demand, 0.05)
            print("⚠️ [SerpAPI] Demand strength unavailable — setting low-confidence floor")

    print(f"💪 [SerpAPI] Final demand strength: {round(demand, 4)}")
    print(f"📊 [SerpAPI] Normalized demand strength: {round(demand, 4)}")
    print("=" * 60 + "\n")

    return TrendDemandSignals(
        avg_search_volume=round(avg_vol, 2),
        growth_rate_5y=round(growth, 4),
        momentum_score=round(momentum, 4),
        volatility_index=round(volatility, 4),
        demand_strength_score=round(demand, 4),
        trend_data_available=True,
        trend_data_source_tier=selected_tier,
    )


def _empty_signals() -> TrendDemandSignals:
    """Return zero-value signals for graceful degradation."""
    return TrendDemandSignals(
        avg_search_volume=0.0,
        growth_rate_5y=0.0,
        momentum_score=0.0,
        volatility_index=0.0,
        demand_strength_score=0.0,
        trend_data_available=False,
        trend_data_source_tier=None,
    )
