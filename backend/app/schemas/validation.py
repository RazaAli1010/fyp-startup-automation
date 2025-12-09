from typing import Optional
from pydantic import BaseModel, Field


class ValidationRequest(BaseModel):
    """Request body for the /validate endpoint."""
    
    idea: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The startup idea to validate. Be descriptive for better results.",
        alias="idea_input",  # Accept both "idea" and "idea_input" from JSON
        examples=[
            "An AI-powered tool that helps small business owners automate their social media content creation and scheduling",
            "A marketplace connecting local farmers directly with restaurants, eliminating middlemen and ensuring fresh produce delivery within 24 hours"
        ]
    )
    
    class Config:
        # Allow field to be populated by either "idea" or "idea_input"
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "idea": "An AI-powered tool that helps small business owners automate their social media content creation and scheduling"
            }
        }

class SamplePost(BaseModel):
    """A sample Reddit post from the analysis."""
    title: str
    score: int
    sentiment: str
    subreddit: str

class RedditSentimentResponse(BaseModel):
    """Reddit sentiment analysis results."""
    overall_sentiment: str = Field(
        ..., 
        description="Overall sentiment: positive, negative, neutral, or mixed"
    )
    sentiment_score: float = Field(
        ..., 
        ge=-1.0, 
        le=1.0,
        description="Sentiment score from -1 (negative) to 1 (positive)"
    )
    total_posts_analyzed: int = Field(..., ge=0)
    top_subreddits: list[str]
    key_concerns: list[str]
    key_praises: list[str]
    sample_posts: list[SamplePost]

class TrendsDataResponse(BaseModel):
    """Google Trends analysis results."""
    trend_direction: str = Field(
        ...,
        description="Trend direction: rising, falling, stable, or no_data"
    )
    interest_score: int = Field(
        ..., 
        ge=0, 
        le=100,
        description="Google's relative interest score (0-100)"
    )
    related_queries: list[str]
    related_topics: list[str]
    geographic_interest: dict[str, int] = Field(
        ...,
        description="Interest by region with scores"
    )
    temporal_trend: str = Field(
        ...,
        description="Long-term trend: growing, declining, stable, or seasonal"
    )

class CompetitorInfo(BaseModel):
    """Information about a single competitor."""
    name: str
    url: str
    description: str
    funding: str


class CompetitorAnalysisResponse(BaseModel):
    """Competitor analysis results."""
    competitors_found: int = Field(..., ge=0)
    direct_competitors: list[CompetitorInfo]
    indirect_competitors: list[CompetitorInfo]
    market_saturation: str = Field(
        ...,
        description="Market saturation level: low, medium, high, or oversaturated"
    )
    differentiation_opportunities: list[str]
    total_funding_in_space: str

class FinalVerdictResponse(BaseModel):
    """Final synthesized verdict with scoring."""
    overall_score: int = Field(
        ..., 
        ge=0, 
        le=100,
        description="Overall validation score (0-100)"
    )
    recommendation: str = Field(
        ...,
        description="Recommendation: strong_go, go, caution, pivot, or no_go"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Confidence in the verdict (0-1)"
    )
    summary: str = Field(..., description="Human-readable summary")
    strengths: list[str]
    weaknesses: list[str]
    action_items: list[str]
    risk_factors: list[str]

class ValidationResponse(BaseModel):
    """Complete response from the /validate endpoint."""
    
    success: bool = Field(
        default=True,
        description="Whether the validation completed successfully"
    )
    idea_input: str = Field(
        ...,
        description="The original idea that was validated"
    )
    reddit_sentiment: Optional[RedditSentimentResponse] = Field(
        default=None,
        description="Reddit sentiment analysis results"
    )
    trends_data: Optional[TrendsDataResponse] = Field(
        default=None,
        description="Google Trends analysis results"
    )
    competitor_analysis: Optional[CompetitorAnalysisResponse] = Field(
        default=None,
        description="Competitor analysis results"
    )
    final_verdict: Optional[FinalVerdictResponse] = Field(
        default=None,
        description="Final synthesized verdict"
    )
    processing_errors: list[str] = Field(
        default_factory=list,
        description="Any errors encountered during processing"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "idea_input": "An AI-powered social media automation tool",
                "reddit_sentiment": {
                    "overall_sentiment": "positive",
                    "sentiment_score": 0.65,
                    "total_posts_analyzed": 47,
                    "top_subreddits": ["r/startups", "r/entrepreneur"],
                    "key_concerns": ["Market saturation"],
                    "key_praises": ["Solves real pain point"],
                    "sample_posts": []
                },
                "trends_data": {
                    "trend_direction": "rising",
                    "interest_score": 72,
                    "related_queries": ["social media tools"],
                    "related_topics": ["AI", "Automation"],
                    "geographic_interest": {"United States": 85},
                    "temporal_trend": "growing"
                },
                "competitor_analysis": {
                    "competitors_found": 5,
                    "direct_competitors": [],
                    "indirect_competitors": [],
                    "market_saturation": "medium",
                    "differentiation_opportunities": ["Focus on SMB"],
                    "total_funding_in_space": "$200M+"
                },
                "final_verdict": {
                    "overall_score": 72,
                    "recommendation": "go",
                    "confidence": 0.78,
                    "summary": "Promising opportunity with manageable competition",
                    "strengths": ["Growing market"],
                    "weaknesses": ["Established players"],
                    "action_items": ["Conduct interviews"],
                    "risk_factors": ["CAC may be high"]
                },
                "processing_errors": []
            }
        }



