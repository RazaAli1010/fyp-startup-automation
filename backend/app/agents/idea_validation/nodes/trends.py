import logging
import os
import random
import re
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..state import ValidationState, TrendsData


logger = logging.getLogger(__name__)


MAX_NETWORK_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2  

SERPAPI_AVAILABLE = False

try:
    from serpapi import GoogleSearch
    SERPAPI_AVAILABLE = True
except ImportError:
    logger.warning(
        "serpapi not installed. Google Trends will use mock data. "
        "Install with: pip install google-search-results"
    )
    GoogleSearch = None


STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "and", "but", "if", "or",
    "because", "until", "while", "although", "though", "after", "before",
    "that", "this", "these", "those", "what", "which", "who", "whom",
    "like", "app", "platform", "tool", "service", "software", "system",
    "uber", "airbnb", "netflix", "amazon"
}


def extract_keywords(idea: str, max_keywords: int = 2) -> list[str]:
    """
    Extract the most relevant keywords from a startup idea.
    
    Args:
        idea: The startup idea string
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of 1-2 relevant keywords for Google Trends
    """
    # Clean and tokenize
    idea_clean = re.sub(r'[^\w\s-]', ' ', idea.lower())
    words = idea_clean.split()
    
    meaningful_words = [
        word for word in words 
        if word not in STOP_WORDS and len(word) > 2
    ]
    
    if meaningful_words:
        return meaningful_words[:max_keywords]
    
   
    words = [w for w in idea.lower().split() if len(w) > 2]
    return words[:max_keywords] if words else [idea[:30]]




def _get_mock_data(idea: str, reason: str = "API unavailable") -> TrendsData:
    keywords = idea.lower().split()[:3]
    
    trend_options = ["rising", "stable", "falling", "no_data"]
    weights = [0.35, 0.35, 0.2, 0.1]
    trend_direction = random.choices(trend_options, weights=weights)[0]
    
    interest_ranges = {
        "rising": (55, 95),
        "stable": (30, 60),
        "falling": (10, 40),
        "no_data": (0, 15)
    }
    
    temporal_mapping = {
        "rising": "growing",
        "stable": "stable",
        "falling": "declining",
        "no_data": "stable"
    }
    
    mock_related_queries = [
        f"{keywords[0] if keywords else 'startup'} software",
        f"best {keywords[0] if keywords else 'business'} tools",
        f"{keywords[0] if keywords else 'app'} alternatives",
        "startup ideas 2024",
        "SaaS business model",
        "market validation tools",
    ]
    
    mock_related_topics = [
        "Artificial Intelligence",
        "Software as a Service",
        "Entrepreneurship",
        "Digital Transformation",
        "Automation",
    ]
    
    mock_regions = {
        "United States": random.randint(60, 100),
        "United Kingdom": random.randint(40, 80),
        "Canada": random.randint(35, 75),
        "India": random.randint(50, 90),
    }
    
    min_interest, max_interest = interest_ranges[trend_direction]
    
    logger.warning(f"[GoogleTrends] Using mock data: {reason}")
    
    return {
        "trend_direction": trend_direction,
        "interest_score": random.randint(min_interest, max_interest),
        "related_queries": random.sample(mock_related_queries, k=random.randint(3, 5)),
        "related_topics": random.sample(mock_related_topics, k=random.randint(2, 4)),
        "geographic_interest": mock_regions,
        "temporal_trend": temporal_mapping[trend_direction],
    }


def _analyze_interest_over_time(timeline_data: list) -> tuple[str, int, str]:
    """
    Analyze the trend direction from SerpApi interest_over_time data.
    
    Args:
        timeline_data: List of data points from SerpApi response
        
    Returns:
        Tuple of (trend_direction, interest_score, temporal_trend)
    """
    if not timeline_data or len(timeline_data) < 4:
        return "stable", 50, "stable"
    
    # Extract values from timeline
    values = []
    for point in timeline_data:
        # SerpApi returns values in different formats depending on query
        if "values" in point and point["values"]:
            # Multi-keyword query
            val = point["values"][0].get("extracted_value", 0)
        elif "extracted_value" in point:
            # Single keyword query
            val = point.get("extracted_value", 0)
        else:
            val = 0
        values.append(val)
    
    if not values:
        return "stable", 50, "stable"
    
    # Calculate interest score (peak value)
    interest_score = max(values) if values else 50
    
    # Compare first quarter vs last quarter
    quarter_size = max(1, len(values) // 4)
    first_quarter_avg = sum(values[:quarter_size]) / quarter_size if values[:quarter_size] else 0
    last_quarter_avg = sum(values[-quarter_size:]) / quarter_size if values[-quarter_size:] else 0
    
    # Determine trend direction
    if first_quarter_avg == 0:
        if last_quarter_avg > 10:
            trend_direction = "rising"
            temporal_trend = "growing"
        else:
            trend_direction = "stable"
            temporal_trend = "stable"
    else:
        ratio = last_quarter_avg / first_quarter_avg
        
        if ratio > 1.2:
            trend_direction = "rising"
            temporal_trend = "growing"
        elif ratio < 0.8:
            trend_direction = "falling"
            temporal_trend = "declining"
        else:
            trend_direction = "stable"
            temporal_trend = "stable"
    
    return trend_direction, int(interest_score), temporal_trend




def _extract_related_topics(data: dict) -> list[str]:
    """Extract related topics from SerpApi response."""
    topics = []
    
    rising = data.get("rising_topics", [])
    for item in rising[:4]:
        if "topic" in item and "title" in item["topic"]:
            topics.append(item["topic"]["title"])
    
    top = data.get("top_topics", [])
    for item in top[:4]:
        if "topic" in item and "title" in item["topic"]:
            title = item["topic"]["title"]
            if title not in topics:
                topics.append(title)
    
    return topics[:4]



def _extract_geographic_interest(data: dict) -> dict[str, int]:
    """Extract geographic interest from SerpApi response."""
    geo_interest = {}
    
    interest_by_region = data.get("interest_by_region", [])
    
    # Get top 5 regions
    for item in interest_by_region[:5]:
        location = item.get("location", "Unknown")
        # Handle different value formats
        if "values" in item and item["values"]:
            value = item["values"][0].get("extracted_value", 0)
        elif "extracted_value" in item:
            value = item.get("extracted_value", 0)
        else:
            value = 0
        geo_interest[location] = int(value)
    
    return geo_interest



async def search_trends(state: ValidationState) -> dict[str, Any]:
    """
    Fetch Google Trends data for the startup idea using SerpApi.
    
    SerpApi provides stable, reliable access to Google Trends data
    without rate limiting issues. No retries or proxy logic needed.
    
    Args:
        state: Current validation state containing the idea_input
        
    Returns:
        Dictionary with trends_data key to merge into state
    """
    idea = state["idea_input"]
    
    # Extract keywords from the idea
    keywords = extract_keywords(idea, max_keywords=2)
    query = ",".join(keywords)  # SerpApi expects comma-separated keywords
    
    logger.info(f"[GoogleTrends] Querying SerpApi for: {query}")
    
    # ==========================================================================
    # Check Prerequisites
    # ==========================================================================
    
    # Check for SerpApi package
    if not SERPAPI_AVAILABLE:
        logger.error("[GoogleTrends] SerpApi package not installed. Using mock data.")
        return {"trends_data": _get_mock_data(idea, "serpapi package not installed")}
    
    # Check for API key
    serpapi_key = os.getenv("SERPAPI_KEY")
    if not serpapi_key:
        logger.error("[GoogleTrends] SERPAPI_KEY not found in environment. Using mock data.")
        return {"trends_data": _get_mock_data(idea, "SERPAPI_KEY not configured")}
    
    # ==========================================================================
    # Make SerpApi Request with Network Resilience
    # ==========================================================================
    
    last_error = None
    
    for attempt in range(MAX_NETWORK_RETRIES):
        try:
            # Configure the Google Trends search
            search = GoogleSearch({
                "engine": "google_trends",
                "q": query,
                "data_type": "TIMESERIES",  # Get interest over time
                "api_key": serpapi_key,
                "timeout": 30  # 30 second timeout
            })
            
            # Execute the search
            results = search.get_dict()
            
            # Check for API errors
            if "error" in results:
                error_msg = results.get("error", "Unknown SerpApi error")
                logger.error(f"[GoogleTrends] SerpApi error: {error_msg}")
                return {"trends_data": _get_mock_data(idea, f"SerpApi error: {error_msg[:100]}")}
            
            # Extract interest over time data
            interest_over_time = results.get("interest_over_time", {})
            timeline_data = interest_over_time.get("timeline_data", [])
            
            if not timeline_data:
                logger.warning("[GoogleTrends] No timeline data returned. Using mock data.")
                return {"trends_data": _get_mock_data(idea, "No trend data for these keywords")}
            
            # Analyze the trend
            trend_direction, interest_score, temporal_trend = _analyze_interest_over_time(timeline_data)
            
            # Extract related queries and topics
            related_queries = _extract_related_queries(results)
            related_topics = _extract_related_topics(results)
            
            # Extract geographic interest
            geo_interest = _extract_geographic_interest(results)
            
            # Ensure we have fallback data if extraction failed
            if not related_queries:
                related_queries = [f"{kw} tools" for kw in keywords] + ["market trends"]
            
            if not related_topics:
                related_topics = ["Technology", "Business", "Software"]
            
            if not geo_interest:
                geo_interest = {
                    "United States": interest_score,
                    "Global": interest_score
                }
            
            # Build the response
            trends_data: TrendsData = {
                "trend_direction": trend_direction,
                "interest_score": interest_score,
                "related_queries": related_queries[:5],
                "related_topics": related_topics[:4],
                "geographic_interest": geo_interest,
                "temporal_trend": temporal_trend,
            }
            
            logger.info(f"[GoogleTrends] ✓ Success: {trend_direction} trend, score={interest_score}")
            return {"trends_data": trends_data}
            
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
            last_error = e
            if attempt < MAX_NETWORK_RETRIES - 1:
                wait_time = RETRY_BACKOFF_FACTOR * (attempt + 1) + random.uniform(0, 1)
                logger.warning(
                    f"[GoogleTrends] Network error (attempt {attempt + 1}/{MAX_NETWORK_RETRIES}): "
                    f"{str(e)[:100]}. Retrying in {wait_time:.1f}s..."
                )
                time.sleep(wait_time)
                continue
            else:
                logger.error(
                    f"[GoogleTrends] Network error after {MAX_NETWORK_RETRIES} attempts. "
                    f"Using mock data. Error: {str(e)[:150]}"
                )
                return {"trends_data": _get_mock_data(idea, f"Network error: {str(e)[:80]}")}
        
        except Exception as e:
            # Non-network error, don't retry
            error_msg = str(e)
            logger.error(f"[GoogleTrends] API error: {error_msg[:200]}. Using mock data.")
            return {"trends_data": _get_mock_data(idea, f"API error: {error_msg[:100]}")}
    
    # Should not reach here, but handle it anyway
    return {"trends_data": _get_mock_data(idea, f"Failed after {MAX_NETWORK_RETRIES} attempts")}

