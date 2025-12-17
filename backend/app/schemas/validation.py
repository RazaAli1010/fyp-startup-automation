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
    market_structure: dict = Field(
        ...,
        description="Market structure classification with type, confidence, and evidence"
    )
    differentiation_opportunities: list[str]
    total_funding_in_space: str


class RecommendationConditionResponse(BaseModel):
    """
    A single falsifiable condition for the recommendation.
    
    Each condition MUST be falsifiable, testable, and tied to a specific risk.
    """
    condition: str = Field(
        ..., 
        description="Falsifiable statement (e.g., 'If users prepay at ≥$5/hour')"
    )
    test_method: str = Field(
        ..., 
        description="How to verify (e.g., 'Run 2-week pilot in 3 cities')"
    )
    linked_risk: str = Field(
        ..., 
        description="Risk this addresses (e.g., 'demand_validation')"
    )


class ConditionalRecommendationResponse(BaseModel):
    """
    Structured recommendation with explicit conditions.
    
    Decision types:
    - conditional_go: Core signals positive, 1-3 assumptions to validate
    - experiment: Mixed signals, small tests required before commitment
    - wait: Market/infrastructure not ready, timing risk dominates
    - avoid: Structural barriers high, key assumptions unlikely/untestable
    """
    decision: str = Field(
        ..., 
        description="Decision: conditional_go, experiment, wait, or avoid"
    )
    conditions: list[RecommendationConditionResponse] = Field(
        ..., 
        min_length=2,
        description="Minimum 2 falsifiable conditions required"
    )
    rationale: str = Field(
        ..., 
        description="Why this decision AND why it is conditional (not unconditional)"
    )


class UnknownResponse(BaseModel):
    """
    A claim or assumption that lacks direct evidence.
    
    REQUIRED: Every final output MUST include unknowns. Empty lists are NOT allowed.
    """
    claim: str = Field(
        ...,
        description="The uncertain claim (e.g., 'Users will pay for this service')"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in claim (0.0-1.0), must be justified"
    )
    reason: str = Field(
        ...,
        description="Why this claim is uncertain or unsupported"
    )
    source: str = Field(
        ...,
        description="Analysis section this relates to (reddit, trends, competitors, economics)"
    )
    evidence_gap: str = Field(
        ...,
        description="What evidence would resolve this unknown"
    )


class KillCriterionResponse(BaseModel):
    """
    Explicit kill criterion that can terminate the idea.
    
    REQUIREMENT: Every criterion must be measurable and explicitly state when to STOP.
    """
    criterion: str = Field(
        ...,
        description="Kill criterion in 'If X fails → stop' format"
    )
    category: str = Field(
        ...,
        description="Category: user_side | supply_side | willingness_to_pay | unit_economics"
    )
    linked_unknown: str = Field(
        ...,
        description="Which unknown/assumption this criterion tests"
    )
    test_cost: str = Field(
        ...,
        description="Cost estimate: cheap (<$500) | moderate ($500-$5000) | expensive (>$5000)"
    )
    test_duration: str = Field(
        ...,
        description="Time estimate: fast (<1 week) | moderate (1-4 weeks) | slow (>4 weeks)"
    )


class FinalVerdictResponse(BaseModel):
    """
    Final synthesized verdict with scoring.
    
    BREAKING CHANGES:
    - recommendation is ConditionalRecommendationResponse (not string)
    - action_items replaced by kill_criteria
    
    MANDATORY: unknowns and kill_criteria must be populated.
    """
    overall_score: int = Field(
        ..., 
        ge=0, 
        le=100,
        description="Overall validation score (0-100)"
    )
    recommendation: ConditionalRecommendationResponse = Field(
        ...,
        description="Conditional recommendation with decision, conditions, and rationale"
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
    risk_factors: list[str]
    unknowns: list[UnknownResponse] = Field(
        ...,
        min_length=1,
        description="MANDATORY list of uncertain claims - never empty"
    )
    kill_criteria: list[KillCriterionResponse] = Field(
        ...,
        min_length=2,
        description="MANDATORY list of explicit stop conditions - replaces action_items"
    )

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
                    "market_structure": {
                        "type": "fragmented",
                        "confidence": 0.7,
                        "evidence": ["Multiple small players, no dominant leader"]
                    },
                    "differentiation_opportunities": ["Focus on SMB"],
                    "total_funding_in_space": "$200M+"
                },
                "final_verdict": {
                    "overall_score": 72,
                    "recommendation": {
                        "decision": "conditional_go",
                        "conditions": [
                            {
                                "condition": "If SMBs demonstrate willingness to pay $49+/month within 30-day trial",
                                "test_method": "Run 30-day free trial with 50 SMBs, measure conversion to paid",
                                "linked_risk": "demand_validation"
                            },
                            {
                                "condition": "If content generation quality rated ≥4/5 by 80% of beta users",
                                "test_method": "Survey beta users after 2 weeks of usage",
                                "linked_risk": "product_quality"
                            }
                        ],
                        "rationale": "Core signals positive (rising demand, positive sentiment) but unproven monetization in SMB segment requires validation before scaling"
                    },
                    "confidence": 0.78,
                    "summary": "Promising opportunity with manageable competition",
                    "strengths": ["Growing market"],
                    "weaknesses": ["Established players"],
                    "risk_factors": ["CAC may be high"],
                    "unknowns": [
                        {
                            "claim": "SMBs will pay for this solution",
                            "confidence": 0.35,
                            "reason": "No pricing experiments conducted",
                            "source": "business_model",
                            "evidence_gap": "Run pricing experiment with 50 SMBs"
                        }
                    ],
                    "kill_criteria": [
                        {
                            "criterion": "If <20% of trial SMBs convert to paid → stop",
                            "category": "willingness_to_pay",
                            "linked_unknown": "SMBs will pay for this solution",
                            "test_cost": "moderate",
                            "test_duration": "moderate"
                        },
                        {
                            "criterion": "If content quality rated <4/5 by 80% of users → stop",
                            "category": "user_side",
                            "linked_unknown": "Content quality meets expectations",
                            "test_cost": "cheap",
                            "test_duration": "fast"
                        }
                    ]
                },
                "processing_errors": []
            }
        }



