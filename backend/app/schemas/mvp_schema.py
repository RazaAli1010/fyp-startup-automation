"""Pydantic schemas for MVP API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MVPBlueprintResponse(BaseModel):
    """MVP blueprint data — nested inside MVPReportRecord."""

    mvp_type: str
    core_hypothesis: str
    primary_user: str
    core_features: List[Dict[str, str]]
    excluded_features: List[str]
    user_flow: List[str]
    recommended_tech_stack: Dict[str, str]
    build_plan: Dict[str, Any]
    validation_plan: Dict[str, Any]
    risk_notes: List[str]


class MVPReportRecord(BaseModel):
    """Single MVP report record — returned by all MVP endpoints."""

    id: str = Field(..., description="MVP report UUID")
    idea_id: str = Field(..., description="Linked idea UUID")
    status: Literal["pending", "generated", "failed"] = Field(
        ..., description="Generation lifecycle status"
    )
    blueprint: Optional[MVPBlueprintResponse] = Field(
        default=None, description="The generated MVP blueprint"
    )
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class MVPReportListResponse(BaseModel):
    """List of MVP report records."""

    records: list[MVPReportRecord] = Field(
        default_factory=list, description="MVP reports sorted by created_at DESC"
    )
