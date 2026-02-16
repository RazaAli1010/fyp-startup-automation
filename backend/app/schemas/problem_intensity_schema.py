"""Problem Intensity Signals — structured output from the Problem Intensity Agent.

Uses Tavily + SerpAPI only.  No Reddit, no Exa, no LLMs.
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class ProblemIntensitySignals(BaseModel):
    """Quantifiable problem-intensity signals derived from search + content data.

    Produced by the Problem Intensity Agent (Tavily + SerpAPI).
    Feeds directly into the normalization engine for the Problem Intensity
    scoring module.
    """

    # ── Search intent ────────────────────────────────────────────────────
    total_problem_queries: int = Field(
        ...,
        ge=0,
        description="Total number of problem-oriented queries executed",
    )
    problem_query_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of search results that are problem-oriented",
    )
    alternatives_query_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of search results about alternatives / switching",
    )

    # ── Evidence content ─────────────────────────────────────────────────
    pain_articles_count: int = Field(
        ...,
        ge=0,
        description="Number of articles / pages with pain-related content",
    )
    avg_article_recency_months: float = Field(
        ...,
        ge=0.0,
        description="Average age of pain articles in months (0 = very recent)",
    )
    pain_keywords: List[str] = Field(
        default_factory=list,
        description="Top pain keywords extracted from article content",
    )

    # ── Complaints (from articles / reviews) ─────────────────────────────
    complaint_density: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of evidence passages that contain complaint language",
    )
    top_complaints: List[str] = Field(
        default_factory=list,
        description="Top repeated complaint phrases extracted from content",
    )

    # ── Manual work & cost ───────────────────────────────────────────────
    manual_process_detected: bool = Field(
        ...,
        description="True if evidence suggests manual / spreadsheet-based workflows",
    )
    manual_steps_count: int = Field(
        ...,
        ge=0,
        description="Estimated number of manual steps in the current workflow",
    )
    estimated_time_waste_hours_per_week: float = Field(
        ...,
        ge=0.0,
        description="Conservative estimate of hours wasted per week on manual work",
    )

    # ── Component scores (0-100, deterministic) ──────────────────────────
    search_intent_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Score derived from problem_query_ratio",
    )
    evidence_strength_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Score derived from article count + recency",
    )
    complaint_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Score derived from complaint density + repetition",
    )
    manual_cost_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Score derived from manual process detection + time waste",
    )

    # ── Final output ─────────────────────────────────────────────────────
    problem_intensity_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Weighted composite: 0.30×search + 0.25×complaint + 0.25×manual + 0.20×evidence",
    )
    confidence_level: Literal["low", "medium", "high"] = Field(
        ...,
        description="Data confidence: high (≥3 categories), medium (2), low (0-1)",
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of how the score was derived",
    )
