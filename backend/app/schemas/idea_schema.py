from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class StartupIdeaInput(BaseModel):
    """Structured multi-section startup idea intake schema."""

    # SECTION 1: Core Idea
    startup_name: str = Field(..., min_length=1, max_length=255)
    one_line_description: str = Field(..., min_length=1, max_length=500)
    industry: str = Field(..., min_length=1, max_length=255)

    # SECTION 2: Target Market
    target_customer_type: Literal["B2B", "B2C", "Marketplace"]
    geography: str = Field(..., min_length=1, max_length=255)
    customer_size: Literal["Individual", "SMB", "Mid-Market", "Enterprise"]

    # SECTION 3: Business Model
    revenue_model: Literal["Subscription", "One-time", "Marketplace Fee", "Ads"]
    pricing_estimate: float

    # SECTION 4: Assumptions
    estimated_cac: float
    estimated_ltv: float
    team_size: int = Field(..., ge=1)
    tech_complexity: float
    regulatory_risk: float

    @field_validator("pricing_estimate")
    @classmethod
    def pricing_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("pricing_estimate must be greater than 0")
        return v

    @field_validator("estimated_cac")
    @classmethod
    def cac_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("estimated_cac must be >= 0")
        return v

    @field_validator("estimated_ltv")
    @classmethod
    def ltv_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("estimated_ltv must be >= 0")
        return v

    @field_validator("tech_complexity")
    @classmethod
    def tech_complexity_range(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("tech_complexity must be between 0 and 1")
        return v

    @field_validator("regulatory_risk")
    @classmethod
    def regulatory_risk_range(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("regulatory_risk must be between 0 and 1")
        return v


class IdeaResponse(BaseModel):
    """Response returned after successfully submitting a startup idea."""

    idea_id: UUID
    message: str
