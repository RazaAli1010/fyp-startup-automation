"""MVP Blueprint schema — strict output contract.

This schema is returned by the MVP generator and stored as JSON in the database.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class MVPBlueprint(BaseModel):
    """Locked MVP output schema — do NOT add or remove fields."""

    mvp_type: str = Field(..., description="MVP approach type (e.g. 'Landing Page + Waitlist', 'Wizard of Oz', 'Concierge')")
    core_hypothesis: str = Field(..., description="Primary hypothesis this MVP validates")
    primary_user: str = Field(..., description="Target user persona for the MVP")

    core_features: List[Dict[str, str]] = Field(
        ..., description="List of core features, each with 'name' and 'description'"
    )
    excluded_features: List[str] = Field(
        ..., description="Features explicitly excluded from MVP scope"
    )
    user_flow: List[str] = Field(
        ..., description="Ordered steps of the primary user journey"
    )

    recommended_tech_stack: Dict[str, str] = Field(
        ..., description="Tech stack recommendations keyed by category (e.g. 'frontend', 'backend')"
    )

    build_plan: Dict[str, Any] = Field(
        ..., description="Phased build plan with timeline and milestones"
    )
    validation_plan: Dict[str, Any] = Field(
        ..., description="Plan for validating the MVP hypothesis"
    )

    risk_notes: List[str] = Field(
        ..., description="Key risks and mitigation notes"
    )
