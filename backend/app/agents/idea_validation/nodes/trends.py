"""
Google Trends Analysis Node (Async Optimized)

Uses SerpAPI to fetch Google Trends data with domain-specific queries,
zero-volume detection, and structured outputs.

PERFORMANCE OPTIMIZATIONS:
- Async HTTP calls with httpx
- Concurrent query execution
- Reduced API calls per query (1 combined call instead of 4)
- 8s timeout per request
- Max 2 retries with 1.5s backoff
"""

import os
import re
import statistics
import asyncio
from typing import Dict, List, Any, Optional, Tuple

import httpx
from openai import AsyncOpenAI
import math

from ..state import ValidationState, TrendsData, QualityMetrics
from ..timing import StepTimer, log_timing
from ..http_client import Timeouts, RetryConfig
from ..epistemic_types import (
    QueryIntent, TRANSACTIONAL_SIGNALS, COMMERCIAL_SIGNALS,
    INTENT_CONFIDENCE_MODIFIERS
)


# Configuration
MIN_DATA_POINTS = 10
MIN_NONZERO_RATIO = 0.2
EMBEDDING_MODEL = "text-embedding-3-small"

# Domain query generation is now dynamic based on intent_keywords
# Removed PARKING_DOMAIN_QUERIES

# Blacklisted query terms (should never generate)
BLACKLISTED_TERMS = {
    "openai", "chatgpt", "technology news", "subscription price",
    "news", "stock", "weather", "sports", "celebrity", "politics",
    "news", "stock", "weather", "sports", "celebrity", "politics",
    "crypto", "bitcoin", "nft", "breaking news", "trending"
}

# Generic terms that indicate low-confidence signal if they are the primary query
GENERIC_TERMS = {
    "software", "app", "website", "platform", "tool", "service", 
    "business", "startup", "company", "market", "industry",
    "online", "digital", "technology", "tech", "solutions"
}

# SerpAPI base URL
SERPAPI_BASE_URL = "https://serpapi.com/search"


def _get_serpapi_key() -> str:
    """Get SerpAPI key from environment."""
    key = os.getenv("SERPAPI_KEY")
    if not key:
        raise ValueError("SERPAPI_KEY environment variable not set")
    return key


def _classify_query_intent(query: str) -> QueryIntent:
    """
    Classify the user intent behind a search query.
    Used to weight the confidence of the trend signal.
    """
    query_lower = query.lower()
    
    # Check for transactional signals
    for signal in TRANSACTIONAL_SIGNALS:
        if signal in query_lower:
            return QueryIntent.TRANSACTIONAL
            
    # Check for commercial investigation signals
    for signal in COMMERCIAL_SIGNALS:
        if signal in query_lower:
            return QueryIntent.COMMERCIAL
            
    # Check for navigational/brand signals (simple heuristic)
    if "login" in query_lower or "support" in query_lower:
        return QueryIntent.NAVIGATIONAL
        
    return QueryIntent.INFORMATIONAL


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def _generate_intent_queries(idea: str, intent_keywords: List[str]) -> List[str]:
    """
    Generate domain-specific search queries using extracted intent keywords.
    """
    queries = []
    
    if intent_keywords:
        # Use top keywords (noun + verb combinations if possible)
        # Try to form search phrases that reflect user intent
        
        # 1. Broad category
        if len(intent_keywords) >= 1:
            queries.append(f"{intent_keywords[0]} trends")
            queries.append(f"{intent_keywords[0]} industry")
            
        # 2. Specific intent (noun + verb)
        if len(intent_keywords) >= 2:
            base = " ".join(intent_keywords[:2])
            queries.append(base)
            queries.append(f"{base} service")
            queries.append(f"{base} app")
            
        # 3. Problem/Solution phrasing
        if len(intent_keywords) >= 3:
            random_noun = intent_keywords[0]
            random_verb = intent_keywords[1] if len(intent_keywords) > 1 else "service"
            queries.append(f"best {random_noun} {random_verb}")

    # Fallback to idea processing if keywords sparse
    words = re.split(r'[\s\-_,;:\.!?\'\"()\[\]{}]+', idea.lower())
    stop_words = {
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'this',
        'that', 'it', 'app', 'platform', 'service', 'tool', 'using', 'based'
    }
    meaningful = [w for w in words if w.isalpha() and len(w) > 3 and w not in stop_words]
    
    if meaningful:
        # Two-word combinations
        if len(meaningful) >= 2:
            queries.append(f"{meaningful[0]} {meaningful[1]}")
        
        # Single most specific term
        for word in meaningful[:2]:
            if word not in BLACKLISTED_TERMS:
                queries.append(f"{word} market")
    
    # Validate and deduplicate
    seen = set()
    valid_queries = []
    for q in queries:
        q_clean = q.strip().lower()
        
        # Skip if blacklisted
        if any(bl in q_clean for bl in BLACKLISTED_TERMS):
            continue
        
        # Skip if already seen
        if q_clean in seen:
            continue
        
        # Validate query
        if _validate_query(q_clean):
            seen.add(q_clean)
            valid_queries.append(q_clean)
    
    return valid_queries[:5]


def _validate_query(query: str) -> bool:
    """Validate query is sensible for Google Trends."""
    if not query or len(query) < 3:
        return False
    
    # Must have alphabetic characters
    alpha_count = sum(1 for c in query if c.isalpha())
    if alpha_count < len(query) * 0.5:
        return False
    
    # No camelCase
    if re.search(r'[a-z][A-Z]', query):
        return False
    
    # Must have vowel (real word check)
    if not re.search(r'[aeiou]', query.lower()):
        return False
    
    return True


async def _fetch_trends_async(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
    data_type: str = "TIMESERIES",
    geo: str = "",
    timeout: float = Timeouts.SERPAPI
) -> Dict[str, Any]:
    """
    Fetch Google Trends data from SerpAPI asynchronously.
    """
    params = {
        "engine": "google_trends",
        "q": query,
        "data_type": data_type,
        "api_key": api_key
    }
    
    if geo:
        params["geo"] = geo
    
    for attempt in range(RetryConfig.MAX_RETRIES + 1):
        try:
            response = await client.get(
                SERPAPI_BASE_URL,
                params=params,
                timeout=timeout
            )
            
            if response.status_code == 200:
                return response.json()
            
            # Non-retryable errors
            if response.status_code in RetryConfig.NON_RETRYABLE_CODES:
                log_timing("trends", f"SerpAPI non-retryable error: {response.status_code}")
                return {}
            
            # Retryable errors
            if attempt < RetryConfig.MAX_RETRIES:
                backoff = min(
                    RetryConfig.INITIAL_BACKOFF * (2 ** attempt),
                    RetryConfig.MAX_BACKOFF
                )
                await asyncio.sleep(backoff)
                
        except httpx.TimeoutException:
            log_timing("trends", f"SerpAPI timeout on attempt {attempt + 1}")
            if attempt < RetryConfig.MAX_RETRIES:
                await asyncio.sleep(RetryConfig.INITIAL_BACKOFF)
        except Exception as e:
            log_timing("trends", f"SerpAPI error: {str(e)[:50]}")
            return {}
    
    return {}


async def _get_embeddings_batch(
    client: AsyncOpenAI,
    texts: List[str],
    timeout: float = Timeouts.OPENAI_EMBEDDING
) -> List[List[float]]:
    """Helper to get embeddings."""
    if not texts:
        return []
    try:
        response = await asyncio.wait_for(
            client.embeddings.create(model=EMBEDDING_MODEL, input=texts[:20]), # Limit batch size
            timeout=timeout
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        log_timing("trends", f"Embedding error: {e}")
        return [[] for _ in texts]



async def _fetch_all_trends_data(
    client: httpx.AsyncClient,
    api_key: str,
    query: str
) -> Tuple[List[Dict], Dict[str, int], List[str], List[str], bool]:
    """
    Fetch all trends data for a query with concurrent API calls.
    Returns (time_series, geography, related_queries, related_topics, success).
    
    OPTIMIZED: Run timeseries + related_queries concurrently (2 calls instead of 4)
    Skip GEO_MAP and RELATED_TOPICS to reduce API calls
    """
    # Run timeseries and related queries concurrently
    timeseries_task = _fetch_trends_async(client, api_key, query, "TIMESERIES")
    related_task = _fetch_trends_async(client, api_key, query, "RELATED_QUERIES")
    
    results = await asyncio.gather(timeseries_task, related_task, return_exceptions=True)
    
    timeseries_result = results[0] if isinstance(results[0], dict) else {}
    related_result = results[1] if isinstance(results[1], dict) else {}
    
    # Extract time series
    time_series = []
    interest_over_time = timeseries_result.get("interest_over_time", {})
    timeline_data = interest_over_time.get("timeline_data", [])
    
    for point in timeline_data:
        date = point.get("date", "")
        values = point.get("values", [])
        if values:
            value = values[0].get("extracted_value", 0)
            time_series.append({"date": date, "value": value, "query": query})
    
    # Extract related queries
    related_queries = []
    rising = related_result.get("related_queries", {}).get("rising", [])
    for item in rising[:5]:
        q = item.get("query", "")
        if q and q.lower() not in BLACKLISTED_TERMS:
            related_queries.append(q)
    
    # Skip related topics and geography to reduce API calls
    related_topics = []
    geography = {}
    
    success = len(time_series) > 0
    
    return time_series, geography, related_queries, related_topics, success


def _analyze_trend(time_series: List[Dict]) -> Tuple[str, int, str, float, float]:
    """
    Analyze trend direction and calculate metrics.
    Returns (direction, interest_score, temporal_trend, slope, confidence).
    
    IMPORTANT: Ensures no contradictory outputs (e.g., insufficient_data + growing).
    """
    if len(time_series) < MIN_DATA_POINTS:
        # Insufficient data - return consistent values
        return "insufficient_data", 0, "insufficient_data", 0.0, 0.0
    
    values = [point["value"] for point in time_series]
    
    # Check for all-zero or low-volume data
    nonzero_count = sum(1 for v in values if v > 0)
    nonzero_ratio = nonzero_count / len(values)
    
    if nonzero_ratio < MIN_NONZERO_RATIO:
        # Zero volume - return consistent values
        return "insufficient_data", 0, "insufficient_data", 0.0, 0.0
    
    # Calculate current interest score
    recent_values = values[-10:] if len(values) >= 10 else values
    interest_score = int(sum(recent_values) / len(recent_values))
    
    # Calculate linear regression slope
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        slope = 0.0
    else:
        slope = numerator / denominator
    
    # Normalize slope
    normalized_slope = slope / max(y_mean, 1) if y_mean > 0 else 0
    
    # Calculate R-squared for confidence
    predictions = [y_mean + slope * (i - x_mean) for i in range(n)]
    ss_res = sum((v - p) ** 2 for v, p in zip(values, predictions))
    ss_tot = sum((v - y_mean) ** 2 for v in values)
    
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    r_squared = max(0, min(1, r_squared))
    
    # Determine trend direction
    if normalized_slope > 0.02:
        direction = "rising"
    elif normalized_slope < -0.02:
        direction = "falling"
    else:
        direction = "stable"
    
    # Determine temporal trend (must be consistent with direction)
    third = len(values) // 3
    if third > 0:
        first_third_avg = sum(values[:third]) / third
        last_third_avg = sum(values[-third:]) / third
        
        if last_third_avg > first_third_avg * 1.2:
            temporal_trend = "growing"
        elif last_third_avg < first_third_avg * 0.8:
            temporal_trend = "declining"
        else:
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
            cv = std_dev / y_mean if y_mean > 0 else 0
            if cv > 0.4:
                temporal_trend = "seasonal"
            else:
                temporal_trend = "stable"
    else:
        temporal_trend = "stable"
    
    # Ensure consistency between direction and temporal_trend
    # If direction is insufficient_data, temporal must also be
    if direction == "insufficient_data":
        temporal_trend = "insufficient_data"
    
    # Calculate confidence
    base_confidence = min(nonzero_ratio, 1.0)
    confidence = base_confidence * (0.5 + 0.5 * r_squared)
    confidence = max(0.1, min(0.95, confidence))
    
    return direction, interest_score, temporal_trend, normalized_slope, confidence


def _is_generic_query(query: str) -> bool:
    """Check if a query is too generic to provide a strong signal."""
    # Single words that are in the generic list
    words = query.lower().split()
    if len(words) == 1 and words[0] in GENERIC_TERMS:
        return True
    
    # Very short queries (unlikely to be specific intent)
    if len(query) < 4:
        return True
        
    return False


async def search_trends(state: ValidationState) -> Dict[str, Any]:
    """
    Search Google Trends for interest in the startup idea.
    
    ASYNC OPTIMIZED:
    - Concurrent query execution
    - Reduced API calls per query (2 instead of 4)
    - 8s timeout per request
    - Max 2 retries
    """
    timer = StepTimer("trends")
    
    idea_input = state.get("idea_input", "")
    processing_errors = list(state.get("processing_errors", []))
    
    if not idea_input:
        return {
            "trends_data": _insufficient_data_response(["no_idea_provided"]),
            "processing_errors": processing_errors + ["Trends: No idea provided"]
        }
    
    try:
        api_key = _get_serpapi_key()
    except ValueError as e:
        return {
            "trends_data": _insufficient_data_response([str(e)]),
            "processing_errors": processing_errors + [f"Trends: {str(e)}"]
        }
    
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
             raise ValueError("OPENAI_API_KEY not set")
    except ValueError as e:
         # Continue without semantic validation if key missing, but warn
         log_timing("trends", "OpenAI key missing, skipping semantic validation")
         openai_key = None

    # Get global embedding and intent from state
    idea_embedding = state.get("idea_embedding", [])
    intent_keywords = state.get("intent_keywords", [])
    
    # Generate queries using intent keywords
    queries = _generate_intent_queries(idea_input, intent_keywords)
    
    if not queries:
        timer.summary()
        return {
            "trends_data": _insufficient_data_response(["no_valid_queries_generated"]),
            "processing_errors": processing_errors + ["Trends: No valid queries"]
        }
    
    # Fetch trends data CONCURRENTLY for all queries
    async with timer.async_step("serpapi_search"):
        async with httpx.AsyncClient() as client:
            search_tasks = [
                _fetch_all_trends_data(client, api_key, query)
                for query in queries
            ]
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
    
    # Aggregate results
    async with timer.async_step("aggregation"):
        all_time_series = []
        all_geography: Dict[str, int] = {}
        all_related_queries: List[str] = []
        all_related_topics: List[str] = []
        successful_queries = []
        failed_queries = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_queries.append(queries[i])
                continue
            
            time_series, geography, related_queries, related_topics, success = result
            
            if success and time_series:
                all_time_series.extend(time_series)
                successful_queries.append(queries[i])
                all_related_queries.extend(related_queries)
                all_related_topics.extend(related_topics)
                
                for region, interest in geography.items():
                    if region in all_geography:
                        all_geography[region] = max(all_geography[region], interest)
                    else:
                        all_geography[region] = interest
            else:
                failed_queries.append(queries[i])
    
    # Check if we have any data
    if not all_time_series:
        timer.summary()
        return {
            "trends_data": _insufficient_data_response([
                "no_trends_data_returned",
                "all_queries_returned_empty",
                f"failed_queries: {len(failed_queries)}"
            ]),
            "processing_errors": processing_errors + ["Trends: No data returned from any query"]
        }
    
    # Aggregate time series
    date_values: Dict[str, List[int]] = {}
    for point in all_time_series:
        date = point["date"]
        value = point["value"]
        if date in date_values:
            date_values[date].append(value)
        else:
            date_values[date] = [value]
    
    averaged_series = []
    for date in sorted(date_values.keys()):
        values = date_values[date]
        avg_value = sum(values) / len(values)
        averaged_series.append({
            "date": date,
            "value": round(avg_value, 1),
            "query": ", ".join(successful_queries[:2])
        })
    
    # Analyze trend
    trend_direction, interest_score, temporal_trend, slope, confidence = _analyze_trend(averaged_series)
    
    # EPISTEMIC RIGOUR: Adjust confidence based on query intent
    intent_modifiers = []
    has_transactional = False
    
    for q in successful_queries:
        intent = _classify_query_intent(q)
        modifier = INTENT_CONFIDENCE_MODIFIERS.get(intent, 0.0)
        intent_modifiers.append(modifier)
        
        if intent == QueryIntent.TRANSACTIONAL:
            has_transactional = True
            
    # Apply average intent modifier
    if intent_modifiers:
        avg_modifier = sum(intent_modifiers) / len(intent_modifiers)
        confidence = max(0.1, min(1.0, confidence + avg_modifier))
        
    # Penalize if NO transactional queries found for a commercial idea
    if not has_transactional:
        confidence *= 0.9
        
    # Penalize confidence if queries are generic
    is_generic = False
    if successful_queries:
        # Check if ALL successful queries are generic
        all_generic = all(_is_generic_query(q) for q in successful_queries)
        if all_generic:
            is_generic = True
            confidence *= 0.5  # Heavy penalty for generic trends
            confidence = min(confidence, 0.4) # Cap at 0.4
    
    # Initialize warnings list early (before semantic validation)
    warnings = []
            
    # Deduplicate related queries/topics
    all_related_queries = list(dict.fromkeys(all_related_queries))
    all_related_topics = list(dict.fromkeys(all_related_topics))
    
    # Semantic Validation of Related Queries
    if idea_embedding and openai_key and (all_related_queries or all_related_topics):
        async with timer.async_step("semantic_filtering"):
            openai_client = AsyncOpenAI(api_key=openai_key)
            
            # Combine items to embed
            items_to_check = all_related_queries[:15] + all_related_topics[:10]
            
            if items_to_check:
                embeddings = await _get_embeddings_batch(openai_client, items_to_check)
                
                valid_items = []
                for i, item in enumerate(items_to_check):
                    if i < len(embeddings) and embeddings[i]:
                        sim = _cosine_similarity(idea_embedding, embeddings[i])
                        if sim > 0.4:  # Threshold for relevance
                            valid_items.append(item)
                
                # Update lists with only valid items
                # If we filtered everything, keep top 1 original just to have something (marked as low relevance in UI maybe?)
                # actually, better to return "No relevant related queries"
                
                # Split back
                validated_queries = [x for x in valid_items if x in all_related_queries]
                validated_topics = [x for x in valid_items if x in all_related_topics]
                
                if len(validated_queries) < len(all_related_queries) * 0.4:
                     warnings.append("high_noise_in_related_queries")
                     
                all_related_queries = validated_queries
                all_related_topics = validated_topics

    # Limit final lists
    all_related_queries = all_related_queries[:10]
    all_related_topics = all_related_topics[:10]
    
    # Determine search volume category
    if interest_score >= 70:
        search_volume_category = "high"
    elif interest_score >= 40:
        search_volume_category = "medium"
    elif interest_score >= 20:
        search_volume_category = "low"
    else:
        search_volume_category = "very_low"
    
    # Build warnings (warnings list initialized earlier for semantic filtering)
    if len(averaged_series) < MIN_DATA_POINTS:
        warnings.append("low_data_points")
    if len(failed_queries) > len(successful_queries):
        warnings.append("many_failed_queries")
    if not all_geography:
        warnings.append("no_geographic_data")
    if interest_score < 20:
        warnings.append("very_low_search_interest")
    if trend_direction == "insufficient_data":
        warnings.append("insufficient_trend_data")
    if is_generic:
        warnings.append("generic_trend_signal_only")
    
    quality: QualityMetrics = {
        "data_volume": len(averaged_series),
        "relevance_mean": len(successful_queries) / len(queries) if queries else 0,
        "confidence": round(confidence, 3),
        "warnings": warnings
    }
    
    # Ensure no contradictions in output
    if trend_direction == "insufficient_data":
        temporal_trend = "insufficient_data"
        interest_score = 0
        confidence = 0.0
    
    trends_data: TrendsData = {
        "trend_direction": trend_direction,
        "interest_score": interest_score,
        "related_queries": all_related_queries if all_related_queries else ["No related queries found"],
        "related_topics": all_related_topics if all_related_topics else ["No related topics found"],
        "geographic_interest": all_geography if all_geography else {"Unknown": 0},
        "temporal_trend": temporal_trend,
        "quality": quality
    }
    
    timer.summary()
    return {"trends_data": trends_data}


def _insufficient_data_response(warnings: List[str]) -> TrendsData:
    """Generate a consistent insufficient data response."""
    return {
        "trend_direction": "insufficient_data",
        "interest_score": 0,
        "related_queries": [],
        "related_topics": [],
        "geographic_interest": {},
        "temporal_trend": "insufficient_data",
        "quality": {
            "data_volume": 0,
            "relevance_mean": 0.0,
            "confidence": 0.0,
            "warnings": warnings
        }
    }
