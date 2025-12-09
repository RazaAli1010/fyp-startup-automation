from typing import TypedDict, Optional


class RedditSentiment(TypedDict):
    """Structure for Reddit sentiment analysis results."""
    overall_sentiment: str  # "positive", "negative", "neutral", "mixed"
    sentiment_score: float  # -1.0 to 1.0
    total_posts_analyzed: int
    top_subreddits: list[str]
    key_concerns: list[str]
    key_praises: list[str]
    sample_posts: list[dict]  # [{title, score, sentiment, subreddit}]


class TrendsData(TypedDict):
    """Structure for Google Trends analysis results."""
    trend_direction: str  # "rising", "falling", "stable", "no_data"
    interest_score: int  # 0-100 (Google's relative interest)
    related_queries: list[str]
    related_topics: list[str]
    geographic_interest: dict  # {region: score}
    temporal_trend: str  # "seasonal", "growing", "declining", "stable"


class CompetitorAnalysis(TypedDict):
    """Structure for competitor analysis results."""
    competitors_found: int
    direct_competitors: list[dict]  # [{name, url, description, funding}]
    indirect_competitors: list[dict]
    market_saturation: str  # "low", "medium", "high", "oversaturated"
    differentiation_opportunities: list[str]
    total_funding_in_space: str  # e.g., "$500M+"


class FinalVerdict(TypedDict):
    """Structure for the final synthesized verdict."""
    overall_score: int  # 0-100
    recommendation: str  # "strong_go", "go", "caution", "pivot", "no_go"
    confidence: float  # 0.0-1.0
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    action_items: list[str]
    risk_factors: list[str]


class ValidationState(TypedDict):
    idea_input: str
    
    # Intermediate Results (populated by parallel nodes)
    reddit_sentiment: Optional[RedditSentiment]
    trends_data: Optional[TrendsData]
    competitor_analysis: Optional[CompetitorAnalysis]
    
    # Final Output (populated by judge node)
    final_verdict: Optional[FinalVerdict]
    
    # Metadata
    processing_errors: list[str]  # Track any errors during processing

