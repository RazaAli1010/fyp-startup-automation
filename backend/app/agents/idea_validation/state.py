"""
Validation Pipeline State Definition

This module defines the shared state schema for the LangGraph validation pipeline.
All nodes read from and write to this state structure.

NOTE: Field names must match the existing API contract in routers/validation.py
"""

from typing import TypedDict, Optional, List, Dict, Any, Annotated
import operator


class QualityMetrics(TypedDict, total=False):
    """Quality metrics included in every node output."""
    data_volume: int
    relevance_mean: float
    confidence: float
    warnings: List[str]


# ============================================================================
# Reddit Node Types
# ============================================================================

class SamplePost(TypedDict, total=False):
    """A sample Reddit post for the API response."""
    title: str
    score: int
    sentiment: str
    subreddit: str


class RedditSentiment(TypedDict, total=False):
    """Output from the Reddit sentiment analysis node - matches API schema."""
    overall_sentiment: str  # positive, negative, neutral, mixed
    sentiment_score: float  # -1 to 1
    total_posts_analyzed: int
    top_subreddits: List[str]
    key_concerns: List[str]
    key_praises: List[str]
    sample_posts: List[SamplePost]
    # Internal quality metrics
    quality: QualityMetrics


# ============================================================================
# Trends Node Types
# ============================================================================

class TrendsData(TypedDict, total=False):
    """Output from the Google Trends analysis node - matches API schema."""
    trend_direction: str  # rising, falling, stable, no_data
    interest_score: int  # 0-100
    related_queries: List[str]
    related_topics: List[str]
    geographic_interest: Dict[str, int]  # region -> score
    temporal_trend: str  # growing, declining, stable, seasonal
    # Internal quality metrics
    quality: QualityMetrics


# ============================================================================
# Competitor Node Types
# ============================================================================

class CompetitorInfo(TypedDict, total=False):
    """Information about a single competitor with strict classification."""
    name: str
    url: str
    description: str
    funding: str
    # STRICT 6-TYPE CLASSIFICATION
    type: str  # direct_product | adjacent_product | directory_or_list | content_or_media | platform_or_tool_non_substitutable | noise
    justification: str  # Why this classification was assigned
    confidence: float  # 0.0 to 1.0 - classification confidence
    relevance_score: float  # Semantic relevance to the idea


class MarketStructure(TypedDict, total=False):
    """Market structure derived ONLY from scoring competitors."""
    type: str  # fragmented | emerging | consolidated | monopolized
    confidence: float
    evidence: List[str]  # Derived ONLY from scoring competitors


class CompetitorAnalysis(TypedDict, total=False):
    """
    Output from the competitor analysis node.
    
    CRITICAL: market_structure is computed using ONLY scoring_competitors
    (direct_product + adjacent_product). Non-scoring competitors are listed
    for context but NEVER affect verdicts or market structure classification.
    
    NOTE: market_saturation has been REMOVED. Use market_structure instead.
    """
    # Counts
    competitors_found: int
    scoring_competitors_count: int      # direct_product + adjacent_product ONLY
    non_scoring_competitors_count: int  # All other types
    
    # Separated competitor lists
    scoring_competitors: List[CompetitorInfo]      # ONLY direct + adjacent
    non_scoring_competitors: List[CompetitorInfo]  # All others (context only)
    
    # Legacy fields for backward compatibility
    direct_competitors: List[CompetitorInfo]
    indirect_competitors: List[CompetitorInfo]
    
    # What was excluded from scoring (for transparency)
    excluded_from_scoring: List[str]  # e.g., ["blogs", "directories", "listicles"]
    
    # Market analysis - ONLY from scoring competitors
    # NOTE: market_structure REPLACES market_saturation entirely
    market_structure: MarketStructure
    differentiation_opportunities: List[str]
    total_funding_in_space: str
    
    # Internal quality metrics
    quality: QualityMetrics


# ============================================================================
# Judge Node Types
# ============================================================================

class EpistemicStatus(TypedDict, total=False):
    """Epistemic quality assessment of the analysis."""
    confidence_level: float              # 0.0-1.0, gated at 0.6
    data_quality_warning: Optional[str]
    contradiction_flag: bool
    contradictions: List[str]
    insufficient_signals: List[str]


class RecommendationCondition(TypedDict, total=False):
    """
    A single falsifiable condition for the recommendation.
    
    Each condition MUST be:
    - Falsifiable: Can be proven true or false
    - Testable: Has a clear method of verification
    - Specific: Tied to a concrete risk or dependency
    
    Example acceptable conditions:
    - "If cafés accept guaranteed seating contracts within 30 days"
    - "If users prepay for 1-hour slots at ≥$5"
    - "If venue churn exceeds 20% after pilot, stop"
    
    Unacceptable conditions (generic/unfalsifiable):
    - "If marketing is good"
    - "If users like it"
    """
    condition: str           # The falsifiable statement (e.g., "If X achieves Y within Z")
    test_method: str         # How to verify this condition (e.g., "Run 2-week pilot in 3 cities")
    linked_risk: str         # Which risk/assumption this addresses (e.g., "supply_acquisition")


class ConditionalRecommendation(TypedDict, total=False):
    """
    Replaces simple string recommendation with conditional logic.
    
    DECISION TYPES:
    
    1. conditional_go
       - Core signals are positive
       - Success depends on 1-3 falsifiable assumptions
       - Suitable for founders ready to validate quickly
    
    2. experiment
       - Signals are mixed or uncertain
       - Small, cheap tests required before commitment
       - No scaling implied
    
    3. wait
       - Market or infrastructure not ready
       - Timing risk dominates idea risk
    
    4. avoid
       - Structural barriers are high
       - Key assumptions are unlikely or untestable
    
    REQUIRED: Every recommendation MUST include ≥2 explicit conditions.
    """
    decision: str            # conditional_go | experiment | wait | avoid
    conditions: List[RecommendationCondition]  # Minimum 2 required
    rationale: str           # Why this decision AND why not unconditional


class MarketReality(TypedDict, total=False):
    """Ground truth about market conditions (verified data only)."""
    verified_competitors: List[str]      # Names of DIRECT products only
    verified_competitor_count: int
    noise_discarded_count: int
    weighted_pressure_score: float       # Σ(relevance × dominance × weight)
    market_structure_type: str           # fragmented | emerging | consolidated | monopolized
    barrier_to_entry: str                # High/Medium/Low
    total_verified_funding: str
    dominant_players: List[str]


class Unknown(TypedDict, total=False):
    """
    A claim or assumption that lacks direct evidence.
    
    CORE PRINCIPLE: If a claim is not directly supported by evidence,
    it MUST be declared as an unknown. Silence about uncertainty is failure.
    
    CONFIDENCE RULES:
    - 0.0-0.3: Low evidence, high uncertainty
    - 0.3-0.6: Mixed signals, moderate uncertainty
    - 0.6-0.9: Strong multi-source evidence
    - 0.9-1.0: Near-certain (rare, requires behavioral proof)
    
    CLAIM EXAMPLES:
    - Users will pay
    - Venues will participate
    - Market is growing
    - Competition is weak
    - Differentiation is sufficient
    - Revenue model is viable
    """
    claim: str           # The uncertain claim or assumption
    confidence: float    # 0.0-1.0, subjective but justified
    reason: str          # Why this is uncertain or unsupported
    source: str          # Which analysis section this relates to
    evidence_gap: str    # What evidence would resolve this unknown


class KillCriterion(TypedDict, total=False):
    """
    Explicit kill criterion that can terminate the idea.
    
    CORE PRINCIPLE: Analysis without the ability to kill is invalid.
    Every action must have a kill switch. Every idea must be allowed to die.
    
    REQUIREMENTS:
    - Must be measurable (specific numbers/metrics)
    - Must be falsifiable (can be proven false)
    - Must be tied to a core assumption
    - Must explicitly state when to STOP
    
    VALID EXAMPLES:
    - "If <10% of surveyed users prepay → stop"
    - "If <5 cafés agree to contracts → stop"
    - "If CAC exceeds first-month revenue → stop"
    
    INVALID EXAMPLES:
    - "Validate demand" (not measurable)
    - "Test MVP" (no stop condition)
    - "Explore partnerships" (vague)
    """
    criterion: str           # "If X fails → stop" format
    category: str            # user_side | supply_side | willingness_to_pay | unit_economics
    linked_unknown: str      # Which unknown this tests
    test_cost: str           # cheap (<$500) | moderate ($500-$5000) | expensive (>$5000)
    test_duration: str       # fast (<1 week) | moderate (1-4 weeks) | slow (>4 weeks)


class FalsificationTest(TypedDict, total=False):
    """Adversarial analysis - reasons the idea might fail."""
    killer_feature_missing: str
    why_this_might_fail: str
    adversarial_concerns: List[str]
    market_timing_risk: str


class FinalVerdict(TypedDict, total=False):
    """
    Output from the judge node - matches API schema.
    
    BREAKING CHANGES:
    - recommendation is now ConditionalRecommendation (not string)
    - action_items replaced by kill_criteria
    
    REQUIRED: unknowns and kill_criteria MUST be populated. Empty lists NOT allowed.
    """
    # Core assessment
    overall_score: int  # 0-100
    recommendation: ConditionalRecommendation  # REPLACED: was string (go/no_go)
    confidence: float  # 0-1
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    risk_factors: List[str]
    
    # MANDATORY: Epistemic uncertainty layer
    unknowns: List[Unknown]  # REQUIRED, never empty - surfaces all uncertain claims
    
    # MANDATORY: Kill criteria (replaces action_items)
    kill_criteria: List[KillCriterion]  # REQUIRED - explicit stop conditions
    
    # Epistemic rigour fields
    epistemic_status: EpistemicStatus
    market_reality: MarketReality
    falsification_test: FalsificationTest
    kill_switch_triggered: bool
    kill_switch_reason: Optional[str]
    
    # Internal quality metrics
    quality: QualityMetrics


# ============================================================================
# Main State Schema
# ============================================================================

class ValidationState(TypedDict, total=False):
    """
    Main state schema for the validation pipeline.
    
    Field names match the existing API contract in routers/validation.py:
    - idea_input (not startup_idea)
    - reddit_sentiment (not reddit_data)
    - trends_data
    - competitor_analysis (not competitors_data)
    - final_verdict (not verdict)
    - processing_errors
    """
    # Input field - matches router expectation
    idea_input: str
    
    # Node outputs - match router expectations
    reddit_sentiment: Optional[RedditSentiment]
    trends_data: Optional[TrendsData]
    competitor_analysis: Optional[CompetitorAnalysis]
    final_verdict: Optional[FinalVerdict]
    
    # Error tracking
    processing_errors: Annotated[List[str], operator.add]
