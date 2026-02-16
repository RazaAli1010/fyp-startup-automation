"""Pydantic schemas for Pitch Deck API responses.

PitchDeckRecord is the DB-backed response returned by all pitch deck endpoints.
It includes metadata (id, status, created_at) alongside the Alai output links.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PitchDeckRecord(BaseModel):
    """Single pitch deck record — returned by all pitch deck endpoints."""

    id: str = Field(..., description="Pitch deck UUID")
    idea_id: str = Field(..., description="Linked idea UUID")
    title: str = Field(..., description="Deck title (startup name)")
    status: Literal["pending", "completed", "failed"] = Field(
        ..., description="Generation lifecycle status"
    )
    provider: str = Field(default="alai", description="Generation provider")
    generation_id: Optional[str] = Field(
        default=None, description="Alai generation ID"
    )
    view_url: Optional[str] = Field(
        default=None, description="Shareable presentation link"
    )
    pdf_url: Optional[str] = Field(
        default=None, description="PDF download link"
    )
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class PitchDeckListResponse(BaseModel):
    """List of pitch deck records."""

    pitch_decks: list[PitchDeckRecord] = Field(
        default_factory=list, description="Pitch decks sorted by created_at DESC"
    )
