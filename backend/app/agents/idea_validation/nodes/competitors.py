"""
Competitor Analysis Node -- DEPRECATED.

The old Exa-based competitor analysis logic has been replaced by the
Competitor Discovery Agent at ``app.services.competitor_agent``, which
accepts a ``QueryBundle`` and returns ``CompetitorSignals``.

This file is retained only so that existing graph imports do not break at
import time.  All functions return empty / no-op values.
"""

from typing import Dict, Any


async def search_competitors(state: Dict[str, Any]) -> Dict[str, Any]:
    """DEPRECATED -- use ``app.services.competitor_agent.fetch_competitor_signals``."""
    return {"competitor_analysis": None, "processing_errors": ["Competitors node deprecated"]}
