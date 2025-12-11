import asyncio
import logging
import os
import random
import socket
from typing import Any

from ..state import ValidationState, RedditSentiment


logger = logging.getLogger(__name__)


def _is_network_error(error: Exception) -> tuple[bool, str]:
    
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # DNS resolution errors
    if isinstance(error, socket.gaierror) or "getaddrinfo" in error_str:
        return True, "DNS resolution failed"
    
    # Connection errors (check string patterns)
    if any(term in error_str for term in [
        "connectionerror", "connection refused", "connection reset",
        "connection aborted", "connection timeout", "nameresolutionerror",
        "nodename nor servname", "temporary failure in name resolution"
    ]):
        return True, "Connection error"
    
    # Timeout errors
    if any(term in error_str for term in ["timeout", "timed out"]):
        return True, "Request timeout"
    
    # SSL/TLS errors
    if any(term in error_str for term in ["ssl", "certificate", "handshake"]):
        return True, "SSL/TLS error"
    
    # Check for requests library specific errors
    if "requests.exceptions" in error_type or "urllib3" in error_type:
        return True, "HTTP client error"
    
    # Check for httpx/aiohttp specific errors (if Tavily uses these)
    if any(lib in error_type.lower() for lib in ["httpx", "aiohttp", "clienterror"]):
        return True, "Async HTTP error"
    
    return False, "Unknown error"

def _categorize_tavily_error(error: Exception) -> str:
    
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # Check for network errors first
    is_network, network_category = _is_network_error(error)
    if is_network:
        return f"Network error ({network_category})"
    
    # API-specific errors
    if "api" in error_type.lower() or "tavily" in error_type.lower():
        if "key" in error_str or "auth" in error_str or "401" in error_str:
            return "Authentication error (invalid API key)"
        if "rate" in error_str or "429" in error_str or "limit" in error_str:
            return "Rate limit exceeded"
        if "400" in error_str or "bad request" in error_str:
            return "Bad request (invalid parameters)"
        if "500" in error_str or "502" in error_str or "503" in error_str:
            return "Tavily server error"
        return "Tavily API error"
    
    # Generic categorization
    if "json" in error_str or "decode" in error_str:
        return "Invalid response format"
    
    return f"Unexpected error: {error_type}"

