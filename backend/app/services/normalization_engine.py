"""Signal Normalization Engine.

Converts heterogeneous raw signals from all upstream agents into
comparable 0-100 normalized values.

Rules
-----
- NO API calls
- NO DB writes
- NO LLMs
- NO scoring or weighting
- Pure math + clamping
- Fully deterministic
"""

from __future__ import annotations

from ..models.idea import Idea
from ..schemas.problem_intensity_schema import ProblemIntensitySignals
from ..schemas.trend_schema import TrendDemandSignals
from ..schemas.competitor_schema import CompetitorSignals
from ..schemas.normalized_schema import NormalizedSignals, NormalizationExplanation

def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp *value* to [lo, hi].  Treats None as 0."""
    if value is None:
        return lo
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Missing-data defaults
# ---------------------------------------------------------------------------
_MISSING_SIGNAL_DEFAULT = 40.0   # No signal = no certainty, neutral floor
_LOW_CONFIDENCE_CAP = 50.0       # Missing trend data caps market signals


def _growth_rate_to_score(raw_growth: float) -> float:
    """Convert a raw 5-year growth rate to a 0-100 score using tiered ranges.

    Tiered mapping (prevents any-positive-growth → 100):
      >= 0.20 (20%)  → 80  (hard cap — Google Trends growth ≠ real CAGR)
      0.10 – 0.20    → 65–80
      0.03 – 0.10    → 50–65
      0.00 – 0.03    → 35–50
      < 0 (decline)  → 10–20
      missing (0.0)  → 40 (handled by caller)

    NOTE: Google Trends growth rates can reach 2.0 (200%) which is NOT
    real market CAGR. We hard-cap at 80 for ≥20% to prevent inflation.
    """
    if raw_growth >= 0.20:
        # Hard cap at 80 — Google Trends ≠ real CAGR
        print(f"📊 [MARKET] Growth rate {raw_growth*100:.1f}% → capped score 80 (trends ≠ CAGR)")
        return 80.0
    elif raw_growth >= 0.10:
        return _clamp(65.0 + (raw_growth - 0.10) / 0.10 * 15.0)            # 65–80
    elif raw_growth >= 0.03:
        return _clamp(50.0 + (raw_growth - 0.03) / 0.07 * 15.0)            # 50–65
    elif raw_growth > 0:
        return _clamp(35.0 + raw_growth / 0.03 * 15.0)                     # 35–50
    elif raw_growth == 0:
        print(f"📉 [MARKET] Missing CAGR → confidence downgraded")
        return _MISSING_SIGNAL_DEFAULT  # No data → neutral
    else:
        # Negative growth (decline)
        return _clamp(10.0 + max(raw_growth + 1.0, 0.0) * 10.0)            # 10–20


def normalize_signals(
    problem: ProblemIntensitySignals,
    trend: TrendDemandSignals,
    competitor: CompetitorSignals,
    idea: Idea,
) -> NormalizedSignals:
    """Normalize all raw agent signals to a common 0-100 scale.

    Parameters
    ----------
    problem : ProblemIntensitySignals
        Pre-computed problem intensity signals (Tavily + SerpAPI, no Reddit).
    trend : TrendDemandSignals
    competitor : CompetitorSignals
    idea : Idea
        The ORM idea instance providing tech_complexity and regulatory_risk.

    Returns
    -------
    NormalizedSignals
        Every field is a float clamped between 0 and 100, plus a
        ``normalization_explanations`` dict with per-signal metadata.
    """
    trend_available = trend.trend_data_available

    # 1. pain_intensity — directly from Problem Intensity Agent (already 0-100)
    raw_pain = problem.problem_intensity_score
    pain_intensity = _clamp(raw_pain)
    print(f"📊 [Normalization] Pain intensity: {pain_intensity} (from Problem Intensity Agent, confidence={problem.confidence_level})")

    # 2. demand_strength  (trend.demand_strength_score is 0-1)
    raw_demand = trend.demand_strength_score
    if not trend_available:
        demand_strength = _MISSING_SIGNAL_DEFAULT
        print(f"📊 [Normalization] Demand strength: no trend data → default {_MISSING_SIGNAL_DEFAULT}")
    else:
        demand_strength = _clamp(raw_demand * 100)

    # 3. market_growth — tiered mapping (replaces soft saturation that inflated to 100)
    raw_growth = trend.growth_rate_5y
    if not trend_available:
        market_growth = _MISSING_SIGNAL_DEFAULT
        print(f"📈 [Normalization] Market growth: no trend data → default {_MISSING_SIGNAL_DEFAULT}")
    else:
        market_growth = _growth_rate_to_score(raw_growth)

    print(f"📈 [Normalization] Raw growth: {raw_growth}")
    print(f"📈 [Normalization] Normalized market growth: {round(market_growth, 2)}")

    # 4. market_momentum  (trend.momentum_score is 0-1)
    raw_momentum = trend.momentum_score
    if not trend_available:
        market_momentum = _MISSING_SIGNAL_DEFAULT
        print(f"📊 [Normalization] Market momentum: no trend data → default {_MISSING_SIGNAL_DEFAULT}")
    else:
        market_momentum = _clamp(raw_momentum * 100)

    # ── Low-confidence cap: if trend data is missing, cap market signals ──
    if not trend_available:
        demand_strength = min(demand_strength, _LOW_CONFIDENCE_CAP)
        market_growth = min(market_growth, _LOW_CONFIDENCE_CAP)
        market_momentum = min(market_momentum, _LOW_CONFIDENCE_CAP)
        print(f"📥 [Normalization] Trend data MISSING → capping market signals at {_LOW_CONFIDENCE_CAP}")

    # 5. competition_density  (competitor.competitor_density_score is 0-1)
    raw_comp_density = competitor.competitor_density_score
    competition_density = _clamp(raw_comp_density * 100)

    # 6. feature_overlap  (competitor.feature_overlap_score is 0-1)
    raw_feat_overlap = competitor.feature_overlap_score
    feature_overlap = _clamp(raw_feat_overlap * 100)

    # 7. tech_complexity_score  (idea.tech_complexity is 0-1)
    raw_tech = idea.tech_complexity
    tech_complexity_score = _clamp(raw_tech * 100)

    # 8. regulatory_risk_score  (idea.regulatory_risk is 0-1)
    raw_reg = idea.regulatory_risk
    regulatory_risk_score = _clamp(raw_reg * 100)

    # ------------------------------------------------------------------ #
    #  Build normalization explanations                                    #
    # ------------------------------------------------------------------ #
    explanations = {
        "pain_intensity": NormalizationExplanation(
            raw_value=round(raw_pain, 4),
            formula="direct pass-through from Problem Intensity Agent (Tavily + SerpAPI)",
            description=(
                f"Problem intensity from search intent, evidence, complaints, and manual cost. "
                f"Confidence: {problem.confidence_level}. {problem.explanation[:120]}"
            ),
        ),
        "demand_strength": NormalizationExplanation(
            raw_value=round(raw_demand, 4),
            formula="normalized = raw × 100",
            description="Derived from search demand proxies (e.g. total results / keyword volume).",
        ),
        "market_growth": NormalizationExplanation(
            raw_value=round(raw_growth, 4),
            formula="tiered: >=20%→80, 10-20%→65, 3-10%→50, <3%→35, missing→40, decline→0-20",
            description=(
                "Market growth uses tiered ranges to prevent score inflation. "
                "Missing data defaults to 40 (neutral). No trend data caps at 50."
            ),
        ),
        "market_momentum": NormalizationExplanation(
            raw_value=round(raw_momentum, 4),
            formula="normalized = raw × 100",
            description="Recent 6-month acceleration relative to prior 6 months, scaled to 0-100.",
        ),
        "competition_density": NormalizationExplanation(
            raw_value=round(raw_comp_density, 4),
            formula="normalized = raw × 100",
            description="Market crowding score (0-1) based on competitor count, scaled to 0-100.",
        ),
        "feature_overlap": NormalizationExplanation(
            raw_value=round(raw_feat_overlap, 4),
            formula="normalized = raw × 100",
            description="Jaccard similarity of competitor features vs. your industry keywords, scaled to 0-100.",
        ),
        "tech_complexity_score": NormalizationExplanation(
            raw_value=round(raw_tech, 4),
            formula="normalized = raw × 100",
            description="User-provided technical complexity (0-1) scaled to 0-100.",
        ),
        "regulatory_risk_score": NormalizationExplanation(
            raw_value=round(raw_reg, 4),
            formula="normalized = raw × 100",
            description="User-provided regulatory risk (0-1) scaled to 0-100.",
        ),
    }

    return NormalizedSignals(
        pain_intensity=round(pain_intensity, 2),
        demand_strength=round(demand_strength, 2),
        market_growth=round(market_growth, 2),
        market_momentum=round(market_momentum, 2),
        competition_density=round(competition_density, 2),
        feature_overlap=round(feature_overlap, 2),
        tech_complexity_score=round(tech_complexity_score, 2),
        regulatory_risk_score=round(regulatory_risk_score, 2),
        normalization_explanations=explanations,
    )
