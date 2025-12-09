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



