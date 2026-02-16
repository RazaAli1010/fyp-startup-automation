from typing import Dict

from pydantic import BaseModel, Field


class NormalizationExplanation(BaseModel):
    """Breakdown of how a single normalized signal was computed."""

    raw_value: float = Field(
        ...,
        description="The raw value before normalization",
    )
    formula: str = Field(
        ...,
        description="Human-readable normalization formula applied",
    )
    description: str = Field(
        ...,
        description="Short explanation of what this signal represents",
    )


class NormalizedSignals(BaseModel):
    """All raw agent signals normalized to a common 0-100 scale.

    Produced by the Signal Normalization Engine.  Every field is a float
    clamped between 0 and 100.  This object is the single input consumed
    by the downstream Scoring Engine.
    """

    pain_intensity: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Problem intensity from Tavily + SerpAPI signals, normalised to 0-100",
    )
    demand_strength: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Trend demand strength normalised to 0-100",
    )
    market_growth: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="5-year growth rate normalised to 0-100 with soft saturation",
    )
    market_momentum: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Recent momentum normalised to 0-100",
    )
    competition_density: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Competitor density normalised to 0-100",
    )
    feature_overlap: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Feature overlap with competitors normalised to 0-100",
    )
    tech_complexity_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Technical complexity normalised to 0-100",
    )
    regulatory_risk_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Regulatory risk normalised to 0-100",
    )
    normalization_explanations: Dict[str, NormalizationExplanation] = Field(
        default_factory=dict,
        description="Per-signal breakdown: raw value, formula, and description",
    )
