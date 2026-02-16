from typing import List, Optional

from pydantic import BaseModel, Field

from .normalized_schema import NormalizedSignals
from .score_schema import ModuleScores


class IdeaEvaluationReport(BaseModel):
    """Complete evaluation report returned by the evaluation pipeline.

    Contains the idea identifier, all normalized signals, module scores,
    and a rule-based summary with verdict, risk level, and key insights.
    """

    idea_id: str = Field(
        ...,
        description="UUID of the evaluated idea",
    )
    normalized_signals: NormalizedSignals = Field(
        ...,
        description="All agent signals normalised to 0-100",
    )
    module_scores: ModuleScores = Field(
        ...,
        description="Deterministic module scores and final viability score",
    )
    competitor_names: List[str] = Field(
        default_factory=list,
        description="Unique competitor names discovered by the Exa agent",
    )
    trend_data_available: bool = Field(
        default=True,
        description="True if any keyword tier returned usable trend data from SerpAPI",
    )
    trend_data_source_tier: Optional[str] = Field(
        default=None,
        description="Which keyword tier produced trend data: 'tier_1', 'tier_2', 'tier_3', or null",
    )
    summary: dict[str, str] = Field(
        ...,
        description="Rule-based verdict, risk_level, key_strength, key_risk",
    )
