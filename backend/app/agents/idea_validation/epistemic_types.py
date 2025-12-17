"""
Epistemic Types Module

Strict type definitions for epistemic rigour in idea validation.
Enforces "Taxonomy or Death" rule with weighted classifications.

CORE PRINCIPLES:
- No entity influences verdict until classified
- NOISE entities have weight 0.0 and are discarded
- All scores are weighted, not count-based
"""

from enum import Enum
from typing import TypedDict, Optional, List
from dataclasses import dataclass


# =============================================================================
# Competitor Classification (Strict Taxonomy)
# =============================================================================

class CompetitorType(str, Enum):
    """
    STRICT 6-TYPE COMPETITOR TAXONOMY
    
    Each discovered competitor MUST be classified into EXACTLY ONE type.
    Classification is mutually exclusive and deterministic.
    
    SCORING TYPES (influence verdicts):
    - direct_product: User could substitute THIS product for the proposed idea
    - adjacent_product: Overlaps partially, different primary use
    
    NON-SCORING TYPES (context only, never affect verdicts):
    - directory_or_list: Aggregators without execution capability
    - content_or_media: Blogs, articles, listicles, ProductHunt pages
    - platform_or_tool_non_substitutable: Different core function entirely
    - noise: SEO spam, broken matches, irrelevant results
    """
    # Scoring types - ONLY these affect market structure and verdicts
    DIRECT_PRODUCT = "direct_product"
    ADJACENT_PRODUCT = "adjacent_product"
    
    # Non-scoring types - Listed for context ONLY
    DIRECTORY_OR_LIST = "directory_or_list"
    CONTENT_OR_MEDIA = "content_or_media"
    PLATFORM_OR_TOOL = "platform_or_tool_non_substitutable"
    NOISE = "noise"


# Define which types are allowed to influence scoring
SCORING_COMPETITOR_TYPES = frozenset({
    CompetitorType.DIRECT_PRODUCT,
    CompetitorType.ADJACENT_PRODUCT,
})

NON_SCORING_COMPETITOR_TYPES = frozenset({
    CompetitorType.DIRECTORY_OR_LIST,
    CompetitorType.CONTENT_OR_MEDIA,
    CompetitorType.PLATFORM_OR_TOOL,
    CompetitorType.NOISE,
})


# Weights for pressure calculation - NON-SCORING types have ZERO weight
COMPETITOR_WEIGHTS = {
    CompetitorType.DIRECT_PRODUCT: 1.0,      # Full weight - direct substitute
    CompetitorType.ADJACENT_PRODUCT: 0.5,    # Half weight - partial overlap
    CompetitorType.DIRECTORY_OR_LIST: 0.0,   # ZERO - never affects scoring
    CompetitorType.CONTENT_OR_MEDIA: 0.0,    # ZERO - never affects scoring
    CompetitorType.PLATFORM_OR_TOOL: 0.0,    # ZERO - never affects scoring
    CompetitorType.NOISE: 0.0,               # ZERO - never affects scoring
}


# =============================================================================
# Query Intent Classification
# =============================================================================

class QueryIntent(str, Enum):
    """
    Search query intent classification for trends analysis.
    Transactional queries indicate higher commercial viability.
    """
    TRANSACTIONAL = "transactional"   # "buy X", "X pricing", "X demo"
    COMMERCIAL = "commercial"         # "best X tool", "X alternatives"
    INFORMATIONAL = "informational"   # "what is X", "how does X work"
    NAVIGATIONAL = "navigational"     # Brand/company searches


# Intent confidence modifiers
INTENT_CONFIDENCE_MODIFIERS = {
    QueryIntent.TRANSACTIONAL: +0.15,
    QueryIntent.COMMERCIAL: +0.05,
    QueryIntent.INFORMATIONAL: -0.10,
    QueryIntent.NAVIGATIONAL: 0.0,
}


# =============================================================================
# Signal Detection Keywords
# =============================================================================

# Transactional intent signals (boost confidence)
TRANSACTIONAL_SIGNALS = frozenset({
    "pricing", "price", "cost", "buy", "purchase", "subscribe",
    "demo", "trial", "signup", "sign up", "get started",
    "free trial", "paid", "subscription", "plan", "tier"
})

# Commercial intent signals
COMMERCIAL_SIGNALS = frozenset({
    "best", "top", "vs", "versus", "alternative", "alternatives",
    "review", "reviews", "comparison", "compare", "recommended"
})

# Noise indicators (should be classified as NOISE)
NOISE_INDICATORS = frozenset({
    "top 10", "top 5", "top 20", "best of", "list of",
    "blog", "article", "news", "directory", "guide",
    "what is", "how to", "tutorial", "explained"
})

# Product indicators (suggest real product, not noise)
PRODUCT_SIGNALS = frozenset({
    "pricing", "login", "sign up", "signup", "dashboard",
    "get started", "book demo", "request demo", "features",
    "enterprise", "customers", "case study", "integrations",
    "api", "documentation", "download", "app store", "play store"
})


# =============================================================================
# WEIGHTED EVIDENCE: Signal Weights
# =============================================================================
# 
# CORE RULE: NO metric may affect scoring without an explicit weight.
# If a signal has no weight, it has NO IMPACT.
# Quality > quantity. Few strong signals > many weak signals.
#

# Reddit / Qualitative Signal Weights
REDDIT_SIGNAL_WEIGHTS = {
    # HIGH VALUE - Direct behavioral/transactional evidence
    "pricing_intent": 3.0,          # Explicit willingness to pay, budgeting, prepay discussions
    "behavioral_complaint": 2.0,     # Specific unmet needs, frustrated users seeking solutions
    "tool_seeking": 2.0,            # Direct requests for recommendations, alternatives
    
    # MEDIUM VALUE - Opinion with context
    "detailed_review": 1.5,         # In-depth user experience or evaluation
    "use_case_mention": 1.5,        # Specific scenario where product would be used
    "casual_mention": 1.0,          # General discussion, opinions without specifics
    
    # LOW VALUE - Weak signals
    "hypothetical": 0.5,            # Abstract or theoretical discussion
    "question_only": 0.5,           # Questions without engagement/answers
    
    # ZERO VALUE - Never affects scores
    "blog_listicle": 0.0,           # Blog posts, lists, media mentions
    "promotional": 0.0,             # Marketing/promotional content
    "off_topic": 0.0,               # Irrelevant discussions captured by keyword
}

# Competitor Signal Weights (extends existing COMPETITOR_WEIGHTS)
COMPETITOR_SIGNAL_WEIGHTS = {
    # Scoring types only
    "direct_product_with_users": 3.0,     # Confirmed users, transactions
    "direct_product_unknown_traction": 2.0,  # Direct substitute but traction unknown
    "adjacent_product": 1.5,              # Partial overlap, different core
    
    # Non-scoring - ZERO
    "directory_aggregator": 0.0,
    "content_media": 0.0,
    "blog_listicle": 0.0,
}

# Trend Signal Weights
TREND_SIGNAL_WEIGHTS = {
    # HIGH VALUE - Strong market signals
    "sustained_growth_3y": 2.0,      # Sustained multi-year growth pattern
    "rising_transactional": 2.0,     # Rising trend on transactional queries
    
    # MEDIUM VALUE - Moderate signals
    "sustained_growth_1y": 1.5,      # 1-year growth pattern
    "rising_commercial": 1.5,        # Rising trend on commercial queries
    "stable_high_volume": 1.0,       # Stable but high volume
    
    # LOW VALUE - Weak signals
    "short_term_spike": 0.5,         # Short-term spike, unclear sustainability
    "stable_low_volume": 0.5,        # Stable but low volume
    "unclear_trend": 0.5,            # Cannot determine direction
    
    # ZERO VALUE
    "generic_query": 0.0,            # Generic/unrelated queries
    "declining": 0.0,                # Declining trend (negative signal)
}


# Signal strength interpretation
SIGNAL_STRENGTH_LABELS = {
    (0.0, 0.0): "No evidence",
    (0.1, 2.0): "Weak signals",
    (2.1, 5.0): "Moderate signals",
    (5.1, 10.0): "Good evidence",
    (10.1, float("inf")): "Strong evidence",
}


def get_signal_strength_label(weighted_sum: float) -> str:
    """Convert weighted signal sum to human-readable strength label."""
    for (low, high), label in SIGNAL_STRENGTH_LABELS.items():
        if low <= weighted_sum <= high:
            return label
    return "Strong evidence"


# =============================================================================
# Dominance Estimation
# =============================================================================

class FundingStage(str, Enum):
    """Funding stage for dominance estimation."""
    UNKNOWN = "unknown"
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C_PLUS = "series_c_plus"
    PUBLIC = "public"


# Dominance factors by funding stage
FUNDING_DOMINANCE_FACTORS = {
    FundingStage.UNKNOWN: 0.3,
    FundingStage.PRE_SEED: 0.2,
    FundingStage.SEED: 0.4,
    FundingStage.SERIES_A: 0.6,
    FundingStage.SERIES_B: 0.8,
    FundingStage.SERIES_C_PLUS: 1.0,
    FundingStage.PUBLIC: 1.0,
}


# =============================================================================
# Epistemic Output Schemas
# =============================================================================

class EpistemicStatus(TypedDict, total=False):
    """
    Epistemic quality assessment of the analysis.
    confidence_level < 0.6 MUST trigger "Inconclusive" verdict.
    """
    confidence_level: float              # 0.0-1.0, gated at 0.6
    data_quality_warning: Optional[str]  # Human-readable warning
    contradiction_flag: bool             # True if data sources contradict
    contradictions: List[str]            # List of specific contradictions
    insufficient_signals: List[str]      # Missing data sources


class MarketReality(TypedDict, total=False):
    """
    Ground truth about market conditions.
    Only verified DIRECT competitors included.
    
    NOTE: saturation_level has been REMOVED. Use market_structure_type instead.
    """
    verified_competitors: List[str]      # Names of verified DIRECT products only
    verified_competitor_count: int       # Count of DIRECT only
    noise_discarded_count: int           # How many NOISE results filtered
    weighted_pressure_score: float       # Σ(relevance × dominance × weight)
    market_structure_type: str           # fragmented | emerging | consolidated | monopolized
    barrier_to_entry: str                # High/Medium/Low
    total_verified_funding: str          # Sum of known funding
    dominant_players: List[str]          # Top 3 by dominance


class FalsificationTest(TypedDict, total=False):
    """
    Adversarial analysis - reasons the idea might fail.
    Required for epistemic honesty.
    """
    killer_feature_missing: str          # What unique feature is lacking
    why_this_might_fail: str             # Pre-mortem summary
    adversarial_concerns: List[str]      # Specific failure modes
    market_timing_risk: str              # Too early/late/crowded


# =============================================================================
# Confidence Calculation Rules
# =============================================================================

# Minimum confidence threshold for non-inconclusive verdict
CONFIDENCE_THRESHOLD = 0.6

# Confidence adjustments
CONFIDENCE_ADJUSTMENTS = {
    "transactional_keyword_match": +0.10,
    "recent_community_discussion": +0.15,  # <6 months
    "product_signals_detected": +0.10,
    "generic_ai_content": -0.25,
    "no_direct_competitors_found": -0.15,  # Suspicious
    "high_noise_ratio": -0.20,
    "data_source_missing": -0.15,
}


# =============================================================================
# Kill Switch Thresholds
# =============================================================================

KILL_SWITCH_THRESHOLDS = {
    "direct_competitor_count": 3,         # If >= 3 direct competitors
    "total_funding_millions": 50,         # AND funding > $50M
    "weighted_pressure_threshold": 2.5,   # OR pressure score > 2.5
}


# =============================================================================
# Dataclass for Classified Competitor
# =============================================================================

@dataclass
class ClassifiedCompetitor:
    """A competitor that has been strictly classified."""
    name: str
    url: str
    description: str
    competitor_type: CompetitorType
    relevance_score: float           # 0.0-1.0, semantic similarity
    dominance_factor: float          # 0.0-1.0, based on funding/market presence
    funding_stage: FundingStage
    funding_amount: Optional[str]
    classification_confidence: float # How confident we are in the classification
    
    @property
    def weight(self) -> float:
        """Get the weight for this competitor type."""
        return COMPETITOR_WEIGHTS[self.competitor_type]
    
    @property
    def pressure_contribution(self) -> float:
        """Calculate this competitor's contribution to market pressure."""
        return self.relevance_score * self.dominance_factor * self.weight
    
    @property
    def is_noise(self) -> bool:
        """Check if this should be discarded from calculations."""
        return self.competitor_type == CompetitorType.NOISE
