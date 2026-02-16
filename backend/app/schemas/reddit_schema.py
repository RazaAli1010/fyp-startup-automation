from pydantic import BaseModel, Field


class RedditPainSignals(BaseModel):
    """Quantifiable pain signals extracted from Reddit posts.

    Produced by the Reddit Pain Mining Agent.  Every field is mandatory.
    This object feeds directly into the Problem Intensity scoring module.
    """

    total_posts_analyzed: int = Field(
        ...,
        ge=0,
        description="Total number of Reddit posts scanned across all subreddits",
    )
    complaint_post_count: int = Field(
        ...,
        ge=0,
        description="Number of posts classified as complaints (pain-word + query-keyword match)",
    )
    avg_upvotes: float = Field(
        ...,
        ge=0.0,
        description="Average score (upvotes) of complaint posts only",
    )
    avg_comments: float = Field(
        ...,
        ge=0.0,
        description="Average comment count of complaint posts only",
    )
    pain_intensity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalised pain intensity between 0 and 1",
    )
    top_pain_keywords: list[str] = Field(
        ...,
        max_length=5,
        description="Top-5 most frequent non-stopword tokens from complaint posts (lowercase)",
    )
