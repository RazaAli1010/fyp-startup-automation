"""
Reddit Sentiment Analysis Node (Async Optimized)

Uses Tavily API to search Reddit for discussions about the startup idea,
with domain-specific relevance filtering and weighted sentiment analysis.

PERFORMANCE OPTIMIZATIONS:
- Async HTTP calls with httpx
- Concurrent query execution
- Batched embedding calls
- 8s timeout per request
- Max 2 retries with 1.5s backoff
"""

import os
import re
import math
import statistics
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

import httpx
from openai import AsyncOpenAI
from textblob import TextBlob

from ..state import ValidationState, RedditSentiment, SamplePost, QualityMetrics
from ..timing import StepTimer, log_timing
from ..http_client import Timeouts, RetryConfig, get_timeout
from ..epistemic_types import TRANSACTIONAL_SIGNALS, PRODUCT_SIGNALS


# Configuration
RELEVANCE_THRESHOLD = 0.55
HIGH_RELEVANCE_THRESHOLD = 0.75
MIN_SAMPLE_SIZE = 50
MAX_SAMPLE_SIZE = 200
MIN_CONTENT_LENGTH = 50
EMBEDDING_MODEL = "text-embedding-3-small"

# Domain-specific keywords are now dynamically extracted from state['intent_keywords']
# Removing hardcoded PARKING_DOMAIN_KEYWORDS

# Excluded subreddits (off-domain communities)
EXCLUDED_SUBREDDITS = {
    "vanlife", "vandwellers", "rvliving", "frugal", "digitalnomad",
    "overlanding", "truckers", "trucking", "gorving", "skoolies",
    "priusdwellers", "urbancarliving", "homeless", "vagabond",
    "solotravel", "backpacking", "camping", "hiking", "roadtrip"
}


def _get_api_keys() -> Tuple[str, str]:
    """Get API keys from environment."""
    tavily_key = os.getenv("TAVILY_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not tavily_key:
        raise ValueError("TAVILY_API_KEY environment variable not set")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    return tavily_key, openai_key


def _extract_domain_context(idea: str, intent_keywords: List[str]) -> List[str]:
    """
    Extract domain-specific context from the idea using global intent keywords.
    """
    # Use the intent keywords extracted by the upstream node
    if intent_keywords:
        return intent_keywords
    
    # Fallback extraction if no keywords provided
    idea_lower = idea.lower()
    words = re.split(r'[\s\-_,;:\.!?\'\"()\[\]{}]+', idea_lower)
    meaningful = [w for w in words if len(w) > 3 and w.isalpha()]
    
    return meaningful[:10]


def _generate_reddit_queries(idea: str, domain_keywords: List[str]) -> List[str]:
    """
    Generate domain-specific Reddit search queries.
    """
    queries = []
    
    # Base query with the idea
    queries.append(f"{idea} site:reddit.com")
    
    # Intent-anchored queries
    if domain_keywords:
        # Combine idea core with domain keywords
        for keyword in domain_keywords[:3]:
            queries.append(f"{keyword} reddit discussion")
            queries.append(f"{keyword} opinions experience")
            
        # Specific intent queries
        core_intent = " ".join(domain_keywords[:2])
        queries.append(f"{core_intent} reddit")
        queries.append(f"{core_intent} app service")
    
    # Deduplicate
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)
    
    return unique[:8]


def _is_excluded_subreddit(subreddit: str) -> bool:
    """Check if subreddit should be excluded."""
    if not subreddit:
        return False
    return subreddit.lower().strip() in EXCLUDED_SUBREDDITS


def _clean_text(text: str) -> str:
    """
    Clean text by removing noise, boilerplate, and broken content.
    Returns empty string if content is garbage.
    """
    if not text:
        return ""
    
    # Remove common boilerplate patterns
    boilerplate_patterns = [
        r'cookie\s*(policy|consent|banner)',
        r'accept\s*all\s*cookies',
        r'(privacy|terms)\s*(policy|of\s*service)',
        r'subscribe\s*to\s*(our)?\s*newsletter',
        r'sign\s*up\s*for\s*(our)?\s*newsletter',
        r'(click|tap)\s*here\s*to',
        r'advertisement',
        r'sponsored\s*content',
        r'\[deleted\]',
        r'\[removed\]',
        r'u/\w+',
        r'r/\w+\s*•',
        r'\d+\s*(upvotes?|points?|comments?)',
        r'(ago|hours?|days?|weeks?|months?)\s*$',
        r'<[^>]+>',  # HTML tags
        r'&\w+;',  # HTML entities
        r'javascript:',
        r'onclick=',
    ]
    
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    
    # Remove base64 encoded content
    text = re.sub(r'data:[^;]+;base64,[A-Za-z0-9+/=]+', '', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove truncation indicators
    truncation_patterns = [r'\.\.\.$', r'…$', r'\.{3,}$', r'\s+\.\s*$']
    for pattern in truncation_patterns:
        text = re.sub(pattern, '', text)
    
    # Validate remaining content
    alpha_count = sum(1 for c in text if c.isalpha())
    if alpha_count < 20:
        return ""
    
    # Check for nonsense (too many special characters)
    special_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / max(len(text), 1)
    if special_ratio > 0.3:
        return ""
    
    # Check for truncated/incomplete sentences
    if len(text) < MIN_CONTENT_LENGTH:
        return ""
    
    return text


def _calculate_recency_weight(text: str) -> float:
    """
    Calculate weight based on post recency (estimated from text if date not available)
    or just default to 1.0 if no date found (conservative).
    """
    if re.search(r'\d+\s+years?\s+ago', text):
        match = re.search(r'(\d+)\s+years?\s+ago', text)
        if match:
            years = int(match.group(1))
            if years >= 2:
                return 0.2  # Old content (>2 years)
            if years >= 1:
                return 0.5  # Somewhat old (1-2 years)
                
    return 1.0  # Default to recent/relevant


def _detect_transactional_intent(text: str) -> bool:
    """Check for transactional keywords in text."""
    text_lower = text.lower()
    for signal in TRANSACTIONAL_SIGNALS:
        if signal in text_lower:
            return True
            
    # Also check for product signals
    for signal in PRODUCT_SIGNALS:
        if signal in text_lower:
            return True
            
    return False


def _has_domain_relevance(content: str, domain_keywords: List[str]) -> bool:
    """
    Check if content explicitly mentions domain-specific keywords.
    """
    content_lower = content.lower()
    matches = sum(1 for kw in domain_keywords if kw.lower() in content_lower)
    return matches >= 1


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def _analyze_sentiment(text: str) -> Tuple[float, float]:
    """
    Analyze sentiment using TextBlob.
    Returns (polarity, subjectivity).
    """
    try:
        blob = TextBlob(text)
        return blob.sentiment.polarity, blob.sentiment.subjectivity
    except Exception:
        return 0.0, 0.5


def _classify_sentiment(score: float) -> str:
    """Classify sentiment score into category."""
    if score >= 0.15:
        return "positive"
    elif score <= -0.15:
        return "negative"
    else:
        return "neutral"


def _extract_concerns_and_praises(
    posts: List[Dict],
    domain_keywords: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Extract real user concerns and praises from posts.
    Only returns defaults if genuinely zero relevant content.
    """
    concerns = []
    praises = []
    
    # Patterns for extracting concerns
    concern_patterns = [
        r'(?:worried|concern|problem|issue|risk|challenge|difficult|annoying|frustrating)[\s:,]+([^.!?]{10,80})',
        r'(?:don\'t|doesn\'t|won\'t|can\'t|hate|dislike)[\s]+([^.!?]{10,80})',
        r'(?:safety|security|liability|insurance|trust)[\s]+(?:issue|concern|problem)s?',
        r'(?:scam|fraud|sketchy|unsafe|dangerous)',
    ]
    
    # Patterns for extracting praises
    praise_patterns = [
        r'(?:love|great|amazing|excellent|helpful|useful|convenient|easy|perfect)[\s:,]+([^.!?]{10,80})',
        r'(?:works?\s+(?:really\s+)?well|highly\s+recommend|game\s*changer)',
        r'(?:saved?\s+(?:me\s+)?(?:money|time|hassle))',
        r'(?:much\s+(?:better|easier|cheaper)\s+than)',
    ]
    
    for post in posts[:30]:
        content = post.get("content", "").lower()
        sentiment = post.get("sentiment_score", 0)
        
        # Extract concerns from negative sentiment posts
        if sentiment < 0:
            for pattern in concern_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, str) and len(match) > 10:
                        concern = match.strip().capitalize()
                        if concern not in concerns and len(concerns) < 8:
                            concerns.append(concern)
        
        # Extract praises from positive sentiment posts
        elif sentiment > 0:
            for pattern in praise_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, str) and len(match) > 10:
                        praise = match.strip().capitalize()
                        if praise not in praises and len(praises) < 8:
                            praises.append(praise)
    
    # Fallback: extract any mentions of domain keywords in context
    if not concerns and not praises:
        for post in posts[:20]:
            content = post.get("content", "")
            for kw in domain_keywords[:5]:
                pattern = rf'({kw}[^.!?]{{10,60}})'
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches[:1]:
                    if post.get("sentiment_score", 0) < 0:
                        if len(concerns) < 5:
                            concerns.append(match.strip().capitalize())
                    elif post.get("sentiment_score", 0) > 0:
                        if len(praises) < 5:
                            praises.append(match.strip().capitalize())
    
    # Only use defaults if truly no relevant content
    if not concerns and len(posts) > 0:
        concerns = ["Limited specific concerns found in analyzed posts"]
    elif not concerns:
        concerns = ["Insufficient data for concern analysis"]
    
    if not praises and len(posts) > 0:
        praises = ["Limited specific praises found in analyzed posts"]
    elif not praises:
        praises = ["Insufficient data for praise analysis"]
    
    return concerns[:5], praises[:5]


def _calculate_sentiment_metrics(
    posts: List[Dict]
) -> Tuple[float, float, float, Tuple[float, float]]:
    """
    Calculate weighted sentiment with variance and uncertainty.
    Returns (weighted_sentiment, variance, uncertainty, confidence_interval).
    """
    if not posts:
        return 0.0, 0.0, 1.0, (-1.0, 1.0)
    
    sentiment_scores = [p["sentiment_score"] for p in posts]
    relevance_scores = [p["relevance_score"] for p in posts]
    
    # Weighted sentiment
    total_weight = sum(relevance_scores)
    if total_weight == 0:
        weighted_sentiment = 0.0
    else:
        weighted_sentiment = sum(
            s * r for s, r in zip(sentiment_scores, relevance_scores)
        ) / total_weight
    
    # Variance
    if len(sentiment_scores) > 1:
        variance = statistics.variance(sentiment_scores)
    else:
        variance = 0.5
    
    # Uncertainty based on sample size and variance
    sample_factor = min(len(posts) / MIN_SAMPLE_SIZE, 1.0)
    variance_factor = 1 - min(variance, 0.5)
    uncertainty = 1 - (sample_factor * variance_factor * 0.7)
    uncertainty = max(0.1, min(0.9, uncertainty))
    
    # Confidence interval
    std_dev = math.sqrt(variance) if variance > 0 else 0.2
    margin = 1.96 * std_dev / math.sqrt(max(len(posts), 1))
    lower = max(-1.0, weighted_sentiment - margin)
    upper = min(1.0, weighted_sentiment + margin)
    
    return weighted_sentiment, variance, uncertainty, (lower, upper)


async def _search_tavily_async(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
    timeout: float = Timeouts.TAVILY
) -> List[Dict]:
    """
    Search Tavily API asynchronously with timeout and retry.
    """
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "include_domains": ["reddit.com"],
        "max_results": 50,
        "include_raw_content": True
    }
    
    for attempt in range(RetryConfig.MAX_RETRIES + 1):
        try:
            response = await client.post(
                url,
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            
            # Non-retryable errors
            if response.status_code in RetryConfig.NON_RETRYABLE_CODES:
                log_timing("reddit", f"Tavily non-retryable error: {response.status_code}")
                return []
            
            # Retryable errors
            if attempt < RetryConfig.MAX_RETRIES:
                backoff = min(
                    RetryConfig.INITIAL_BACKOFF * (2 ** attempt),
                    RetryConfig.MAX_BACKOFF
                )
                await asyncio.sleep(backoff)
                
        except httpx.TimeoutException:
            log_timing("reddit", f"Tavily timeout on attempt {attempt + 1}")
            if attempt < RetryConfig.MAX_RETRIES:
                await asyncio.sleep(RetryConfig.INITIAL_BACKOFF)
        except Exception as e:
            log_timing("reddit", f"Tavily error: {str(e)[:50]}")
            return []
    
    return []


async def _get_embeddings_batch(
    client: AsyncOpenAI,
    texts: List[str],
    timeout: float = Timeouts.OPENAI_EMBEDDING
) -> List[List[float]]:
    """
    Get embeddings for multiple texts in a single batch call.
    Returns list of embedding vectors (or empty list for failed texts).
    """
    if not texts:
        return []
    
    # Truncate texts to fit token limits
    truncated = [t[:8000] for t in texts]
    
    try:
        response = await asyncio.wait_for(
            client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=truncated
            ),
            timeout=timeout
        )
        return [item.embedding for item in response.data]
    except asyncio.TimeoutError:
        log_timing("reddit", "Embedding batch timeout")
        return [[] for _ in texts]
    except Exception as e:
        log_timing("reddit", f"Embedding batch error: {str(e)[:50]}")
        return [[] for _ in texts]


async def search_reddit(state: ValidationState) -> Dict[str, Any]:
    """
    Search Reddit for discussions about the startup idea.
    
    ASYNC OPTIMIZED:
    - Concurrent query execution
    - Batched embeddings
    - 8s timeout per request
    - Max 2 retries
    """
    timer = StepTimer("reddit")
    
    idea_input = state.get("idea_input", "")
    processing_errors = list(state.get("processing_errors", []))
    
    if not idea_input:
        return {
            "reddit_sentiment": _insufficient_data_response(["no_idea_provided"]),
            "processing_errors": processing_errors + ["Reddit: No idea provided"]
        }
    
    try:
        tavily_key, openai_key = _get_api_keys()
    except ValueError as e:
        return {
            "reddit_sentiment": _insufficient_data_response([str(e)]),
            "processing_errors": processing_errors + [f"Reddit: {str(e)}"]
        }
    
    # Get global embedding and intent from state
    idea_embedding = state.get("idea_embedding", [])
    intent_keywords = state.get("intent_keywords", [])
    
    if not idea_embedding:
        return {
            "reddit_sentiment": _insufficient_data_response(["missing_idea_embedding"]),
            "processing_errors": processing_errors + ["Reddit: Missing idea embedding"]
        }
        
    # Extract domain context using global intent keywords
    domain_keywords = _extract_domain_context(idea_input, intent_keywords)
    
    # Generate search queries
    queries = _generate_reddit_queries(idea_input, domain_keywords)
    
    # Initialize clients
    openai_client = AsyncOpenAI(api_key=openai_key)
    
    # Search Tavily CONCURRENTLY for all queries
    async with timer.async_step("tavily_search"):
        async with httpx.AsyncClient() as http_client:
            search_tasks = [
                _search_tavily_async(http_client, tavily_key, query)
                for query in queries
            ]
            results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)
    
    # Flatten results
    all_results = []
    for result_list in results_lists:
        if isinstance(result_list, list):
            all_results.extend(result_list)
    
    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    if not unique_results:
        timer.summary()
        return {
            "reddit_sentiment": _insufficient_data_response(["no_reddit_results"]),
            "processing_errors": processing_errors + ["Reddit: No results found"]
        }
    
    # Process results and collect texts for batch embedding
    async with timer.async_step("processing"):
        candidate_posts = []
        discarded_noise_count = 0
        excluded_subreddit_count = 0
        subreddit_counts: Dict[str, int] = {}
        
        for result in unique_results:
            # Extract subreddit
            url = result.get("url", "")
            subreddit = ""
            subreddit_match = re.search(r'reddit\.com/r/(\w+)', url)
            if subreddit_match:
                subreddit = subreddit_match.group(1)
            
            # Check for excluded subreddits
            if _is_excluded_subreddit(subreddit):
                excluded_subreddit_count += 1
                continue
            
            # Extract and clean content
            raw_content = result.get("raw_content") or result.get("content", "")
            title = result.get("title", "")
            
            cleaned_content = _clean_text(raw_content)
            cleaned_title = _clean_text(title)
            
            full_content = f"{cleaned_title} {cleaned_content}".strip()
            
            # Validate content quality
            if len(full_content) < MIN_CONTENT_LENGTH:
                discarded_noise_count += 1
                continue
            
            # Check domain relevance (quick keyword check)
            has_keyword_match = _has_domain_relevance(full_content, domain_keywords)
            
            candidate_posts.append({
                "title": cleaned_title[:200],
                "content": cleaned_content[:500],
                "full_content": full_content[:2000],
                "subreddit": subreddit,
                "url": url,
                "has_keyword_match": has_keyword_match
            })
            
            # Track subreddit
            if subreddit:
                subreddit_counts[subreddit] = subreddit_counts.get(subreddit, 0) + 1
    
    if not candidate_posts:
        timer.summary()
        return {
            "reddit_sentiment": _insufficient_data_response(["all_posts_filtered"]),
            "processing_errors": processing_errors + ["Reddit: All posts filtered"]
        }
    
    # BATCH embedding call for all candidate posts
    async with timer.async_step("batch_embeddings"):
        texts_to_embed = [p["full_content"] for p in candidate_posts]
        embeddings = await _get_embeddings_batch(openai_client, texts_to_embed)
    
    # Calculate relevance and filter
    async with timer.async_step("relevance_scoring"):
        processed_posts = []
        low_relevance_count = 0
        
        for i, post in enumerate(candidate_posts):
            # Calculate base relevance
            if embeddings[i]:
                base_relevance = _cosine_similarity(idea_embedding, embeddings[i])
            else:
                base_relevance = 0.3
            
            # EPISTEMIC RIGOUR: Apply recency weighting
            recency_weight = _calculate_recency_weight(post["full_content"])
            
            # EPISTEMIC RIGOUR: Check for transactional intent
            is_transactional = _detect_transactional_intent(post["full_content"])
            
            # Calculate adjusted relevance
            # 1. Penalize old content
            relevance_score = base_relevance * recency_weight
            
            # 2. Boost for keyword match OR transactional signal
            if post["has_keyword_match"] or is_transactional:
                relevance_score = min(1.0, relevance_score + 0.15)
            
            # Filter by relevance
            if relevance_score < RELEVANCE_THRESHOLD and not (post["has_keyword_match"] or is_transactional):
                low_relevance_count += 1
                continue
            
            # Analyze sentiment
            polarity, subjectivity = _analyze_sentiment(post["full_content"])
            
            processed_posts.append({
                "title": post["title"],
                "content": post["content"],
                "subreddit": post["subreddit"],
                "relevance_score": round(relevance_score, 3),
                "sentiment_score": round(polarity, 3),
                "subjectivity": round(subjectivity, 3),
                "url": post["url"]
            })
    
    # Check if we have enough data
    total_discarded = discarded_noise_count + excluded_subreddit_count + low_relevance_count
    
    if len(processed_posts) < 5:
        timer.summary()
        return {
            "reddit_sentiment": _insufficient_data_response([
                "low_sample_size",
                f"only_{len(processed_posts)}_relevant_posts",
                f"discarded_{total_discarded}_posts"
            ]),
            "processing_errors": processing_errors + ["Reddit: Insufficient relevant posts"]
        }
    
    # Calculate sentiment metrics
    weighted_sentiment, variance, uncertainty, conf_interval = _calculate_sentiment_metrics(processed_posts)
    
    # Determine overall sentiment
    overall_sentiment = _classify_sentiment(weighted_sentiment)
    
    # Check for mixed signals
    pos_count = sum(1 for p in processed_posts if p["sentiment_score"] > 0.1)
    neg_count = sum(1 for p in processed_posts if p["sentiment_score"] < -0.1)
    if pos_count >= 3 and neg_count >= 3:
        overall_sentiment = "mixed"
    
    # Get top subreddits
    top_subreddits = sorted(subreddit_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_subreddits = [f"r/{s[0]}" for s in top_subreddits if s[0]]
    if not top_subreddits:
        top_subreddits = ["r/various"]
    
    # Extract concerns and praises
    key_concerns, key_praises = _extract_concerns_and_praises(processed_posts, domain_keywords)
    
    # Build sample posts
    sample_posts: List[SamplePost] = []
    for post in sorted(processed_posts, key=lambda x: x["relevance_score"], reverse=True)[:5]:
        sample_posts.append({
            "title": post["title"][:100],
            "score": int(post["relevance_score"] * 100),
            "sentiment": _classify_sentiment(post["sentiment_score"]),
            "subreddit": post["subreddit"] or "unknown"
        })
    
    # Calculate confidence
    relevance_scores = [p["relevance_score"] for p in processed_posts]
    relevance_mean = statistics.mean(relevance_scores) if relevance_scores else 0
    
    sample_factor = min(len(processed_posts) / MIN_SAMPLE_SIZE, 1.0)
    noise_penalty = min(total_discarded / max(len(processed_posts), 1), 0.5)
    confidence = sample_factor * relevance_mean * (1 - noise_penalty) * (1 - uncertainty * 0.5)
    confidence = max(0.1, min(0.95, confidence))
    
    # Build warnings
    warnings = []
    if len(processed_posts) < MIN_SAMPLE_SIZE:
        warnings.append("sample_size_below_target")
    if total_discarded > len(processed_posts):
        warnings.append("high_noise_ratio")
    if variance > 0.3:
        warnings.append("high_sentiment_variance")
    if excluded_subreddit_count > 5:
        warnings.append("many_off_domain_results")
    if relevance_mean < 0.6:
        warnings.append("low_average_relevance")
    
    quality: QualityMetrics = {
        "data_volume": len(processed_posts),
        "relevance_mean": round(relevance_mean, 3),
        "confidence": round(confidence, 3),
        "warnings": warnings
    }
    
    reddit_sentiment: RedditSentiment = {
        "overall_sentiment": overall_sentiment,
        "sentiment_score": round(weighted_sentiment, 2),
        "total_posts_analyzed": len(processed_posts),
        "top_subreddits": top_subreddits,
        "key_concerns": key_concerns,
        "key_praises": key_praises,
        "sample_posts": sample_posts,
        "quality": quality
    }
    
    timer.summary()
    return {"reddit_sentiment": reddit_sentiment}


def _insufficient_data_response(warnings: List[str]) -> RedditSentiment:
    """Generate a standardized insufficient data response."""
    return {
        "overall_sentiment": "insufficient_data",
        "sentiment_score": 0.0,
        "total_posts_analyzed": 0,
        "top_subreddits": [],
        "key_concerns": ["Insufficient data for analysis"],
        "key_praises": ["Insufficient data for analysis"],
        "sample_posts": [],
        "quality": {
            "data_volume": 0,
            "relevance_mean": 0.0,
            "confidence": 0.0,
            "warnings": warnings
        }
    }
