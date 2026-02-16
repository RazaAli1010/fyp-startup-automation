"""Centralized Google OAuth 2.0 configuration.

Loads and validates Google OAuth environment variables at import time.
Exposes GOOGLE_AUTH_ENABLED boolean and config values for use by auth routes.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Determine if Google OAuth is fully configured — all three values required
GOOGLE_AUTH_ENABLED: bool = bool(
    GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI
)

_missing: list[str] = []
if not GOOGLE_CLIENT_ID:
    _missing.append("GOOGLE_CLIENT_ID")
if not GOOGLE_CLIENT_SECRET:
    _missing.append("GOOGLE_CLIENT_SECRET")
if not GOOGLE_REDIRECT_URI:
    _missing.append("GOOGLE_REDIRECT_URI")

if GOOGLE_AUTH_ENABLED:
    logger.info("[AUTH] Google OAuth enabled: True")
else:
    logger.warning(
        "[AUTH] Google OAuth enabled: False (missing env vars: %s)",
        ", ".join(_missing),
    )


def log_google_oauth_status() -> None:
    """Print Google OAuth status to stdout for startup visibility."""
    if GOOGLE_AUTH_ENABLED:
        print("[AUTH] Google OAuth enabled: True")
        print(f"[AUTH] Google Redirect URI: {GOOGLE_REDIRECT_URI}")
    else:
        print(f"[AUTH] Google OAuth enabled: False (missing env vars: {', '.join(_missing)})")
