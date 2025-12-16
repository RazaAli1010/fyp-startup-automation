"""
Async HTTP Client Configuration

Provides a shared httpx.AsyncClient with connection pooling and
timeout presets for each external service.
"""

import httpx
from typing import Optional
from contextlib import asynccontextmanager


# Timeout configurations (in seconds)
class Timeouts:
    """Timeout presets for external services."""
    TAVILY = 8.0        # Reddit/Tavily API
    SERPAPI = 8.0       # Google Trends via SerpAPI
    EXA = 10.0          # Exa.ai search
    OPENAI = 12.0       # OpenAI API calls
    OPENAI_EMBEDDING = 15.0  # OpenAI embeddings (batch)
    
    # Global node timeout - if a node takes longer, bail out
    NODE_MAX = 25.0


# Retry configuration
class RetryConfig:
    """Retry settings - minimal to avoid cumulative delays."""
    MAX_RETRIES = 2
    INITIAL_BACKOFF = 0.5  # seconds
    MAX_BACKOFF = 1.5      # seconds
    
    # Non-retryable status codes
    NON_RETRYABLE_CODES = {401, 403, 404, 422}
    
    # Retryable status codes
    RETRYABLE_CODES = {429, 500, 502, 503, 504}


# Shared client instance (lazily initialized)
_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    """Get the shared async HTTP client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            follow_redirects=True,
        )
    return _client


async def close_client():
    """Close the shared client (call on app shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


@asynccontextmanager
async def managed_client():
    """Context manager for client lifecycle."""
    client = await get_client()
    try:
        yield client
    finally:
        pass  # Don't close here - reuse for connection pooling


def get_timeout(service: str) -> httpx.Timeout:
    """Get timeout configuration for a service."""
    timeouts = {
        "tavily": Timeouts.TAVILY,
        "serpapi": Timeouts.SERPAPI,
        "exa": Timeouts.EXA,
        "openai": Timeouts.OPENAI,
        "openai_embedding": Timeouts.OPENAI_EMBEDDING,
    }
    seconds = timeouts.get(service.lower(), 10.0)
    return httpx.Timeout(seconds, connect=5.0)


def is_retryable_error(status_code: int) -> bool:
    """Check if an HTTP error is retryable."""
    return status_code in RetryConfig.RETRYABLE_CODES


def is_non_retryable_error(status_code: int) -> bool:
    """Check if an HTTP error should not be retried."""
    return status_code in RetryConfig.NON_RETRYABLE_CODES
