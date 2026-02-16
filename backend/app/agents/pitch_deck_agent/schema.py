"""Pydantic schemas for Pitch Deck Agent input and output contracts."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


# ── Slide types ──────────────────────────────────────────────────────────

SlideType = Literal[
    "title",
    "problem",
    "solution",
    "market",
    "business_model",
    "competition",
    "traction",
    "risks",
    "ask",
]


class SlideOutput(BaseModel):
    """A single slide in the generated pitch deck."""

    type: SlideType = Field(..., description="Semantic slide type")
    title: str = Field(..., description="Slide heading")
    content: List[str] = Field(
        ..., description="Bullet points for this slide"
    )


class PitchDeckOutput(BaseModel):
    """Complete pitch deck returned by the generator."""

    deck_title: str = Field(..., description="Startup name as deck title")
    tagline: str = Field(..., description="One-line value proposition")
    slides: List[SlideOutput] = Field(
        default_factory=list, description="Ordered list of slides (empty when using Alai Slides API)"
    )
    provider: str = Field(
        default="alai",
        description="Provider that generated this deck",
    )
    generation_id: str = Field(
        default="", description="Alai generation ID"
    )
    view_url: str = Field(
        default="", description="Shareable presentation link from Alai"
    )
    pdf_url: str = Field(
        default="", description="PDF export link from Alai"
    )


# ── Internal input contracts (not exposed via API) ───────────────────────

class IdeaContext(BaseModel):
    """Subset of idea fields needed by the generator."""

    name: str
    description: str
    industry: str
    target_customer: str
    geography: str
    revenue_model: str
    pricing_estimate: float
    team_size: int


class ValidationContext(BaseModel):
    """Subset of evaluation results needed by the generator."""

    final_score: float
    verdict: str
    risk_level: str
    key_strength: str
    key_risk: str
    module_scores: ModuleScoresContext


class ModuleScoresContext(BaseModel):
    """Module scores passed to the generator."""

    problem_intensity: float
    market_timing: float
    competition_pressure: float
    market_potential: float
    execution_feasibility: float


# Rebuild ValidationContext to resolve forward ref
ValidationContext.model_rebuild()


class PitchDeckInput(BaseModel):
    """Full input contract for the pitch deck generator."""

    idea: IdeaContext
    validation: ValidationContext
