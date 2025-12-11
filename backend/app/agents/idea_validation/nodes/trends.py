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