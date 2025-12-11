import asyncio
import logging
import os
import random
import socket
from typing import Any

from ..state import ValidationState, RedditSentiment


logger = logging.getLogger(__name__)


def _is_network_error(error: Exception) -> tuple[bool, str]:
    
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # DNS resolution errors
    if isinstance(error, socket.gaierror) or "getaddrinfo" in error_str:
        return True, "DNS resolution failed"
    
    # Connection errors (check string patterns)
    if any(term in error_str for term in [
        "connectionerror", "connection refused", "connection reset",
        "connection aborted", "connection timeout", "nameresolutionerror",
        "nodename nor servname", "temporary failure in name resolution"
    ]):
        return True, "Connection error"
    
    # Timeout errors
    if any(term in error_str for term in ["timeout", "timed out"]):
        return True, "Request timeout"
    
    # SSL/TLS errors
    if any(term in error_str for term in ["ssl", "certificate", "handshake"]):
        return True, "SSL/TLS error"
    
    # Check for requests library specific errors
    if "requests.exceptions" in error_type or "urllib3" in error_type:
        return True, "HTTP client error"
    
    # Check for httpx/aiohttp specific errors (if Tavily uses these)
    if any(lib in error_type.lower() for lib in ["httpx", "aiohttp", "clienterror"]):
        return True, "Async HTTP error"
    
    return False, "Unknown error"

def _categorize_tavily_error(error: Exception) -> str:
    
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # Check for network errors first
    is_network, network_category = _is_network_error(error)
    if is_network:
        return f"Network error ({network_category})"
    
    # API-specific errors
    if "api" in error_type.lower() or "tavily" in error_type.lower():
        if "key" in error_str or "auth" in error_str or "401" in error_str:
            return "Authentication error (invalid API key)"
        if "rate" in error_str or "429" in error_str or "limit" in error_str:
            return "Rate limit exceeded"
        if "400" in error_str or "bad request" in error_str:
            return "Bad request (invalid parameters)"
        if "500" in error_str or "502" in error_str or "503" in error_str:
            return "Tavily server error"
        return "Tavily API error"
    
    # Generic categorization
    if "json" in error_str or "decode" in error_str:
        return "Invalid response format"
    
    return f"Unexpected error: {error_type}"

def _get_mock_data(idea: str) -> RedditSentiment:
    
    keywords = idea.lower().split()
    
    sentiment_options = ["positive", "neutral", "mixed", "negative"]
    weights = [0.3, 0.35, 0.25, 0.1]
    overall_sentiment = random.choices(sentiment_options, weights=weights)[0]
    
    sentiment_scores = {
        "positive": random.uniform(0.3, 0.8),
        "neutral": random.uniform(-0.2, 0.2),
        "mixed": random.uniform(-0.1, 0.3),
        "negative": random.uniform(-0.8, -0.2)
    }
    
    mock_subreddits = [
        "r/startups", "r/entrepreneur", "r/SaaS", 
        "r/smallbusiness", "r/Startup_Ideas", "r/Business_Ideas"
    ]
    
    mock_concerns = [
        "Market might be too saturated",
        "Customer acquisition cost could be high",
        "Technical implementation complexity",
        "Regulatory challenges in some regions",
        "Existing solutions already address this"
    ]
    
    mock_praises = [
        "Solves a real pain point",
        "Good timing with market trends",
        "Clear monetization path",
        "Strong differentiation potential",
        "Growing demand in this space"
    ]
    
    return {
        "overall_sentiment": overall_sentiment,
        "sentiment_score": round(sentiment_scores[overall_sentiment], 2),
        "total_posts_analyzed": random.randint(15, 150),
        "top_subreddits": random.sample(mock_subreddits, k=random.randint(2, 4)),
        "key_concerns": random.sample(mock_concerns, k=random.randint(1, 3)),
        "key_praises": random.sample(mock_praises, k=random.randint(1, 3)),
        "sample_posts": [
            {
                "title": f"Anyone building something for {keywords[0] if keywords else 'this space'}?",
                "score": random.randint(10, 500),
                "sentiment": "positive",
                "subreddit": "r/startups"
            },
            {
                "title": f"Thoughts on {idea[:50]}...",
                "score": random.randint(5, 200),
                "sentiment": overall_sentiment,
                "subreddit": "r/entrepreneur"
            },
            {
                "title": f"Market analysis: {keywords[0] if keywords else 'startup'} industry",
                "score": random.randint(20, 300),
                "sentiment": "neutral",
                "subreddit": "r/Business_Ideas"
            }
        ]
    }

def _analyze_sentiment(content: str) -> tuple[str, float]:
    
    content_lower = content.lower()
    
    positive_keywords = [
        "love", "great", "amazing", "awesome", "excellent", "fantastic",
        "helpful", "useful", "works well", "recommend", "perfect", "solved",
        "easy", "intuitive", "efficient", "impressed", "game changer"
    ]
    
    negative_keywords = [
        "hate", "terrible", "awful", "horrible", "worst", "frustrating",
        "useless", "broken", "doesn't work", "waste", "scam", "avoid",
        "confusing", "complicated", "buggy", "disappointed", "overpriced"
    ]
    
    positive_count = sum(1 for kw in positive_keywords if kw in content_lower)
    negative_count = sum(1 for kw in negative_keywords if kw in content_lower)
    
    total = positive_count + negative_count
    if total == 0:
        return "neutral", 0.0
    
    score = (positive_count - negative_count) / max(total, 1)
    score = max(-1.0, min(1.0, score))  # Clamp to [-1, 1]
    
    if score > 0.2:
        sentiment = "positive"
    elif score < -0.2:
        sentiment = "negative"
    elif positive_count > 0 and negative_count > 0:
        sentiment = "mixed"
    else:
        sentiment = "neutral"
    
    return sentiment, round(score, 2)
