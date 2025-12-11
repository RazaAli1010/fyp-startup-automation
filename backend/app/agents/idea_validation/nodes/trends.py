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