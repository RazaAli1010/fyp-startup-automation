"""
Reddit Sentiment Analysis Node — DEPRECATED.

The Tavily-based Reddit search logic has been replaced by the Reddit Pain
Mining Agent at ``app.services.reddit_agent``, which uses the official
Reddit API (PRAW) and accepts a ``QueryBundle``.

This file is retained only so that existing graph imports do not break at
import time.  All functions return empty / no-op values.
"""

from typing import Dict, List, Any, Tuple


async def search_reddit(state: Dict[str, Any]) -> Dict[str, Any]:
    """DEPRECATED — use ``app.services.reddit_agent.fetch_reddit_pain_signals``."""
    return {"reddit_sentiment": None, "processing_errors": ["Reddit node deprecated"]}
