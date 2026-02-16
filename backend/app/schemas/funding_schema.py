from pydantic import BaseModel, Field


class FundingSignals(BaseModel):
    """Capital and funding intelligence for the competitive landscape.

    Produced by the Funding Enrichment Agent via a pluggable data provider.
    All fields are mandatory.  This object feeds directly into
    the Signal Normalization Engine and downstream Scoring Engine.
    """

    total_competitors_enriched: int = Field(
        ...,
        ge=0,
        description="Count of competitors successfully enriched with funding data",
    )
    avg_total_funding: float = Field(
        ...,
        ge=0.0,
        description="Mean total funding (USD) across enriched competitors",
    )
    median_total_funding: float = Field(
        ...,
        ge=0.0,
        description="Median total funding (USD) across enriched competitors",
    )
    funding_density_index: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Capital heaviness: min(avg_total_funding / 50_000_000, 1.0)",
    )
    stage_distribution: dict[str, int] = Field(
        ...,
        description="Count of competitors per latest funding stage (e.g. {'Seed': 4, 'Series A': 3})",
    )
    capital_intensity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Barrier-to-entry proxy: min(median_total_funding / 30_000_000, 1.0)",
    )
