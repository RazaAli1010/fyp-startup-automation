"""Funding Enrichment Agent.

Enriches competitor names with capital and funding intelligence via a
pluggable ``FundingDataProvider``.  The provider is selected at runtime
through the ``FUNDING_PROVIDER`` environment variable.

Rules
-----
- NO LLM calls
- NO heuristic funding estimates
- NO scoring / judging
- Pure enrichment: real API data only
- Provider-agnostic: never references a specific API directly
"""

from __future__ import annotations

import logging
import statistics
from typing import Dict, List, Optional

from ..schemas.funding_schema import FundingSignals
from .funding_providers import FundingDataProvider, get_provider

logger = logging.getLogger(__name__)

# Stage normalisation map — various providers use different labels; we
# collapse them into a small canonical set for the stage_distribution dict.
_STAGE_NORMALISATION: Dict[str, str] = {
    "pre_seed": "Pre-Seed",
    "seed": "Seed",
    "angel": "Seed",
    "series_a": "Series A",
    "series_b": "Series B",
    "series_c": "Series C",
    "series_d": "Series D",
    "series_e": "Series E+",
    "series_f": "Series E+",
    "series_g": "Series E+",
    "series_h": "Series E+",
    "private_equity": "Private Equity",
    "debt_financing": "Debt",
    "grant": "Grant",
    "ipo": "IPO",
    "post_ipo_equity": "IPO",
    "post_ipo_debt": "IPO",
    "undisclosed": "Undisclosed",
}


# ===================================================================== #
#  Internal helpers                                                       #
# ===================================================================== #

def _normalise_stage(raw_stage: str) -> str:
    """Map a raw funding type to a canonical stage label."""
    if not raw_stage:
        return "Unknown"
    key = raw_stage.strip().lower().replace(" ", "_").replace("-", "_")
    return _STAGE_NORMALISATION.get(key, raw_stage.title())


# ===================================================================== #
#  Public API                                                             #
# ===================================================================== #

def fetch_funding_signals(competitor_names: List[str]) -> FundingSignals:
    """Enrich competitor names with funding data from the configured provider.

    Parameters
    ----------
    competitor_names:
        A list of company names from ``CompetitorSignals.competitor_names``.

    Returns
    -------
    FundingSignals
        Structured funding metrics ready for downstream consumption.
    """
    if not competitor_names:
        logger.info("No competitor names provided — returning empty signals.")
        return _empty_signals()

    provider: Optional[FundingDataProvider] = get_provider()
    if provider is None:
        logger.warning(
            "No funding provider configured — returning empty signals. "
            "Set FUNDING_PROVIDER env var to enable enrichment."
        )
        return _empty_signals()

    # ------------------------------------------------------------------ #
    #  1. Enrich each competitor                                          #
    # ------------------------------------------------------------------ #
    enriched: List[Dict] = []

    for name in competitor_names:
        try:
            funding_data = provider.get_funding_data(name)
        except Exception as exc:
            logger.warning(
                "Provider error for %r: %s — skipping.", name, exc
            )
            continue

        if not funding_data:
            logger.info("No funding data for %r — skipping.", name)
            continue

        enriched.append(funding_data)

    total_enriched = len(enriched)

    if total_enriched == 0:
        logger.info("No competitors enriched — returning empty signals.")
        return _empty_signals()

    # ------------------------------------------------------------------ #
    #  2. Compute metrics                                                 #
    # ------------------------------------------------------------------ #
    funding_amounts = [e["total_funding_usd"] for e in enriched]

    avg_funding = sum(funding_amounts) / total_enriched
    med_funding = float(statistics.median(funding_amounts))

    # funding_density_index
    density = min(avg_funding / 50_000_000, 1.0)

    # stage_distribution
    stage_dist: Dict[str, int] = {}
    for e in enriched:
        stage = _normalise_stage(e.get("last_funding_type", ""))
        stage_dist[stage] = stage_dist.get(stage, 0) + 1

    # capital_intensity_score
    intensity = min(med_funding / 30_000_000, 1.0)

    return FundingSignals(
        total_competitors_enriched=total_enriched,
        avg_total_funding=round(avg_funding, 2),
        median_total_funding=round(med_funding, 2),
        funding_density_index=round(density, 4),
        stage_distribution=stage_dist,
        capital_intensity_score=round(intensity, 4),
    )


def _empty_signals() -> FundingSignals:
    """Return zero-value signals for graceful degradation."""
    return FundingSignals(
        total_competitors_enriched=0,
        avg_total_funding=0.0,
        median_total_funding=0.0,
        funding_density_index=0.0,
        stage_distribution={},
        capital_intensity_score=0.0,
    )
