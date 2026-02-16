from pydantic import BaseModel, Field


class ModuleScores(BaseModel):
    """Deterministic module scores and final viability score.

    Produced by the Scoring Engine from ``NormalizedSignals``.
    Every field is a float clamped between 0 and 100.
    The ``final_viability_score`` is a weighted composite of all modules.
    """

    problem_intensity: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Direct pass-through of normalised pain_intensity",
    )
    market_timing: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="0.4*market_growth + 0.3*market_momentum + 0.3*demand_strength",
    )
    competition_pressure: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="100 - (0.6*competition_density + 0.4*feature_overlap)",
    )
    market_potential: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="0.6*demand_strength + 0.4*market_growth",
    )
    execution_feasibility: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="100 - (0.6*tech_complexity_score + 0.4*regulatory_risk_score)",
    )
    final_viability_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Weighted composite: 0.25*PI + 0.25*MT + 0.20*CP + 0.15*MP + 0.15*EF",
    )
