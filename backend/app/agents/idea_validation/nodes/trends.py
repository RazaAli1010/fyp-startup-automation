"""
Google Trends Analysis Node — DEPRECATED.

The old async SerpAPI trend logic has been replaced by the Trend & Demand
Agent at ``app.services.trend_agent``, which accepts a ``QueryBundle``
and returns ``TrendDemandSignals``.

This file is retained only so that existing graph imports do not break at
import time.  All functions return empty / no-op values.
"""

from typing import Dict, Any


async def search_trends(state: Dict[str, Any]) -> Dict[str, Any]:
    """DEPRECATED — use ``app.services.trend_agent.fetch_trend_demand_signals``."""
    return {"trends_data": None, "processing_errors": ["Trends node deprecated"]}
