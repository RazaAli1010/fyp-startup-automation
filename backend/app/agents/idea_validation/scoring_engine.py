"""
Scoring Engine -- DEPRECATED.

The old ValidationMetrics / calculate_viability_score logic has been
replaced by the Deterministic Scoring Engine at
``app.services.scoring_engine``, which accepts ``NormalizedSignals``
and returns ``ModuleScores``.

This file is retained only so that existing graph imports do not break
at import time.
"""

from typing import Dict
from pydantic import BaseModel, Field


class ValidationMetrics(BaseModel):
    """DEPRECATED -- use ``app.schemas.score_schema.ModuleScores``."""
    demand_score: float = Field(0, ge=0, le=100)
    market_size_score: float = Field(0, ge=0, le=100)
    differentiation_score: float = Field(0, ge=0, le=100)
    timing_score: float = Field(0, ge=0, le=100)
    execution_risk_score: float = Field(0, ge=0, le=100)
    failure_risk_score: float = Field(0, ge=0, le=100)
    economic_viability_score: float = Field(0, ge=0, le=100)
    investor_fit_score: float = Field(0, ge=0, le=100)


def calculate_viability_score(metrics: ValidationMetrics) -> Dict:
    """DEPRECATED -- use ``app.services.scoring_engine.compute_scores``."""
    return {
        "viability_score": 0.0,
        "score_breakdown": {},
        "risk_adjusted_score": 0.0,
    }
