from typing import Optional

from pydantic import BaseModel, Field


class QueryBundle(BaseModel):
    """Deterministic query bundle generated from structured startup idea input.

    Consumed by all downstream data agents (trends, reddit, competitors).
    Every field is required and must contain at least one entry.
    """

    core_keywords: list[str] = Field(
        ...,
        min_length=1,
        description="Primary search keywords derived from industry, description, and revenue model",
    )
    trend_keywords: list[str] = Field(
        ...,
        min_length=1,
        description="Short 1-3 word phrases optimised for Google Trends / SerpAPI",
    )
    trend_keywords_tier2: Optional[list[str]] = Field(
        default=None,
        description="Category-level fallback keywords for SerpAPI (industry + function)",
    )
    trend_keywords_tier3: Optional[list[str]] = Field(
        default=None,
        description="Broad market fallback keywords for SerpAPI (general industry terms)",
    )
    reddit_queries: list[str] = Field(
        ...,
        min_length=1,
        description="Pain-focused phrases for Reddit sentiment search",
    )
    competitor_queries: list[str] = Field(
        ...,
        min_length=1,
        description="Discovery-oriented queries for competitor search (Exa)",
    )
    industry_tags: list[str] = Field(
        ...,
        min_length=1,
        description="Single-word or short lowercase tags for the industry vertical",
    )
