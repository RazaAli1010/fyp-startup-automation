from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class StartupIdeaInput(BaseModel):
    """Simplified startup idea intake — only user-facing inputs.

    Removed inputs (not used in scoring or inferred by OpenAI):
      - customer_size, revenue_model, pricing_estimate
      - estimated_cac, estimated_ltv, team_size
      - tech_complexity, regulatory_risk
    """

    # SECTION 1: Core Idea
    startup_name: str = Field(..., min_length=1, max_length=255)
    one_line_description: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Detailed business description (2-5 paragraphs). "
        "Explain the problem, solution, target users, and how it works.",
    )
    industry: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Comma-separated industry tags from the standardized list.",
    )

    # SECTION 2: Target Market
    target_customer_type: Literal["B2B", "B2C", "B2B2C"]
    geography: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Comma-separated target countries/regions.",
    )

    @field_validator("one_line_description")
    @classmethod
    def description_not_trivial(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped.split()) < 5:
            raise ValueError(
                "Business description must be detailed (at least 5 words). "
                "Explain the problem, solution, and target users."
            )
        return stripped


class IdeaResponse(BaseModel):
    """Response returned after successfully submitting a startup idea."""

    idea_id: UUID
    message: str
