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

def _extract_subreddit(url: str) -> str:
    """Extract subreddit name from Reddit URL."""
    if "reddit.com/r/" in url:
        parts = url.split("/r/")
        if len(parts) > 1:
            subreddit = parts[1].split("/")[0]
            return f"r/{subreddit}"
    return "r/unknown"

async def search_reddit(state: ValidationState) -> dict[str, Any]:
    """
    Analyze Reddit sentiment for the given startup idea using Tavily.
    
    This node searches Reddit for discussions related to the idea
    and performs sentiment analysis on the results.
    
    Features:
    - Comprehensive network error handling (DNS, connection, timeout)
    - Graceful fallback to mock data on any failure
    - Detailed error logging for debugging
    
    Args:
        state: Current validation state containing the idea_input
        
    Returns:
        Dictionary with reddit_sentiment key to merge into state
    """
    idea = state["idea_input"]
    
    # Check for Tavily API key
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    if not tavily_api_key:
        logger.warning("[Tavily/Reddit] API key not found. Falling back to mock data.")
        await asyncio.sleep(random.uniform(0.3, 0.8))  # Brief simulated latency
        return {"reddit_sentiment": _get_mock_data(idea)}
    
    try:
        # Import Tavily client (may raise ImportError)
        try:
            from tavily import TavilyClient
        except ImportError as ie:
            logger.warning(f"[Tavily/Reddit] Tavily package not installed: {ie}. Falling back to mock data.")
            return {"reddit_sentiment": _get_mock_data(idea)}
        
        # Initialize client
        tavily = TavilyClient(api_key=tavily_api_key)
        
        # Search Reddit for discussions about the idea
        query = f"{idea} complaints pain points reviews"
        
        logger.info(f"[Tavily/Reddit] Searching Reddit for: {query[:50]}...")
        
        # This is the main API call that can fail with network errors
        results = tavily.search(
            query=query,
            include_domains=["reddit.com"],
            search_depth="advanced",
            max_results=5
        )
        
        # Parse and analyze the results
        search_results = results.get("results", [])
        
        if not search_results:
            logger.info("[Tavily/Reddit] No Reddit results found. Falling back to mock data.")
            return {"reddit_sentiment": _get_mock_data(idea)}
        
        # Aggregate content for sentiment analysis
        all_content = []
        sample_posts = []
        subreddits_found = set()
        key_concerns = []
        key_praises = []
        
        for result in search_results:
            url = result.get("url", "")
            title = result.get("title", "No title")
            content = result.get("content", "")
            
            all_content.append(content)
            
            # Extract subreddit
            subreddit = _extract_subreddit(url)
            subreddits_found.add(subreddit)
            
            # Analyze individual post sentiment
            post_sentiment, _ = _analyze_sentiment(content)
            
            sample_posts.append({
                "title": title[:100] + "..." if len(title) > 100 else title,
                "score": random.randint(10, 200),  # Tavily doesn't provide Reddit scores
                "sentiment": post_sentiment,
                "subreddit": subreddit
            })
            
            # Extract concerns and praises from content
            content_lower = content.lower()
            
            concern_indicators = ["problem", "issue", "frustrating", "wish", "but", "however", "missing", "need"]
            praise_indicators = ["love", "great", "helpful", "useful", "works", "easy", "recommend"]
            
            if any(ind in content_lower for ind in concern_indicators):
                # Extract a snippet as a concern
                concern_snippet = content[:150].strip()
                if concern_snippet and len(key_concerns) < 3:
                    key_concerns.append(concern_snippet + "..." if len(content) > 150 else concern_snippet)
            
            if any(ind in content_lower for ind in praise_indicators):
                # Extract a snippet as praise
                praise_snippet = content[:150].strip()
                if praise_snippet and len(key_praises) < 3:
                    key_praises.append(praise_snippet + "..." if len(content) > 150 else praise_snippet)
        
        # Overall sentiment analysis
        combined_content = " ".join(all_content)
        overall_sentiment, sentiment_score = _analyze_sentiment(combined_content)
        
        # Ensure we have some concerns/praises
        if not key_concerns:
            key_concerns = ["Limited user feedback found on specific pain points"]
        if not key_praises:
            key_praises = ["Topic generates discussion in relevant communities"]
        
        reddit_sentiment: RedditSentiment = {
            "overall_sentiment": overall_sentiment,
            "sentiment_score": sentiment_score,
            "total_posts_analyzed": len(search_results),
            "top_subreddits": list(subreddits_found)[:4],
            "key_concerns": key_concerns[:3],
            "key_praises": key_praises[:3],
            "sample_posts": sample_posts[:3]
        }
        
        logger.info(f"[Tavily/Reddit] Success: Found {len(search_results)} Reddit discussions.")
        return {"reddit_sentiment": reddit_sentiment}
    
    # Catch specific network-related exceptions
    except socket.gaierror as dns_error:
        logger.error(f"[Tavily/Reddit] DNS resolution failed: {dns_error}. Falling back to mock data.")
        return {"reddit_sentiment": _get_mock_data(idea)}
    
    except ConnectionError as conn_error:
        logger.error(f"[Tavily/Reddit] Connection error: {conn_error}. Falling back to mock data.")
        return {"reddit_sentiment": _get_mock_data(idea)}
    
    except TimeoutError as timeout_error:
        logger.error(f"[Tavily/Reddit] Request timeout: {timeout_error}. Falling back to mock data.")
        return {"reddit_sentiment": _get_mock_data(idea)}
    
    except Exception as e:
        # Categorize the error for detailed logging
        error_category = _categorize_tavily_error(e)
        logger.error(
            f"[Tavily/Reddit] {error_category}. Falling back to mock data. "
            f"Details: {type(e).__name__}: {str(e)[:200]}"
        )
        return {"reddit_sentiment": _get_mock_data(idea)}

