from pydantic import BaseModel, Field


class CompetitorSignals(BaseModel):
    """Structured competitor landscape signals from Exa API discovery.

    Produced by the Competitor Discovery Agent.  All fields are mandatory.
    This object feeds directly into Competition Pressure and Differentiation
    scoring modules.
    """

    total_competitors: int = Field(
        ...,
        ge=0,
        description="Count of unique competitor entities discovered",
    )
    competitor_names: list[str] = Field(
        ...,
        max_length=15,
        description="Unique competitor names (max 15)",
    )
    avg_company_age: float = Field(
        ...,
        ge=0.0,
        description="Average estimated company age in years (from founding year or Exa metadata)",
    )
    competitor_density_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Market crowding: min(total_competitors / 20, 1.0)",
    )
    feature_overlap_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Jaccard similarity of competitor description nouns vs industry + core keywords",
    )
