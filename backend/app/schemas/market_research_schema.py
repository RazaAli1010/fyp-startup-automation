"""Pydantic schemas for Market Research API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MarketResearchRecord(BaseModel):
    """Single market research record — returned by all market research endpoints."""

    id: str = Field(..., description="Market research UUID")
    idea_id: str = Field(..., description="Linked idea UUID")
    status: Literal["pending", "completed", "failed"] = Field(
        ..., description="Generation lifecycle status"
    )

    tam_min: Optional[float] = Field(default=None, description="TAM lower bound (USD)")
    tam_max: Optional[float] = Field(default=None, description="TAM upper bound (USD)")
    sam_min: Optional[float] = Field(default=None, description="SAM lower bound (USD)")
    sam_max: Optional[float] = Field(default=None, description="SAM upper bound (USD)")
    som_min: Optional[float] = Field(default=None, description="SOM lower bound (USD)")
    som_max: Optional[float] = Field(default=None, description="SOM upper bound (USD)")

    arpu_annual: Optional[float] = Field(default=None, description="Annual revenue per user (USD)")
    growth_rate_estimate: Optional[float] = Field(default=None, description="Estimated annual growth rate (%)")
    demand_strength: Optional[float] = Field(default=None, description="Demand strength score 0-100")

    assumptions: Optional[List[str]] = Field(default=None, description="Assumptions used in calculations")
    confidence: Optional[Dict[str, Any]] = Field(default=None, description="Confidence scores and explanations")
    sources: Optional[List[str]] = Field(default=None, description="Data sources used")
    competitors: Optional[List[Dict[str, Any]]] = Field(default=None, description="Discovered competitors")
    competitor_count: Optional[int] = Field(default=None, description="Number of competitors found")

    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class MarketResearchListResponse(BaseModel):
    """List of market research records."""

    records: list[MarketResearchRecord] = Field(
        default_factory=list, description="Market research records sorted by created_at DESC"
    )
