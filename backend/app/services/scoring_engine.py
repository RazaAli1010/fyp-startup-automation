"""Deterministic Scoring Engine.

Converts normalized 0-100 signals into module scores and a final
viability score using fixed mathematical formulas.

Rules
-----
- NO API calls
- NO DB writes
- NO LLMs
- NO heuristics beyond the explicit formulas
- NO funding data — scoring is funding-free
- Pure deterministic math
"""

from __future__ import annotations

from ..schemas.normalized_schema import NormalizedSignals
from ..schemas.score_schema import ModuleScores


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp *value* to [lo, hi]."""
    return max(lo, min(hi, value))


def compute_scores(normalized: NormalizedSignals) -> ModuleScores:
    """Compute module scores and final viability from normalized signals.

    Parameters
    ----------
    normalized : NormalizedSignals
        All values on a common 0-100 scale.

    Returns
    -------
    ModuleScores
        Five module scores plus a weighted ``final_viability_score``,
        all clamped 0-100.
    """

    # 1. Problem Intensity
    problem_intensity = _clamp(normalized.pain_intensity)

    # 2. Market Timing
    market_timing = _clamp(
        0.4 * normalized.market_growth
        + 0.3 * normalized.market_momentum
        + 0.3 * normalized.demand_strength
    )

    # 3. Competition Pressure  (higher competition = worse score)
    competition_pressure = _clamp(
        100
        - (0.6 * normalized.competition_density
           + 0.4 * normalized.feature_overlap)
    )

    # 4. Market Potential
    market_potential = _clamp(
        0.6 * normalized.demand_strength
        + 0.4 * normalized.market_growth
    )

    # 5. Execution Feasibility
    execution_feasibility = _clamp(
        100
        - (0.6 * normalized.tech_complexity_score
           + 0.4 * normalized.regulatory_risk_score)
    )

    # Final Viability Score  (weights sum to 1.0)
    final_viability_score = _clamp(
        0.25 * problem_intensity
        + 0.25 * market_timing
        + 0.20 * competition_pressure
        + 0.15 * market_potential
        + 0.15 * execution_feasibility
    )

    return ModuleScores(
        problem_intensity=round(problem_intensity, 2),
        market_timing=round(market_timing, 2),
        competition_pressure=round(competition_pressure, 2),
        market_potential=round(market_potential, 2),
        execution_feasibility=round(execution_feasibility, 2),
        final_viability_score=round(final_viability_score, 2),
    )
