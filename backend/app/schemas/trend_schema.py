from typing import Optional

from pydantic import BaseModel, Field


class TrendDemandSignals(BaseModel):
    """Quantifiable market demand and timing signals from Google Trends.

    Produced by the Trend & Demand Agent via SerpAPI.
    All fields are mandatory.  This object feeds directly into the
    Market Timing scoring module.
    """

    avg_search_volume: float = Field(
        ...,
        ge=0.0,
        description="Mean Google Trends interest value (0-100 scale) across all keywords",
    )
    growth_rate_5y: float = Field(
        ...,
        ge=-1.0,
        le=2.0,
        description="5-year growth rate: (last_year_avg - first_year_avg) / first_year_avg, clamped [-1, 2]",
    )
    momentum_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Recent acceleration: normalised ratio of last-6-month avg vs previous-6-month avg",
    )
    volatility_index: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Instability measure: std_dev / mean of trend values, clamped [0, 1]",
    )
    demand_strength_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite demand signal: min(avg_volume/100, 1) * (1 + growth_rate), clamped [0, 1]",
    )
    trend_data_available: bool = Field(
        default=True,
        description="True if any keyword tier returned usable trend data",
    )
    trend_data_source_tier: Optional[str] = Field(
        default=None,
        description="Which keyword tier produced the data: 'tier_1', 'tier_2', 'tier_3', or null",
    )
