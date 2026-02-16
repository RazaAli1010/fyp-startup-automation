"""
Judge Logic Node (Deterministic)

Aggregates data from all upstream nodes and produces a final verdict
with transparent scoring, uncertainty propagation, and full schema compliance.

All scoring is deterministic — no LLM calls, no external API calls.
"""

import statistics
import asyncio
from typing import Dict, List, Any, Optional, Tuple

from ..state import (
    ValidationState, FinalVerdict, QualityMetrics,
    RedditSentiment, TrendsData, CompetitorAnalysis,
    EpistemicStatus, MarketReality, FalsificationTest,
    ConditionalRecommendation, RecommendationCondition,
    Unknown, KillCriterion
)
from ..timing import StepTimer, log_timing
from ..epistemic_types import (
    CompetitorType, CONFIDENCE_THRESHOLD, KILL_SWITCH_THRESHOLDS,
    CONFIDENCE_ADJUSTMENTS, REDDIT_SIGNAL_WEIGHTS, TREND_SIGNAL_WEIGHTS,
    get_signal_strength_label
)
from ..scoring_engine import ValidationMetrics, calculate_viability_score


# Scoring rubric with weights
SCORING_DIMENSIONS = {
    "market_demand": {"weight": 0.20, "description": "Market size and demand signals"},
    "sentiment": {"weight": 0.15, "description": "Public sentiment from discussions"},
    "competition": {"weight": 0.20, "description": "Competition intensity"},
    "trend_momentum": {"weight": 0.15, "description": "Search trend direction"},
    "feasibility": {"weight": 0.15, "description": "Technical/operational feasibility"},
    "economics": {"weight": 0.15, "description": "Economic sustainability"},
}

# Known parking competitors list removed - handled by dynamic semantic validation upstream
# KNOWN_COMPETITORS removed


# =============================================================================
# EPISTEMIC RIGOUR: Kill Switch & Contradiction Detection
# =============================================================================

def _check_kill_switch(
    direct_competitor_count: int,
    total_funding_millions: float,
    weighted_pressure: float
) -> Tuple[bool, Optional[str]]:
    """
    Kill switch: Auto-reject if market is dominated by well-funded incumbents.
    
    Conditions:
    - direct_competitors >= 3 AND funding >= $50M
    - OR weighted_pressure >= 2.5
    
    Returns: (triggered, reason)
    """
    if direct_competitor_count >= KILL_SWITCH_THRESHOLDS["direct_competitor_count"] and \
       total_funding_millions >= KILL_SWITCH_THRESHOLDS["total_funding_millions"]:
        return True, f"HIGH_RISK: {direct_competitor_count} direct competitors with ${total_funding_millions:.0f}M+ funding"
    
    if weighted_pressure >= KILL_SWITCH_THRESHOLDS["weighted_pressure_threshold"]:
        return True, f"HIGH_RISK: Market pressure score {weighted_pressure:.2f} exceeds threshold"
    
    return False, None


def _detect_contradictions(
    reddit_data: Optional[RedditSentiment],
    trends_data: Optional[TrendsData],
    competitor_data: Optional[CompetitorAnalysis]
) -> Tuple[bool, List[str]]:
    """
    Detect contradictions between data sources.
    
    Examples:
    - Positive Reddit sentiment + zero search volume = suspicious
    - "emerging" market structure + dominant funded players = mismatch
    """
    contradictions = []
    
    # Reddit positive but no search interest
    if reddit_data and trends_data:
        sentiment = reddit_data.get("overall_sentiment", "")
        sentiment_score = reddit_data.get("sentiment_score", 0)
        interest_score = trends_data.get("interest_score", 0)
        
        if sentiment_score > 0.3 and interest_score < 15:
            contradictions.append(
                f"MISMATCH: Positive community sentiment ({sentiment}) but very low search interest ({interest_score})"
            )
    
    # Market structure contradictions
    if competitor_data:
        market_structure = competitor_data.get("market_structure", {})
        structure_type = market_structure.get("type", "unknown")
        scoring_count = competitor_data.get("scoring_competitors_count", 0)
        direct_count = len(competitor_data.get("direct_competitors", []))
        
        # "emerging" claimed but many direct competitors
        if structure_type == "emerging" and direct_count >= 5:
            contradictions.append(
                f"MISMATCH: 'emerging' market structure claimed but {direct_count} direct competitors found"
            )
        
        # "fragmented" should indicate opportunity, not barrier
        if structure_type == "fragmented" and scoring_count >= 4:
            # This is fine - fragmented means opportunity
            pass
    
    # High trends but negative sentiment
    if reddit_data and trends_data:
        sentiment_score = reddit_data.get("sentiment_score", 0)
        interest_score = trends_data.get("interest_score", 0)
        
        if interest_score > 70 and sentiment_score < -0.2:
            contradictions.append(
                f"MISMATCH: High search interest ({interest_score}) but negative sentiment ({sentiment_score:.2f})"
            )
    
    return len(contradictions) > 0, contradictions


def _is_insufficient_data(data: Optional[Dict]) -> bool:
    """Check if a node returned insufficient data."""
    if not data:
        return True
    
    quality = data.get("quality", {})
    if quality.get("data_volume", 0) == 0:
        return True
    if quality.get("confidence", 0) < 0.1:
        return True
    
    # Check for explicit insufficient_data markers
    if data.get("overall_sentiment") == "insufficient_data":
        return True
    if data.get("trend_direction") == "insufficient_data":
        return True
    # NOTE: market_saturation removed - check market_structure instead
    market_structure = data.get("market_structure", {})
    if market_structure.get("confidence", 1.0) == 0.0:
        return True
    
    return False


def _has_known_competitors(competitor_data: Optional[CompetitorAnalysis]) -> bool:
    """Check if known competitors were found (based on flag from upstream)."""
    if not competitor_data:
        return False
        
    # Rely on the upstream node's "is_known" flag which might be set by more advanced logic
    # or simply check if we have high-relevance direct competitors
    direct = competitor_data.get("direct_competitors", [])
    return any(c.get("is_known", False) for c in direct)


def _calculate_market_demand_score(
    trends_data: Optional[TrendsData],
    reddit_data: Optional[RedditSentiment]
) -> Tuple[float, float, str]:
    """
    Calculate market demand score using WEIGHTED EVIDENCE, not counts.
    
    CORE RULE: Quality > quantity. Few strong signals outweigh many weak ones.
    Raw counts (post counts, competitor counts) do NOT influence scores directly.
    """
    weighted_signals = []
    confidences = []
    signal_explanations = []
    
    # === TRENDS DATA: Weighted by signal type ===
    if trends_data and not _is_insufficient_data(trends_data):
        trend_direction = trends_data.get("trend_direction", "")
        interest_score = trends_data.get("interest_score", 0)
        temporal_trend = trends_data.get("temporal_trend", "stable")
        quality = trends_data.get("quality", {})
        
        # Determine trend signal type and weight
        if trend_direction == "rising" and temporal_trend == "growing":
            if interest_score > 70:
                trend_weight = TREND_SIGNAL_WEIGHTS["sustained_growth_3y"]
                trend_score = 85
                signal_explanations.append(f"Sustained rising trend (weight={trend_weight})")
            else:
                trend_weight = TREND_SIGNAL_WEIGHTS["sustained_growth_1y"]
                trend_score = 75
                signal_explanations.append(f"Rising trend (weight={trend_weight})")
        elif trend_direction == "rising":
            trend_weight = TREND_SIGNAL_WEIGHTS["rising_commercial"]
            trend_score = 70
            signal_explanations.append(f"Rising direction (weight={trend_weight})")
        elif trend_direction == "stable" and interest_score > 50:
            trend_weight = TREND_SIGNAL_WEIGHTS["stable_high_volume"]
            trend_score = 55
            signal_explanations.append(f"Stable high volume (weight={trend_weight})")
        elif trend_direction == "stable":
            trend_weight = TREND_SIGNAL_WEIGHTS["stable_low_volume"]
            trend_score = 45
            signal_explanations.append(f"Stable low volume (weight={trend_weight})")
        elif trend_direction == "falling":
            trend_weight = TREND_SIGNAL_WEIGHTS["declining"]
            trend_score = 25
            signal_explanations.append(f"Declining trend (weight={trend_weight})")
        else:
            trend_weight = TREND_SIGNAL_WEIGHTS["unclear_trend"]
            trend_score = 40
            signal_explanations.append(f"Unclear trend (weight={trend_weight})")
        
        weighted_signals.append((trend_score, trend_weight))
        confidences.append(quality.get("confidence", 0.5))
    
    # === REDDIT DATA: Weighted by signal quality, NOT post count ===
    if reddit_data and not _is_insufficient_data(reddit_data):
        quality = reddit_data.get("quality", {})
        sentiment_score = reddit_data.get("sentiment_score", 0)
        key_concerns = reddit_data.get("key_concerns", [])
        key_praises = reddit_data.get("key_praises", [])
        
        # Analyze signal quality from content, not count
        # High-weight signals: pricing mentions, behavioral complaints, tool-seeking
        has_pricing_signals = any(
            any(kw in str(c).lower() for kw in ["price", "cost", "pay", "budget", "afford"])
            for c in (key_concerns + key_praises)
        )
        has_behavioral_signals = any(
            any(kw in str(c).lower() for kw in ["need", "want", "looking for", "wish", "frustrat"])
            for c in key_concerns
        )
        
        # Calculate weighted signal sum
        reddit_weighted_sum = 0.0
        if has_pricing_signals:
            reddit_weighted_sum += REDDIT_SIGNAL_WEIGHTS["pricing_intent"]
            signal_explanations.append(f"Pricing intent detected (weight={REDDIT_SIGNAL_WEIGHTS['pricing_intent']})")
        
        if has_behavioral_signals:
            reddit_weighted_sum += REDDIT_SIGNAL_WEIGHTS["behavioral_complaint"]
            signal_explanations.append(f"Behavioral complaints (weight={REDDIT_SIGNAL_WEIGHTS['behavioral_complaint']})")
        
        # Sentiment contributes as contextual signal
        if sentiment_score > 0.3:
            reddit_weighted_sum += REDDIT_SIGNAL_WEIGHTS["detailed_review"]
            signal_explanations.append(f"Positive sentiment context (weight={REDDIT_SIGNAL_WEIGHTS['detailed_review']})")
        elif sentiment_score > 0:
            reddit_weighted_sum += REDDIT_SIGNAL_WEIGHTS["casual_mention"]
        else:
            reddit_weighted_sum += REDDIT_SIGNAL_WEIGHTS["hypothetical"]
        
        # Convert weighted signal sum to score (NOT based on post count)
        # Strong evidence (>5 weighted) → high score
        # Weak evidence (<2 weighted) → low score
        if reddit_weighted_sum >= 5.0:
            reddit_score = 80
        elif reddit_weighted_sum >= 3.0:
            reddit_score = 65
        elif reddit_weighted_sum >= 2.0:
            reddit_score = 55
        elif reddit_weighted_sum > 0:
            reddit_score = 45
        else:
            reddit_score = 35
        
        # Weight for this data source based on signal quality
        reddit_weight = min(2.0, reddit_weighted_sum / 2.0)
        weighted_signals.append((reddit_score, max(0.5, reddit_weight)))
        confidences.append(quality.get("confidence", 0.5))
    
    if not weighted_signals:
        return 50.0, 0.2, "Insufficient data for weighted analysis"
    
    # === WEIGHTED AVERAGE: Scores weighted by signal quality ===
    total_weight = sum(w for _, w in weighted_signals)
    if total_weight == 0:
        return 50.0, 0.2, "No weighted signals detected"
    
    weighted_score = sum(s * w for s, w in weighted_signals) / total_weight
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
    
    # Build transparent rationale
    strength_label = get_signal_strength_label(total_weight)
    rationale = f"{strength_label}: " + "; ".join(signal_explanations[:3])
    
    return (
        round(weighted_score, 1),
        round(avg_confidence, 2),
        rationale
    )


def _calculate_sentiment_score(
    reddit_data: Optional[RedditSentiment]
) -> Tuple[float, float, str]:
    """
    Calculate sentiment score using WEIGHTED EVIDENCE quality, not just sentiment value.
    
    CORE RULE: Sentiment from high-quality signals (behavioral, tool-seeking) 
    is weighted more than casual mentions.
    """
    if not reddit_data or _is_insufficient_data(reddit_data):
        return 50.0, 0.2, "Insufficient data"
    
    sentiment = reddit_data.get("overall_sentiment", "neutral")
    sentiment_value = reddit_data.get("sentiment_score", 0)
    quality = reddit_data.get("quality", {})
    key_concerns = reddit_data.get("key_concerns", [])
    key_praises = reddit_data.get("key_praises", [])
    
    # Analyze signal quality to weight the sentiment
    signal_weight = 0.5  # Base weight for raw sentiment
    signal_explanations = []
    
    # Check for high-quality signals that increase sentiment weight
    has_behavioral = any(
        any(kw in str(c).lower() for kw in ["need", "want", "frustrat", "problem", "struggle"])
        for c in key_concerns
    )
    has_use_case = any(
        any(kw in str(c).lower() for kw in ["use case", "scenario", "would use", "looking for"])
        for c in (key_concerns + key_praises)
    )
    has_detailed = len(key_praises) >= 2 or len(key_concerns) >= 2
    
    if has_behavioral:
        signal_weight += REDDIT_SIGNAL_WEIGHTS["behavioral_complaint"]
        signal_explanations.append(f"Behavioral signals (weight={REDDIT_SIGNAL_WEIGHTS['behavioral_complaint']})")
    if has_use_case:
        signal_weight += REDDIT_SIGNAL_WEIGHTS["use_case_mention"]
        signal_explanations.append(f"Use case mentions (weight={REDDIT_SIGNAL_WEIGHTS['use_case_mention']})")
    if has_detailed:
        signal_weight += REDDIT_SIGNAL_WEIGHTS["detailed_review"]
        signal_explanations.append(f"Detailed feedback (weight={REDDIT_SIGNAL_WEIGHTS['detailed_review']})")
    
    # Base score from sentiment value, but weighted by signal quality
    base_score = 50 + (sentiment_value * 40)
    base_score = max(10, min(90, base_score))
    
    # Confidence scales with signal quality weight
    confidence_boost = min(0.3, signal_weight * 0.05)
    adjusted_confidence = min(0.95, quality.get("confidence", 0.5) + confidence_boost)
    
    # Build transparent rationale
    strength_label = get_signal_strength_label(signal_weight)
    explanation = "; ".join(signal_explanations[:2]) if signal_explanations else "Casual mentions only"
    rationale = f"Sentiment: {sentiment} ({sentiment_value:.2f}). {strength_label}: {explanation}"
    
    return (
        round(base_score, 1),
        round(adjusted_confidence, 2),
        rationale
    )


def _parse_funding_to_millions(funding_str: str) -> float:
    """Parse funding string to numeric value in millions USD."""
    import re
    if not funding_str or funding_str == "Unknown":
        return 0.0
    
    match = re.search(r'\$?([\d\.]+)\s*([MBK])', funding_str, re.IGNORECASE)
    if match:
        amount = float(match.group(1))
        unit = match.group(2).upper()
        if unit == 'B':
            return amount * 1000
        elif unit == 'K':
            return amount / 1000
        return amount
    return 0.0


def _calculate_competition_score(
    competitor_data: Optional[CompetitorAnalysis]
) -> Tuple[float, float, str]:
    """
    Calculate competition score based on MARKET STRUCTURE, not saturation.
    
    Structure-based scoring:
    - fragmented: High score (opportunity for consolidation)
    - emerging: High score (early mover advantage)
    - consolidated: Medium score (differentiation required)
    - monopolized: Low score (extremely hard to enter)
    """
    if not competitor_data or _is_insufficient_data(competitor_data):
        return 50.0, 0.2, "Insufficient data"
    
    market_structure = competitor_data.get("market_structure", {})
    structure_type = market_structure.get("type", "unknown")
    structure_confidence = market_structure.get("confidence", 0.5)
    
    scoring_count = competitor_data.get("scoring_competitors_count", 0)
    direct_count = len(competitor_data.get("direct_competitors", []))
    quality = competitor_data.get("quality", {})
    
    # CRITICAL: Score based on STRUCTURE, not count
    # Many weak players = OPPORTUNITY (fragmented)
    # Few strong players = BARRIER (consolidated/monopolized)
    structure_scores = {
        "fragmented": 70,    # Opportunity for consolidation
        "emerging": 75,      # Early mover advantage
        "consolidated": 45,  # Differentiation required
        "monopolized": 20,   # Extremely hard to enter
        "unknown": 50,
    }
    base_score = structure_scores.get(structure_type, 50)
    
    # Adjust by evidence quality, not raw count
    if structure_confidence >= 0.8:
        pass  # Trust the structure classification
    elif structure_confidence >= 0.6:
        base_score = base_score * 0.95  # Slight uncertainty penalty
    else:
        base_score = 50  # Low confidence - default to neutral
    
    # Build rationale from evidence
    evidence = market_structure.get("evidence", [])
    evidence_summary = evidence[0] if evidence else "No evidence available"
    
    return (
        round(base_score, 1),
        round(min(quality.get("confidence", 0.5), structure_confidence), 2),
        f"Market structure: {structure_type}. {evidence_summary}"
    )


def _calculate_trend_momentum_score(
    trends_data: Optional[TrendsData]
) -> Tuple[float, float, str]:
    """
    Calculate trend momentum score using WEIGHTED SIGNAL TYPES.
    
    CORE RULE: Sustained multi-year growth has higher weight than short-term spikes.
    Generic queries have zero weight.
    """
    if not trends_data or _is_insufficient_data(trends_data):
        return 50.0, 0.2, "Insufficient data for weighted analysis"
    
    direction = trends_data.get("trend_direction", "stable")
    temporal = trends_data.get("temporal_trend", "stable")
    interest_score = trends_data.get("interest_score", 0)
    quality = trends_data.get("quality", {})
    
    # Determine signal type and weight based on trend characteristics
    if direction == "rising" and temporal == "growing":
        if interest_score > 70:
            signal_type = "sustained_growth_3y"
            base_score = 90
        else:
            signal_type = "sustained_growth_1y"
            base_score = 80
    elif direction == "rising":
        signal_type = "rising_commercial"
        base_score = 70
    elif direction == "stable" and interest_score > 50:
        signal_type = "stable_high_volume"
        base_score = 55
    elif direction == "stable":
        signal_type = "stable_low_volume"
        base_score = 45
    elif direction == "falling":
        signal_type = "declining"
        base_score = 25
    else:
        signal_type = "unclear_trend"
        base_score = 40
    
    signal_weight = TREND_SIGNAL_WEIGHTS.get(signal_type, 0.5)
    
    # Build transparent rationale
    strength_label = get_signal_strength_label(signal_weight)
    rationale = f"{strength_label}: {signal_type.replace('_', ' ')} (weight={signal_weight})"
    
    return (
        round(base_score, 1),
        round(quality.get("confidence", 0.5), 2),
        rationale
    )


def _deterministic_assessment(
    dimension_scores: Dict[str, float],
    insufficient_nodes: List[str],
    market_structure_type: str,
    has_known_competitors: bool
) -> Dict[str, Any]:
    """Deterministic feasibility and economics assessment. No LLM calls."""
    md = dimension_scores.get("market_demand", 50)
    comp = dimension_scores.get("competition", 50)
    trend = dimension_scores.get("trend_momentum", 50)
    sent = dimension_scores.get("sentiment", 50)

    metrics = ValidationMetrics(
        demand_score=md,
        market_size_score=trend,
        differentiation_score=comp,
        timing_score=trend,
        execution_risk_score=max(0, 100 - comp),
        failure_risk_score=max(0, 100 - md),
        economic_viability_score=(md + comp) / 2.0,
        investor_fit_score=(trend + sent) / 2.0,
    )
    viability = calculate_viability_score(metrics)

    feasibility_score: float = viability["viability_score"]
    economics_score: float = viability["risk_adjusted_score"]

    strengths: List[str] = []
    weaknesses: List[str] = []
    risk_factors: List[str] = []

    if md >= 65:
        strengths.append("Strong market demand signals detected")
    elif md < 40:
        weaknesses.append("Weak market demand signals")
        risk_factors.append("Low market demand")

    if comp >= 65:
        strengths.append("Favorable competitive landscape")
    elif comp < 40:
        weaknesses.append("High competitive pressure")
        risk_factors.append("Intense competition")

    if trend >= 65:
        strengths.append("Positive trend momentum")
    elif trend < 40:
        weaknesses.append("Declining or weak trend momentum")
        risk_factors.append("Weak market momentum")

    if sent >= 65:
        strengths.append("Positive community sentiment")
    elif sent < 40:
        weaknesses.append("Negative or neutral sentiment")

    if market_structure_type in ["fragmented", "emerging"]:
        strengths.append(f"Market structure ({market_structure_type}) suggests opportunity")
    elif market_structure_type in ["consolidated", "monopolized"]:
        risk_factors.append(f"Market structure ({market_structure_type}) presents barriers")

    if has_known_competitors:
        risk_factors.append("Known major players in market")

    if insufficient_nodes:
        weaknesses.append(f"Insufficient data from: {', '.join(insufficient_nodes)}")
        risk_factors.append("Incomplete data coverage")

    if not strengths:
        strengths.append("Idea submitted for validation")
    if not weaknesses:
        weaknesses.append("No critical weaknesses identified")
    if not risk_factors:
        risk_factors.append("Standard market entry risks")

    summary_parts: List[str] = []
    if feasibility_score >= 65:
        summary_parts.append("Viability score indicates promising potential.")
    elif feasibility_score >= 40:
        summary_parts.append("Mixed viability signals require further validation.")
    else:
        summary_parts.append("Low viability score suggests significant challenges.")

    if len(insufficient_nodes) >= 2:
        summary_parts.append("Analysis limited by insufficient upstream data.")
    elif len(insufficient_nodes) == 1:
        summary_parts.append(f"Partial data gap in {insufficient_nodes[0]} analysis.")

    return {
        "feasibility_score": round(feasibility_score, 1),
        "economics_score": round(economics_score, 1),
        "summary": " ".join(summary_parts),
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "risk_factors": risk_factors[:3],
        "viability_breakdown": viability["score_breakdown"],
    }


def _calculate_confidence_interval(
    score: float,
    confidence: float,
    insufficient_count: int
) -> Tuple[float, float]:
    """
    Calculate confidence interval based on score, confidence, and data quality.
    WIDER intervals when data is insufficient.
    """
    # Base interval width inversely proportional to confidence
    base_width = (1 - confidence) * 30
    
    # Widen for each insufficient data source
    insufficient_penalty = insufficient_count * 8
    
    total_width = base_width + insufficient_penalty
    
    lower = max(0, score - total_width)
    upper = min(100, score + total_width)
    
    return round(lower, 1), round(upper, 1)


# =============================================================================
# EPISTEMIC UNCERTAINTY: Unknowns Extraction
# =============================================================================

def _extract_unknowns(
    reddit_data: Optional[RedditSentiment],
    trends_data: Optional[TrendsData],
    competitor_data: Optional[CompetitorAnalysis],
    dimension_scores: Dict[str, float],
    insufficient_nodes: List[str]
) -> List[Unknown]:
    """
    Extract uncertain claims and assumptions from all data sources.
    
    CORE PRINCIPLE: If a claim is not directly supported by evidence,
    it MUST be declared as an unknown. Silence about uncertainty is failure.
    
    EVIDENCE GAP DETECTION:
    - Missing pricing data
    - Absence of real transaction signals
    - Lack of behavioral proof (not opinions)
    - Reliance on anecdotal sentiment
    
    REQUIRED: Returns minimum 3 unknowns. Empty lists are NEVER valid.
    """
    unknowns: List[Unknown] = []
    
    # === REDDIT SENTIMENT UNKNOWNS ===
    if reddit_data and not _is_insufficient_data(reddit_data):
        sentiment_score = reddit_data.get("sentiment_score", 0)
        total_posts = reddit_data.get("total_posts_analyzed", 0)
        
        # Willingness to pay is ALWAYS unknown from sentiment alone
        unknowns.append({
            "claim": "Users will pay for this solution",
            "confidence": 0.25,
            "reason": f"Reddit sentiment ({sentiment_score:.2f}) reflects opinions, not purchasing behavior. {total_posts} posts analyzed but none contain transaction data.",
            "source": "reddit_sentiment",
            "evidence_gap": "Pre-orders, pricing experiments, or payment intent surveys"
        })
        
        # Positive sentiment doesn't mean adoption
        if sentiment_score > 0.3:
            unknowns.append({
                "claim": "Positive sentiment will convert to adoption",
                "confidence": 0.35,
                "reason": "Community enthusiasm does not predict user behavior. No activation or retention data.",
                "source": "reddit_sentiment",
                "evidence_gap": "Beta signup conversion rates, activation metrics, or retention cohorts"
            })
    else:
        # Insufficient Reddit data is itself an unknown
        unknowns.append({
            "claim": "Market has community interest",
            "confidence": 0.15,
            "reason": "Insufficient Reddit data to assess community sentiment or demand signals.",
            "source": "reddit_sentiment",
            "evidence_gap": "Targeted community engagement in 5+ relevant subreddits"
        })
    
    # === TRENDS UNKNOWNS ===
    if trends_data and not _is_insufficient_data(trends_data):
        interest_score = trends_data.get("interest_score", 0)
        trend_direction = trends_data.get("trend_direction", "unknown")
        
        # Search interest != purchase intent
        unknowns.append({
            "claim": "Search interest indicates purchase intent",
            "confidence": 0.30 if trend_direction == "rising" else 0.20,
            "reason": f"Google Trends shows {trend_direction} interest (score: {interest_score}) but search behavior ≠ buying behavior.",
            "source": "trends_analysis",
            "evidence_gap": "Click-through rates on ads, landing page conversions, or purchase funnel data"
        })
        
        if trend_direction != "rising":
            unknowns.append({
                "claim": "Market is growing",
                "confidence": 0.25 if trend_direction == "stable" else 0.15,
                "reason": f"Trend direction is '{trend_direction}', not rising. May indicate mature or declining market.",
                "source": "trends_analysis",
                "evidence_gap": "Industry reports, TAM growth projections, or multi-year trend analysis"
            })
    else:
        unknowns.append({
            "claim": "Market has search demand",
            "confidence": 0.20,
            "reason": "Insufficient Google Trends data to assess market interest signals.",
            "source": "trends_analysis",
            "evidence_gap": "Paid ad campaign with $500+ spend to measure CTR and CPC"
        })
    
    # === COMPETITOR UNKNOWNS ===
    if competitor_data and not _is_insufficient_data(competitor_data):
        market_structure = competitor_data.get("market_structure", {})
        structure_type = market_structure.get("type", "unknown")
        structure_confidence = market_structure.get("confidence", 0.5)
        direct_count = len(competitor_data.get("direct_competitors", []))
        
        # Switching costs are always uncertain
        unknowns.append({
            "claim": "Users will switch from existing solutions",
            "confidence": 0.30,
            "reason": f"Market structure is '{structure_type}' with {direct_count} direct competitors. Switching costs unknown.",
            "source": "competitor_analysis",
            "evidence_gap": "User interviews about switching friction, exit barriers from incumbents"
        })
        
        # Differentiation viability
        if structure_type in ["consolidated", "monopolized"]:
            unknowns.append({
                "claim": "Differentiation strategy will be effective",
                "confidence": 0.25,
                "reason": f"'{structure_type}' market structure suggests strong incumbents. Differentiation claims untested.",
                "source": "competitor_analysis",
                "evidence_gap": "A/B test showing preference for differentiated feature, or niche user validation"
            })
        
        # Moat sustainability
        unknowns.append({
            "claim": "Competitive moat is sustainable",
            "confidence": 0.35,
            "reason": "No evidence of defensible advantage. Incumbents could replicate features if traction proven.",
            "source": "competitor_analysis",
            "evidence_gap": "Technical barriers, network effects, or exclusive partnerships"
        })
    else:
        unknowns.append({
            "claim": "Competitive landscape is understood",
            "confidence": 0.15,
            "reason": "Insufficient competitor data. May be missing key incumbents or alternatives.",
            "source": "competitor_analysis",
            "evidence_gap": "Deep competitive analysis with funding, features, and user interviews"
        })
    
    # === DIMENSION-BASED UNKNOWNS ===
    weak_dims = {k: v for k, v in dimension_scores.items() if v < 50}
    
    dimension_unknowns = {
        "market_demand": {
            "claim": "Sufficient market demand exists",
            "reason": "Market demand score is weak. Demand signals may be insufficient or misinterpreted.",
            "evidence_gap": "Cold outreach to 50+ target users, measure response rate"
        },
        "sentiment": {
            "claim": "Public sentiment will translate to adoption",
            "reason": "Sentiment analysis shows weak or mixed signals. Opinion ≠ behavior.",
            "evidence_gap": "Beta launch with activation tracking"
        },
        "competition": {
            "claim": "Competition level is manageable",
            "reason": "Competition score is concerning. May face stronger resistance than expected.",
            "evidence_gap": "Detailed win/loss analysis from competitor's customers"
        },
        "trend_momentum": {
            "claim": "Timing is right for market entry",
            "reason": "Trend momentum is weak. Market may not be ready or may be declining.",
            "evidence_gap": "Industry analyst reports, VC investment trends in category"
        },
        "feasibility": {
            "claim": "Solution is technically feasible",
            "reason": "Feasibility assessment is uncertain. Technical challenges may be underestimated.",
            "evidence_gap": "Technical prototype validation, key integration tests"
        },
        "economics": {
            "claim": "Unit economics are viable",
            "reason": "Economics score is weak. CAC, LTV, or margins may be problematic.",
            "evidence_gap": "Pricing experiments, cost modeling with real vendor quotes"
        }
    }
    
    for dim, score in weak_dims.items():
        if dim in dimension_unknowns:
            unknowns.append({
                "claim": dimension_unknowns[dim]["claim"],
                "confidence": max(0.15, score / 100 * 0.6),  # Scale confidence to score
                "reason": dimension_unknowns[dim]["reason"],
                "source": f"dimension_{dim}",
                "evidence_gap": dimension_unknowns[dim]["evidence_gap"]
            })
    
    # === CORE BUSINESS ASSUMPTIONS (ALWAYS UNCERTAIN) ===
    # These are ALWAYS unknown unless explicitly proven
    core_unknowns = [
        {
            "claim": "Revenue model is viable at scale",
            "confidence": 0.30,
            "reason": "No revenue data. Pricing assumptions untested.",
            "source": "business_model",
            "evidence_gap": "Pricing experiments with real payment collection"
        },
        {
            "claim": "Customer acquisition cost is sustainable",
            "confidence": 0.25,
            "reason": "No CAC data. Acquisition channels untested.",
            "source": "business_model",
            "evidence_gap": "Paid acquisition test with $1000+ spend"
        }
    ]
    
    # Add core unknowns if not already covered
    for cu in core_unknowns:
        if not any(u["claim"] == cu["claim"] for u in unknowns):
            unknowns.append(cu)
    
    # === ENSURE MINIMUM UNKNOWNS ===
    # If somehow we have fewer than 3, add fundamental business unknowns
    if len(unknowns) < 3:
        fallback_unknowns = [
            {
                "claim": "Target market segment is correctly identified",
                "confidence": 0.35,
                "reason": "Market segmentation based on assumptions, not validated interviews.",
                "source": "market_definition",
                "evidence_gap": "50+ customer discovery interviews with segment validation"
            },
            {
                "claim": "Problem is painful enough to drive action",
                "confidence": 0.30,
                "reason": "Pain point intensity not measured. May be 'nice to have' not 'must have'.",
                "source": "problem_validation",
                "evidence_gap": "Pain intensity scoring (1-10) from 30+ target users"
            },
            {
                "claim": "Team can execute on this vision",
                "confidence": 0.40,
                "reason": "Execution capability not assessed by this analysis.",
                "source": "execution_risk",
                "evidence_gap": "Track record evaluation, team capability assessment"
            }
        ]
        for fu in fallback_unknowns:
            if len(unknowns) < 3:
                unknowns.append(fu)
    
    # Sort by confidence (lowest first - most uncertain claims first)
    unknowns.sort(key=lambda x: x.get("confidence", 0.5))
    
    return unknowns[:10]  # Cap at 10 most uncertain claims


def _generate_kill_criteria(
    unknowns: List[Unknown],
    market_structure_type: str,
    dimension_scores: Dict[str, float],
    recommendation_decision: str
) -> List[KillCriterion]:
    """
    Generate explicit kill criteria from unknowns and weak dimensions.
    
    CORE PRINCIPLE: Analysis without the ability to kill is invalid.
    Every idea must be allowed to die. Every action must have a kill switch.
    
    REQUIREMENTS:
    - 2-5 kill criteria
    - At least one user-side kill
    - At least one supply-side kill
    - At least one willingness-to-pay kill (if monetized)
    
    INVALID CRITERIA (will NOT be generated):
    - "Validate demand" (not measurable)
    - "Test MVP" (no stop condition)
    - "Explore partnerships" (vague)
    """
    kill_criteria: List[KillCriterion] = []
    
    # === USER-SIDE KILL CRITERIA ===
    # Always include at least one user validation criterion
    user_unknowns = [u for u in unknowns if u.get("source") in ["reddit_sentiment", "dimension_market_demand", "dimension_sentiment"]]
    
    kill_criteria.append({
        "criterion": "If <15% of 50 surveyed target users express urgent need for this solution → stop",
        "category": "user_side",
        "linked_unknown": user_unknowns[0].get("claim", "Users need this solution") if user_unknowns else "Users need this solution",
        "test_cost": "cheap",
        "test_duration": "fast"
    })
    
    # User adoption criterion
    kill_criteria.append({
        "criterion": "If <20% of 30 beta users return after first week → stop",
        "category": "user_side",
        "linked_unknown": "Positive sentiment will convert to adoption",
        "test_cost": "moderate",
        "test_duration": "moderate"
    })
    
    # === WILLINGNESS-TO-PAY KILL CRITERIA ===
    # Critical for any monetized idea
    kill_criteria.append({
        "criterion": "If <5% of surveyed users offer to prepay or commit budget → stop",
        "category": "willingness_to_pay",
        "linked_unknown": "Users will pay for this solution",
        "test_cost": "cheap",
        "test_duration": "fast"
    })
    
    # === SUPPLY-SIDE KILL CRITERIA ===
    # Based on market structure
    if market_structure_type in ["consolidated", "monopolized"]:
        kill_criteria.append({
            "criterion": "If <3 users choose this over incumbent in blind comparison → stop",
            "category": "supply_side",
            "linked_unknown": "Differentiation strategy will be effective",
            "test_cost": "moderate",
            "test_duration": "moderate"
        })
    else:
        kill_criteria.append({
            "criterion": "If <10 potential partners/suppliers respond to outreach within 2 weeks → stop",
            "category": "supply_side",
            "linked_unknown": "Supply-side partners will participate",
            "test_cost": "cheap",
            "test_duration": "fast"
        })
    
    # === UNIT ECONOMICS KILL CRITERIA ===
    econ_score = dimension_scores.get("economics", 50)
    if econ_score < 60:
        kill_criteria.append({
            "criterion": "If CAC exceeds 3-month customer value in pilot → stop",
            "category": "unit_economics",
            "linked_unknown": "Unit economics are viable",
            "test_cost": "moderate",
            "test_duration": "moderate"
        })
    
    # === DECISION-SPECIFIC CRITERIA ===
    if recommendation_decision == "experiment":
        kill_criteria.append({
            "criterion": "If experiment budget ($500-$1000) depleted with no validated signal → stop",
            "category": "unit_economics",
            "linked_unknown": "Experiment will yield actionable data",
            "test_cost": "moderate",
            "test_duration": "moderate"
        })
    elif recommendation_decision == "wait":
        kill_criteria.append({
            "criterion": "If market signals remain weak after 3-month monitoring → stop",
            "category": "user_side",
            "linked_unknown": "Market timing will improve",
            "test_cost": "cheap",
            "test_duration": "slow"
        })
    elif recommendation_decision == "avoid":
        kill_criteria.append({
            "criterion": "If any of the above criteria fail within first 2 weeks of research → permanently stop",
            "category": "user_side",
            "linked_unknown": "Core assumptions are testable",
            "test_cost": "cheap",
            "test_duration": "fast"
        })
    
    # Ensure minimum 2 criteria
    if len(kill_criteria) < 2:
        kill_criteria.append({
            "criterion": "If <10 users complete onboarding in first week of launch → stop",
            "category": "user_side",
            "linked_unknown": "Users will activate",
            "test_cost": "moderate",
            "test_duration": "fast"
        })
    
    return kill_criteria[:5]  # Cap at 5 criteria


def _generate_conditions(
    decision: str,
    risk_factors: List[str],
    weaknesses: List[str],
    dimension_scores: Dict[str, float],
    market_structure_type: str,
    insufficient_nodes: List[str]
) -> List[RecommendationCondition]:
    """
    Generate falsifiable conditions from risk factors and weak dimensions.
    
    RULES:
    - Each condition MUST be falsifiable (can be proven true/false)
    - Each condition MUST be testable (has concrete verification method)
    - Each condition MUST be linked to a specific risk
    - Minimum 2 conditions required
    
    UNACCEPTABLE conditions (will NOT be generated):
    - "If marketing is good"
    - "If users like it"
    """
    conditions: List[RecommendationCondition] = []
    
    # Map weak dimensions to specific test conditions
    weak_dims = [k for k, v in dimension_scores.items() if v < 50]
    
    dimension_conditions = {
        "market_demand": {
            "condition": "If target users actively seek this solution within 30 days of outreach",
            "test_method": "Cold outreach to 50 target users, measure response rate ≥15%",
            "linked_risk": "demand_validation"
        },
        "sentiment": {
            "condition": "If early users rate product satisfaction ≥4/5 after 2-week trial",
            "test_method": "NPS survey of 30+ beta users",
            "linked_risk": "product_market_fit"
        },
        "competition": {
            "condition": "If differentiation is validated by users choosing this over alternatives",
            "test_method": "A/B test with competitor comparison, measure preference ≥60%",
            "linked_risk": "competitive_positioning"
        },
        "trend_momentum": {
            "condition": "If search interest grows ≥10% month-over-month for 3 months",
            "test_method": "Monitor Google Trends weekly, validate trajectory",
            "linked_risk": "market_timing"
        },
        "feasibility": {
            "condition": "If core technical functionality delivers in ≤3 month runway",
            "test_method": "Build MVP, validate key feature works as expected",
            "linked_risk": "execution_risk"
        },
        "economics": {
            "condition": "If unit economics show CAC < LTV/3 in pilot phase",
            "test_method": "Track acquisition cost and retention for 50 paying users",
            "linked_risk": "business_model_viability"
        }
    }
    
    # Add conditions for weak dimensions first
    for dim in weak_dims[:2]:
        if dim in dimension_conditions:
            conditions.append(dimension_conditions[dim])
    
    # Add conditions based on risk factors (from LLM)
    risk_condition_templates = {
        "cac": {
            "condition": "If customer acquisition cost remains below $50 for 100 users",
            "test_method": "Track marketing spend per conversion in 4-week sprint",
            "linked_risk": "customer_acquisition"
        },
        "churn": {
            "condition": "If monthly churn rate stays below 5% after 3 months",
            "test_method": "Cohort analysis of first 100 users",
            "linked_risk": "retention"
        },
        "funding": {
            "condition": "If bootstrappable to $10K MRR without external funding",
            "test_method": "Financial projection validated by 6-month runway",
            "linked_risk": "capital_dependency"
        },
        "market": {
            "condition": "If market size exceeds $100M total addressable market",
            "test_method": "Bottom-up TAM calculation with 3 data sources",
            "linked_risk": "market_size"
        },
        "competition": {
            "condition": "If no incumbent launches identical feature within 6 months",
            "test_method": "Competitive monitoring, pivot trigger if matched",
            "linked_risk": "competitive_response"
        },
        "technical": {
            "condition": "If core technology achieves target performance in testing",
            "test_method": "Technical benchmark against requirements spec",
            "linked_risk": "technical_risk"
        }
    }
    
    for risk in risk_factors[:3]:
        risk_lower = risk.lower()
        for key, template in risk_condition_templates.items():
            if key in risk_lower and template not in conditions:
                conditions.append(template)
                break
    
    # Add conditions for market structure
    structure_conditions = {
        "monopolized": {
            "condition": "If dominant player's weakness creates entry window within 12 months",
            "test_method": "Track dominant player for pricing/feature gaps",
            "linked_risk": "market_entry_barrier"
        },
        "consolidated": {
            "condition": "If underserved niche segment responds to differentiated offering",
            "test_method": "Survey 100 users in target niche, measure pain intensity ≥8/10",
            "linked_risk": "differentiation"
        },
        "emerging": {
            "condition": "If market infrastructure matures to support the solution",
            "test_method": "Track 3 enabling technology adoption rates monthly",
            "linked_risk": "market_readiness"
        }
    }
    
    if market_structure_type in structure_conditions:
        conditions.append(structure_conditions[market_structure_type])
    
    # Add conditions for insufficient data
    if insufficient_nodes:
        data_conditions = {
            "reddit": {
                "condition": "If community validation shows demand through 50+ engaged discussions",
                "test_method": "Post in 5 relevant communities, measure engagement",
                "linked_risk": "community_validation"
            },
            "trends": {
                "condition": "If search demand validates market interest at scale",
                "test_method": "Run Google Ads test with $500, measure CTR ≥2%",
                "linked_risk": "search_demand"
            },
            "competitors": {
                "condition": "If competitive landscape allows sustainable differentiation",
                "test_method": "Deep competitive analysis of top 5 players",
                "linked_risk": "competitive_clarity"
            }
        }
        for node in insufficient_nodes[:2]:
            if node in data_conditions:
                conditions.append(data_conditions[node])
    
    # Ensure minimum 2 conditions
    if len(conditions) < 2:
        # Add generic but still falsifiable conditions
        defaults = [
            {
                "condition": "If 10 users complete onboarding and use product 3+ times in first week",
                "test_method": "Track activation metrics in beta launch",
                "linked_risk": "activation"
            },
            {
                "condition": "If at least 1 user offers to pay before product is finished",
                "test_method": "Pre-sell during customer discovery",
                "linked_risk": "willingness_to_pay"
            }
        ]
        for d in defaults:
            if len(conditions) < 2:
                conditions.append(d)
    
    return conditions[:5]  # Cap at 5 conditions


def _determine_recommendation(
    overall_score: float,
    confidence: float,
    insufficient_count: int,
    dimension_scores: Dict[str, float],
    has_known_competitors: bool,
    kill_switch_triggered: bool = False,
    kill_switch_reason: Optional[str] = None,
    risk_factors: List[str] = None,
    weaknesses: List[str] = None,
    market_structure_type: str = "unknown",
    insufficient_nodes: List[str] = None
) -> ConditionalRecommendation:
    """
    Generate conditional recommendation with falsifiable conditions.
    
    DECISION MAPPING (STRICT):
    
    1. conditional_go
       - Core signals are positive (score ≥65, confidence ≥0.6)
       - Success depends on 1-3 falsifiable assumptions
       - Suitable for founders ready to validate quickly
    
    2. experiment
       - Signals are mixed or uncertain (score 45-65 OR confidence 0.4-0.6)
       - Small, cheap tests required before commitment
       - No scaling implied
    
    3. wait
       - Market or infrastructure not ready (emerging market, low interest)
       - Timing risk dominates idea risk
    
    4. avoid
       - Kill switch triggered OR score <40 OR 2+ critical dimension failures
       - Structural barriers are high
       - Key assumptions are unlikely or untestable
    
    REMOVED (binary verdicts are INVALID):
    - "go" / "no_go" / "strong_go" / "caution" / "pivot" / "inconclusive"
    """
    risk_factors = risk_factors or []
    weaknesses = weaknesses or []
    insufficient_nodes = insufficient_nodes or []
    
    # === DECISION LOGIC ===
    
    # Check for blocking conditions first
    low_dimensions = [k for k, v in dimension_scores.items() if v < 30]
    
    # === AVOID: Structural barriers too high ===
    if kill_switch_triggered:
        decision = "avoid"
        rationale = f"Structural barrier: {kill_switch_reason}. Market is dominated by well-funded incumbents with high switching costs. Conditions describe what would need to change for reconsideration."
    
    elif len(low_dimensions) >= 2:
        decision = "avoid"
        rationale = f"Critical failures in {', '.join(low_dimensions)}. Multiple structural barriers make success unlikely. Conditions describe minimum thresholds that would change this assessment."
    
    elif overall_score < 40:
        decision = "avoid"
        rationale = f"Overall score {overall_score:.0f}/100 indicates high-risk profile. Key assumptions appear unlikely or untestable based on available data."
    
    # === WAIT: Timing risk dominates ===
    elif market_structure_type == "emerging" and dimension_scores.get("trend_momentum", 50) < 40:
        decision = "wait"
        rationale = f"Market structure is 'emerging' but momentum signals are weak. Timing risk dominates idea risk. Wait for market infrastructure to mature before committing resources."
    
    elif confidence < 0.4 and insufficient_count >= 2:
        decision = "wait"
        rationale = f"Confidence {confidence:.2f} with {insufficient_count} data gaps. Insufficient signal strength to commit. Wait until core market signals are clearer."
    
    # === EXPERIMENT: Mixed signals require validation ===
    elif 40 <= overall_score < 65 or (0.4 <= confidence < 0.6):
        decision = "experiment"
        rationale = f"Score {overall_score:.0f}/100 with confidence {confidence:.2f} indicates mixed signals. Run small, cheap experiments before full commitment. No scaling until conditions are validated."
    
    elif insufficient_count >= 1 and overall_score < 75:
        decision = "experiment"
        rationale = f"Promising score {overall_score:.0f}/100 but {insufficient_count} data source(s) missing. Validate assumptions through targeted experiments before scaling."
    
    # === CONDITIONAL_GO: Positive signals with assumptions ===
    else:
        decision = "conditional_go"
        if overall_score >= 75 and confidence >= 0.7:
            rationale = f"Strong signals: score {overall_score:.0f}/100, confidence {confidence:.2f}. Core assumptions are positive. Proceed with validation focus on the following conditions."
        else:
            rationale = f"Positive signals: score {overall_score:.0f}/100, confidence {confidence:.2f}. Success depends on validating 1-3 key assumptions. Suitable for founders ready to execute validation quickly."
    
    # Generate conditions based on decision and risk factors
    conditions = _generate_conditions(
        decision=decision,
        risk_factors=risk_factors,
        weaknesses=weaknesses,
        dimension_scores=dimension_scores,
        market_structure_type=market_structure_type,
        insufficient_nodes=insufficient_nodes
    )
    
    return {
        "decision": decision,
        "conditions": conditions,
        "rationale": rationale
    }


async def judge_logic(state: ValidationState) -> Dict[str, Any]:
    """
    Aggregate upstream data and produce final verdict.

    Fully deterministic — no LLM calls, no external API calls.
    """
    timer = StepTimer("judge")

    idea_input = state.get("idea_input", "")
    processing_errors = list(state.get("processing_errors", []))

    reddit_data = state.get("reddit_sentiment")
    trends_data = state.get("trends_data")
    competitor_data = state.get("competitor_analysis")

    if not idea_input:
        return {
            "final_verdict": _insufficient_verdict(["no_idea_provided"]),
            "processing_errors": processing_errors + ["Judge: No idea provided"]
        }
    
    # Identify insufficient data nodes
    insufficient_nodes = []
    if _is_insufficient_data(reddit_data):
        insufficient_nodes.append("reddit")
    if _is_insufficient_data(trends_data):
        insufficient_nodes.append("trends")
    if _is_insufficient_data(competitor_data):
        insufficient_nodes.append("competitors")
    
    # Check for known competitors
    has_known_competitors = _has_known_competitors(competitor_data)
    
    # --- DOMAIN CONSISTENCY CHECK ---
    # Penalize if multiple nodes report high noise or semantic mismatch
    semantic_warnings = []
    semantic_penalty_factor = 1.0
    
    for node_name, data in [("reddit", reddit_data), ("trends", trends_data), ("competitors", competitor_data)]:
        if data:
            node_warnings = data.get("quality", {}).get("warnings", [])
            for w in node_warnings:
                if w in ["high_noise_ratio", "many_off_domain_results", "high_noise_in_related_queries"]:
                    semantic_warnings.append(f"{node_name}: {w}")
                    
    if len(semantic_warnings) >= 2:
        processing_errors.append("Domain Consistency: Multiple nodes reported high noise/semantic filtering.")
        semantic_penalty_factor = 0.8
        
    # Calculate dimension scores
    async with timer.async_step("dimension_scoring"):
        dimension_scores: Dict[str, float] = {}
        dimension_confidences: Dict[str, float] = {}
        score_breakdown: Dict[str, Dict] = {}
        
        # Market Demand
        md_score, md_conf, md_rationale = _calculate_market_demand_score(trends_data, reddit_data)
        dimension_scores["market_demand"] = md_score
        dimension_confidences["market_demand"] = md_conf
        score_breakdown["market_demand"] = {
            "score": md_score, "weight": 0.20, "confidence": md_conf, "rationale": md_rationale
        }
        
        # Sentiment
        sent_score, sent_conf, sent_rationale = _calculate_sentiment_score(reddit_data)
        dimension_scores["sentiment"] = sent_score
        dimension_confidences["sentiment"] = sent_conf
        score_breakdown["sentiment"] = {
            "score": sent_score, "weight": 0.15, "confidence": sent_conf, "rationale": sent_rationale
        }
        
        # Competition
        comp_score, comp_conf, comp_rationale = _calculate_competition_score(competitor_data)
        dimension_scores["competition"] = comp_score
        dimension_confidences["competition"] = comp_conf
        score_breakdown["competition"] = {
            "score": comp_score, "weight": 0.20, "confidence": comp_conf, "rationale": comp_rationale
        }
        
        # Trend Momentum
        trend_score, trend_conf, trend_rationale = _calculate_trend_momentum_score(trends_data)
        dimension_scores["trend_momentum"] = trend_score
        dimension_confidences["trend_momentum"] = trend_conf
        score_breakdown["trend_momentum"] = {
            "score": trend_score, "weight": 0.15, "confidence": trend_conf, "rationale": trend_rationale
        }
    
    # Deterministic assessment (replaces LLM)
    async with timer.async_step("deterministic_assessment"):
        deterministic_result = _deterministic_assessment(
            dimension_scores=dimension_scores,
            insufficient_nodes=insufficient_nodes,
            market_structure_type=(
                competitor_data.get("market_structure", {}).get("type", "unknown")
                if competitor_data else "unknown"
            ),
            has_known_competitors=has_known_competitors,
        )

    # Feasibility
    feas_score = deterministic_result.get("feasibility_score", 50)
    feas_conf = 0.6 if not insufficient_nodes else 0.4
    dimension_scores["feasibility"] = feas_score
    dimension_confidences["feasibility"] = feas_conf
    score_breakdown["feasibility"] = {
        "score": feas_score, "weight": 0.15, "confidence": feas_conf, "rationale": "Deterministic scoring engine"
    }

    # Economics
    econ_score = deterministic_result.get("economics_score", 50)
    econ_conf = 0.6 if not insufficient_nodes else 0.4
    dimension_scores["economics"] = econ_score
    dimension_confidences["economics"] = econ_conf
    score_breakdown["economics"] = {
        "score": econ_score, "weight": 0.15, "confidence": econ_conf, "rationale": "Deterministic scoring engine"
    }
    
    # Calculate weighted overall score
    total_weight = sum(SCORING_DIMENSIONS[d]["weight"] for d in dimension_scores)
    weighted_sum = sum(dimension_scores[d] * SCORING_DIMENSIONS[d]["weight"] for d in dimension_scores)
    overall_score = int(weighted_sum / total_weight) if total_weight > 0 else 50
    overall_score = max(0, min(100, overall_score))
    
    # Calculate overall confidence
    weighted_conf_sum = sum(dimension_confidences[d] * SCORING_DIMENSIONS[d]["weight"] for d in dimension_confidences)
    overall_confidence = weighted_conf_sum / total_weight if total_weight > 0 else 0.5
    
    # Penalize for insufficient data
    if insufficient_nodes:
        overall_confidence *= (1 - 0.15 * len(insufficient_nodes))
        
    # Apply semantic penalty to confidence
    if semantic_warnings:
        overall_confidence *= 0.9
        
    overall_confidence = max(0.1, min(0.95, overall_confidence))
    
    # Calculate confidence interval
    conf_lower, conf_upper = _calculate_confidence_interval(
        overall_score, overall_confidence, len(insufficient_nodes)
    )
    
    # Determine recommendation (will be recalculated with kill switch later)
    # First pass without kill switch info - used for warnings only
    # Final recommendation is calculated after kill switch check
    
    # Build warnings
    warnings = []
    for node in insufficient_nodes:
        warnings.append(f"{node}_data_insufficient")
    if overall_confidence < 0.4:
        warnings.append("low_confidence")
    if conf_upper - conf_lower > 35:
        warnings.append("wide_confidence_interval")
    # NOTE: market_saturation_adjusted warning removed - using market_structure now
    
    quality: QualityMetrics = {
        "data_volume": sum([
            (reddit_data.get("quality", {}).get("data_volume", 0) if reddit_data else 0),
            (trends_data.get("quality", {}).get("data_volume", 0) if trends_data else 0),
            (competitor_data.get("quality", {}).get("data_volume", 0) if competitor_data else 0),
        ]),
        "relevance_mean": round(statistics.mean([
            reddit_data.get("quality", {}).get("relevance_mean", 0.5) if reddit_data else 0.5,
            trends_data.get("quality", {}).get("relevance_mean", 0.5) if trends_data else 0.5,
            competitor_data.get("quality", {}).get("relevance_mean", 0.5) if competitor_data else 0.5,
        ]), 3),
        "confidence": round(overall_confidence, 3),
        "warnings": warnings
    }
    
    # =========================================================================
    # EPISTEMIC OUTPUT: Build rigorous output schema
    # =========================================================================
    
    # Check kill switch
    direct_count = len(competitor_data.get("direct_competitors", [])) if competitor_data else 0
    total_funding_str = competitor_data.get("total_funding_in_space", "Unknown") if competitor_data else "Unknown"
    total_funding_millions = _parse_funding_to_millions(total_funding_str)
    
    # Use weighted pressure if available, else estimate
    weighted_pressure = 0.0
    if competitor_data:
        # Estimate from direct count and funding
        weighted_pressure = direct_count * 0.5 + (total_funding_millions / 50) * 0.3
    
    kill_switch_triggered, kill_switch_reason = _check_kill_switch(
        direct_count, total_funding_millions, weighted_pressure
    )
    
    # Check for contradictions
    has_contradictions, contradictions = _detect_contradictions(
        reddit_data, trends_data, competitor_data
    )
    
    # Build epistemic_status
    data_quality_warning = None
    if len(insufficient_nodes) >= 2:
        data_quality_warning = f"Missing data from: {', '.join(insufficient_nodes)}"
    elif overall_confidence < CONFIDENCE_THRESHOLD:
        data_quality_warning = f"Confidence {overall_confidence:.2f} below threshold"
    
    epistemic_status: EpistemicStatus = {
        "confidence_level": round(overall_confidence, 3),
        "data_quality_warning": data_quality_warning,
        "contradiction_flag": has_contradictions,
        "contradictions": contradictions,
        "insufficient_signals": insufficient_nodes
    }
    
    # Build market_reality using MARKET STRUCTURE (not saturation)
    verified_competitors = []
    market_structure_type = "unknown"
    if competitor_data:
        for c in competitor_data.get("direct_competitors", [])[:10]:
            verified_competitors.append(c.get("name", "Unknown"))
        # Get market structure type
        market_structure = competitor_data.get("market_structure", {})
        market_structure_type = market_structure.get("type", "unknown")
    
    # Determine barrier to entry based on STRUCTURE, not raw count
    if market_structure_type == "monopolized":
        barrier_to_entry = "High"
    elif market_structure_type == "consolidated":
        barrier_to_entry = "Medium"
    elif market_structure_type in ["fragmented", "emerging"]:
        barrier_to_entry = "Low"
    else:
        barrier_to_entry = "Medium" if direct_count >= 2 else "Low"
    
    market_reality: MarketReality = {
        "verified_competitors": verified_competitors,
        "verified_competitor_count": direct_count,
        "noise_discarded_count": competitor_data.get("non_scoring_competitors_count", 0) if competitor_data else 0,
        "weighted_pressure_score": round(weighted_pressure, 2),
        "market_structure_type": market_structure_type,  # REPLACED saturation_level
        "barrier_to_entry": barrier_to_entry,
        "total_verified_funding": total_funding_str,
        "dominant_players": verified_competitors[:3]
    }

    
    # Build falsification_test (adversarial analysis)
    falsification_test: FalsificationTest = {
        "killer_feature_missing": deterministic_result.get("weaknesses", ["Unknown"])[0] if deterministic_result.get("weaknesses") else "Unknown",
        "why_this_might_fail": deterministic_result.get("risk_factors", ["Unknown"])[0] if deterministic_result.get("risk_factors") else "Unknown",
        "adversarial_concerns": deterministic_result.get("risk_factors", []),
        "market_timing_risk": "crowded" if kill_switch_triggered else ("late" if direct_count >= 3 else "viable")
    }
    
    # Calculate recommendation with all signals including kill switch
    recommendation = _determine_recommendation(
        overall_score=overall_score,
        confidence=overall_confidence,
        insufficient_count=len(insufficient_nodes),
        dimension_scores=dimension_scores,
        has_known_competitors=has_known_competitors,
        kill_switch_triggered=kill_switch_triggered,
        kill_switch_reason=kill_switch_reason,
        risk_factors=deterministic_result.get("risk_factors", []),
        weaknesses=deterministic_result.get("weaknesses", []),
        market_structure_type=market_structure_type,
        insufficient_nodes=insufficient_nodes
    )

    # === EXTRACT UNKNOWNS (MANDATORY) ===
    unknowns = _extract_unknowns(
        reddit_data=reddit_data,
        trends_data=trends_data,
        competitor_data=competitor_data,
        dimension_scores=dimension_scores,
        insufficient_nodes=insufficient_nodes
    )
    
    # === CONFIDENCE PENALTY FOR UNKNOWNS ===
    # More unknowns = lower confidence (epistemic honesty)
    unknown_count = len(unknowns)
    avg_unknown_confidence = sum(u.get("confidence", 0.5) for u in unknowns) / max(1, unknown_count)
    
    # Apply penalty: each low-confidence unknown reduces overall confidence
    low_confidence_unknowns = [u for u in unknowns if u.get("confidence", 0.5) < 0.35]
    unknown_penalty = len(low_confidence_unknowns) * 0.03
    overall_confidence = max(0.1, overall_confidence - unknown_penalty)
    
    # === GENERATE KILL CRITERIA (MANDATORY) ===
    # Replaces generic action_items with explicit stop conditions
    kill_criteria = _generate_kill_criteria(
        unknowns=unknowns,
        market_structure_type=market_structure_type,
        dimension_scores=dimension_scores,
        recommendation_decision=recommendation.get("decision", "experiment")
    )
    
    # === CONFIDENCE ADJUSTMENT FOR TESTABILITY ===
    # Easy/cheap tests → confidence boost
    # Expensive/slow tests → confidence penalty
    cheap_fast_tests = sum(1 for k in kill_criteria if k.get("test_cost") == "cheap" and k.get("test_duration") == "fast")
    expensive_slow_tests = sum(1 for k in kill_criteria if k.get("test_cost") == "expensive" or k.get("test_duration") == "slow")
    
    testability_adjustment = (cheap_fast_tests * 0.02) - (expensive_slow_tests * 0.03)
    overall_confidence = max(0.1, min(0.95, overall_confidence + testability_adjustment))
    
    final_verdict: FinalVerdict = {
        # Core assessment
        "overall_score": overall_score,
        "recommendation": recommendation,  # ConditionalRecommendation dict
        "confidence": round(overall_confidence, 2),
        "summary": deterministic_result.get("summary", "Analysis complete."),
        "strengths": deterministic_result.get("strengths", []),
        "weaknesses": deterministic_result.get("weaknesses", []),
        "risk_factors": deterministic_result.get("risk_factors", []),
        
        # MANDATORY: Epistemic uncertainty layer
        "unknowns": unknowns,  # Never empty - surfaces all uncertain claims
        
        # MANDATORY: Kill criteria (replaces action_items)
        "kill_criteria": kill_criteria,  # Explicit stop conditions
        
        # Epistemic rigour fields
        "epistemic_status": epistemic_status,
        "market_reality": market_reality,
        "falsification_test": falsification_test,
        "kill_switch_triggered": kill_switch_triggered,
        "kill_switch_reason": kill_switch_reason,
        
        "quality": quality
    }
    
    timer.summary()
    return {"final_verdict": final_verdict}


def _insufficient_verdict(warnings: List[str]) -> FinalVerdict:
    """Generate insufficient data verdict with wait recommendation."""
    return {
        "overall_score": 0,
        "recommendation": {
            "decision": "wait",
            "conditions": [
                {
                    "condition": "If sufficient market data can be gathered within 2 weeks",
                    "test_method": "Run targeted research with Reddit API, Google Trends, and competitor analysis",
                    "linked_risk": "data_availability"
                },
                {
                    "condition": "If 10+ relevant community discussions can be found",
                    "test_method": "Search relevant subreddits and forums manually",
                    "linked_risk": "community_existence"
                }
            ],
            "rationale": "Unable to assess due to insufficient data. Wait until core market signals are available before committing resources."
        },
        "confidence": 0.0,
        "summary": "Unable to complete assessment due to insufficient data.",
        "strengths": [],
        "weaknesses": ["Insufficient data for analysis"],
        "risk_factors": ["Analysis incomplete"],
        # MANDATORY: Unknowns are NEVER empty
        "unknowns": [
            {
                "claim": "Market demand exists for this solution",
                "confidence": 0.10,
                "reason": "No data available to assess demand. Analysis failed to gather sufficient signals.",
                "source": "data_collection",
                "evidence_gap": "Reddit sentiment analysis, Google Trends data, or direct user interviews"
            },
            {
                "claim": "Competitive landscape is favorable",
                "confidence": 0.10,
                "reason": "No competitor data available. Unknown number and strength of alternatives.",
                "source": "data_collection",
                "evidence_gap": "Competitor analysis from search results and funding databases"
            },
            {
                "claim": "Timing is appropriate for market entry",
                "confidence": 0.15,
                "reason": "No trend data available. Unable to assess market trajectory.",
                "source": "data_collection",
                "evidence_gap": "Google Trends analysis or industry reports"
            }
        ],
        # MANDATORY: Kill criteria (replaces action_items)
        "kill_criteria": [
            {
                "criterion": "If <10 relevant Reddit posts found within 1 week of manual search → stop",
                "category": "user_side",
                "linked_unknown": "Market demand exists for this solution",
                "test_cost": "cheap",
                "test_duration": "fast"
            },
            {
                "criterion": "If Google Trends shows <20 interest score for core keywords → stop",
                "category": "user_side",
                "linked_unknown": "Timing is appropriate for market entry",
                "test_cost": "cheap",
                "test_duration": "fast"
            },
            {
                "criterion": "If <3 direct competitors can be identified → reassess market existence",
                "category": "supply_side",
                "linked_unknown": "Competitive landscape is favorable",
                "test_cost": "cheap",
                "test_duration": "fast"
            }
        ],
        "quality": {
            "data_volume": 0,
            "relevance_mean": 0.0,
            "confidence": 0.0,
            "warnings": warnings
        }
    }
