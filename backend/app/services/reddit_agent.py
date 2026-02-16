"""Reddit Pain Mining Agent.

Searches relevant subreddits via the official Reddit API (PRAW), detects
complaint posts using deterministic pain-word matching, and returns
structured numeric pain signals.

Rules
-----
- NO LLM calls
- NO text summarisation
- NO scoring / judging
- Pure signal extraction: same QueryBundle → same RedditPainSignals
  (modulo Reddit's live data)
"""

from __future__ import annotations

import logging
import os
import re
from collections import Counter
from typing import List

import praw
from praw.exceptions import PRAWException

from ..schemas.query_schema import QueryBundle
from ..schemas.reddit_schema import RedditPainSignals

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pain-word lexicon.  A post is a *complaint* when its title OR selftext
# contains at least one of these AND matches at least one query keyword.
# ---------------------------------------------------------------------------
_PAIN_WORDS: frozenset[str] = frozenset(
    {
        "problem",
        "issue",
        "struggle",
        "pain",
        "frustrated",
        "hate",
        "slow",
        "expensive",
    }
)

# ---------------------------------------------------------------------------
# Stop-words excluded when extracting top pain keywords from complaint text.
# ---------------------------------------------------------------------------
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "be", "been",
        "this", "that", "it", "its", "we", "our", "they", "their", "my", "me",
        "i", "you", "your", "he", "she", "him", "her", "us", "them",
        "do", "does", "did", "has", "have", "had", "not", "no", "so",
        "very", "just", "also", "about", "into", "over", "such", "than",
        "then", "each", "every", "all", "both", "few", "more", "most",
        "some", "any", "other", "what", "which", "who", "how", "where",
        "when", "will", "can", "would", "could", "should", "if", "up",
        "out", "get", "got", "like", "know", "think", "want", "need",
        "use", "using", "used", "one", "even", "still", "really", "much",
        "way", "going", "been", "being", "there", "here", "don", "doesn",
        "didn", "won", "isn", "aren", "wasn", "weren", "hasn", "haven",
        "wouldn", "couldn", "shouldn", "ain", "ll", "ve", "re",
    }
)

# ---------------------------------------------------------------------------
# Industry → subreddit mapping.  Fallbacks are always appended.
# ---------------------------------------------------------------------------
INDUSTRY_SUBREDDIT_MAP: dict[str, list[str]] = {
    "saas": ["SaaS", "startups", "Entrepreneur"],
    "fintech": ["fintech", "personalfinance", "Entrepreneur"],
    "ai": ["ArtificialIntelligence", "MachineLearning", "startups"],
    "ecommerce": ["ecommerce", "Entrepreneur"],
    "healthtech": ["healthIT", "digitalhealth", "startups"],
    "edtech": ["edtech", "education", "startups"],
    "marketplace": ["startups", "Entrepreneur", "smallbusiness"],
    "crypto": ["CryptoCurrency", "defi", "startups"],
    "cybersecurity": ["cybersecurity", "netsec", "startups"],
    "hr": ["humanresources", "recruiting", "startups"],
    "logistics": ["logistics", "supplychain", "startups"],
    "proptech": ["realestateinvesting", "proptech", "startups"],
    "legaltech": ["legaltech", "law", "startups"],
    "insurtech": ["Insurance", "startups", "Entrepreneur"],
}

_FALLBACK_SUBREDDITS: list[str] = ["Entrepreneur", "startups"]

# Maximum posts fetched per subreddit per query (keeps API usage bounded).
_POSTS_PER_QUERY = 25


# ===================================================================== #
#  Internal helpers                                                       #
# ===================================================================== #

def _get_reddit_client() -> praw.Reddit:
    """Build a read-only PRAW Reddit instance from environment variables.

    Required env vars:
        REDDIT_CLIENT_ID
        REDDIT_CLIENT_SECRET
        REDDIT_USER_AGENT   (optional — defaults to a sensible value)
    """
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv(
        "REDDIT_USER_AGENT",
        "StartBot/1.0 (pain-mining agent)",
    )

    if not client_id or not client_secret:
        raise EnvironmentError(
            "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables "
            "must be set to use the Reddit Pain Mining Agent."
        )

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def _resolve_subreddits(industry_tags: List[str]) -> List[str]:
    """Return a deduplicated list of subreddits for the given industry tags.

    Always includes the fallback subreddits.
    """
    subs: list[str] = []
    for tag in industry_tags:
        tag_lower = tag.lower().strip()
        if tag_lower in INDUSTRY_SUBREDDIT_MAP:
            subs.extend(INDUSTRY_SUBREDDIT_MAP[tag_lower])

    # Always append fallbacks
    subs.extend(_FALLBACK_SUBREDDITS)

    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for s in subs:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def _tokenise(text: str) -> List[str]:
    """Split text into lowercase alpha tokens ≥ 3 chars, minus stop-words."""
    return [
        t
        for t in re.split(r"[^a-zA-Z]+", text.lower())
        if len(t) >= 3 and t not in _STOP_WORDS
    ]


def _contains_pain_word(text: str) -> bool:
    """Return True if *text* contains at least one pain word."""
    text_lower = text.lower()
    return any(pw in text_lower for pw in _PAIN_WORDS)


def _matches_query_keyword(text: str, query_keywords: List[str]) -> bool:
    """Return True if *text* contains at least one token from the queries."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in query_keywords)


def _extract_query_keywords(reddit_queries: List[str]) -> List[str]:
    """Flatten reddit_queries into a unique list of lowercase keyword tokens.

    These are used for the second half of the complaint-detection rule:
    a post must match at least one of these keywords.
    """
    tokens: list[str] = []
    for query in reddit_queries:
        tokens.extend(_tokenise(query))

    # Deduplicate
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


# ===================================================================== #
#  Public API                                                             #
# ===================================================================== #

def fetch_reddit_pain_signals(query_bundle: QueryBundle) -> RedditPainSignals:
    """Search Reddit and return quantifiable pain signals.

    Parameters
    ----------
    query_bundle:
        A ``QueryBundle`` whose ``reddit_queries`` and ``industry_tags``
        fields drive subreddit selection and complaint detection.

    Returns
    -------
    RedditPainSignals
        Structured numeric pain metrics ready for downstream consumption.
    """
    # ------------------------------------------------------------------ #
    #  1. Resolve subreddits from industry tags                           #
    # ------------------------------------------------------------------ #
    subreddits = _resolve_subreddits(query_bundle.industry_tags)
    query_keywords = _extract_query_keywords(query_bundle.reddit_queries)

    if not query_keywords:
        logger.warning("No query keywords derived from reddit_queries — returning empty signals.")
        return _empty_signals()

    # ------------------------------------------------------------------ #
    #  2. Fetch posts via PRAW                                            #
    # ------------------------------------------------------------------ #
    try:
        reddit = _get_reddit_client()
    except EnvironmentError as exc:
        logger.error("Reddit client init failed: %s", exc)
        return _empty_signals()

    all_posts: list[dict] = []

    for sub_name in subreddits:
        for query in query_bundle.reddit_queries:
            try:
                subreddit = reddit.subreddit(sub_name)
                results = subreddit.search(query, sort="relevance", limit=_POSTS_PER_QUERY)
                for submission in results:
                    all_posts.append(
                        {
                            "title": submission.title or "",
                            "selftext": submission.selftext or "",
                            "score": submission.score,
                            "num_comments": submission.num_comments,
                            "id": submission.id,
                        }
                    )
            except PRAWException as exc:
                logger.warning("PRAW error on r/%s query=%r: %s", sub_name, query, exc)
            except Exception as exc:
                logger.warning("Unexpected error on r/%s query=%r: %s", sub_name, query, exc)

    # Deduplicate by submission id
    seen_ids: set[str] = set()
    unique_posts: list[dict] = []
    for post in all_posts:
        if post["id"] not in seen_ids:
            seen_ids.add(post["id"])
            unique_posts.append(post)

    total_posts_analyzed = len(unique_posts)

    if total_posts_analyzed == 0:
        logger.info("No Reddit posts found for the given queries.")
        return _empty_signals()

    # ------------------------------------------------------------------ #
    #  3. Classify complaints                                             #
    # ------------------------------------------------------------------ #
    complaint_posts: list[dict] = []
    complaint_token_counter: Counter = Counter()

    for post in unique_posts:
        combined_text = f"{post['title']} {post['selftext']}"

        is_pain = _contains_pain_word(combined_text)
        is_relevant = _matches_query_keyword(combined_text, query_keywords)

        if is_pain and is_relevant:
            complaint_posts.append(post)
            complaint_token_counter.update(_tokenise(combined_text))

    complaint_post_count = len(complaint_posts)

    # ------------------------------------------------------------------ #
    #  4. Compute metrics                                                 #
    # ------------------------------------------------------------------ #
    if complaint_post_count > 0:
        avg_upvotes = sum(p["score"] for p in complaint_posts) / complaint_post_count
        avg_comments = sum(p["num_comments"] for p in complaint_posts) / complaint_post_count
    else:
        avg_upvotes = 0.0
        avg_comments = 0.0

    # Pain intensity formula (clamped to [0, 1])
    if total_posts_analyzed > 0 and complaint_post_count > 0:
        pain_intensity = min(
            (complaint_post_count / total_posts_analyzed) * (avg_comments / 10),
            1.0,
        )
    else:
        pain_intensity = 0.0

    # Top pain keywords — most frequent non-stopwords from complaint text
    # Exclude the pain words themselves so the list surfaces domain terms.
    top_pain_keywords = [
        word
        for word, _ in complaint_token_counter.most_common(10)
        if word not in _PAIN_WORDS
    ][:5]

    return RedditPainSignals(
        total_posts_analyzed=total_posts_analyzed,
        complaint_post_count=complaint_post_count,
        avg_upvotes=round(avg_upvotes, 2),
        avg_comments=round(avg_comments, 2),
        pain_intensity_score=round(pain_intensity, 4),
        top_pain_keywords=top_pain_keywords,
    )


def _empty_signals() -> RedditPainSignals:
    """Return a zero-value RedditPainSignals for graceful degradation."""
    return RedditPainSignals(
        total_posts_analyzed=0,
        complaint_post_count=0,
        avg_upvotes=0.0,
        avg_comments=0.0,
        pain_intensity_score=0.0,
        top_pain_keywords=[],
    )
