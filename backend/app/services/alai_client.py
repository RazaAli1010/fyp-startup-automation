"""Alai Slides API client — create generation, poll status, extract links.

Reads configuration from environment variables:
  ALAI_API_KEY    — required; generation fails loudly if missing
  ALAI_BASE_URL   — https://slides-api.getalai.com/api/v1
  ALAI_MAX_SLIDES — max slides per deck (default 10)
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

# ── Load .env FIRST, then read vars ─────────────────────────────────────

load_dotenv()

ALAI_API_KEY: str = os.getenv("ALAI_API_KEY", "")
ALAI_BASE_URL: str = os.getenv("ALAI_BASE_URL", "https://slides-api.getalai.com/api/v1")
ALAI_MAX_SLIDES: int = int(os.getenv("ALAI_MAX_SLIDES", "10"))

# ── Startup diagnostics ─────────────────────────────────────────────────
print("🔐 [ALAI] API key loaded:", bool(ALAI_API_KEY))
print("🌐 [ALAI] Base URL:", ALAI_BASE_URL)
print("📊 [ALAI] Max slides allowed:", ALAI_MAX_SLIDES)
if not ALAI_API_KEY:
    print("⚠️  [ALAI] WARNING: ALAI_API_KEY is EMPTY — pitch deck generation will FAIL")


def is_alai_available() -> bool:
    """Return True if the Alai API key is configured."""
    return bool(ALAI_API_KEY and ALAI_API_KEY.strip())


class AlaiError(Exception):
    """Raised when the Alai API returns an error or is unavailable."""


async def generate_pitch_deck_via_alai(
    *,
    input_text: str,
    deck_title: str,
) -> dict[str, Any]:
    """Create an Alai Slides generation, poll until complete, return links.

    Flow:
      1. POST /generations  → get generation_id
      2. GET  /generations/{id}  → poll until completed/failed
      3. Extract view_url and pdf_url from completed response

    Parameters
    ----------
    input_text:
        The text content describing the pitch deck (idea + validation summary).
    deck_title:
        Title for the presentation.

    Returns
    -------
    dict with keys: generation_id, view_url, pdf_url

    Raises
    ------
    AlaiError
        If the API key is missing, any request fails, polling times out,
        or output links are missing.
    """
    if not is_alai_available():
        print("❌ [ALAI] API key is MISSING — cannot proceed")
        raise AlaiError("Alai API key missing — pitch deck generation unavailable")

    # ── STEP 1: Create generation ────────────────────────
    payload = {
        "input_text": input_text,
        "presentation_options": {
            "title": deck_title,
            "slide_range": f"6-{ALAI_MAX_SLIDES}",
        },
        "export_formats": ["link", "pdf"],
    }

    print(f"🚀 [ALAI] Generation started — title={deck_title}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ALAI_BASE_URL}/generations",
                headers={"Authorization": f"Bearer {ALAI_API_KEY}"},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        print("❌ [ALAI] Create request TIMED OUT")
        raise AlaiError("Alai generation create request timed out") from exc
    except httpx.HTTPError as exc:
        print(f"❌ [ALAI] Create request FAILED: {exc}")
        raise AlaiError(f"Alai generation create request failed: {exc}") from exc

    if response.status_code not in (200, 201):
        print(f"❌ [ALAI] Create returned non-200: {response.status_code}")
        raise AlaiError(f"Alai generation create failed (HTTP {response.status_code}): {response.text[:500]}")

    try:
        create_json = response.json()
    except ValueError as exc:
        print(f"❌ [ALAI] Failed to parse create response JSON")
        raise AlaiError("Alai create response is not valid JSON") from exc

    generation_id = create_json.get("generation_id")
    if not generation_id:
        print(f"❌ [ALAI] No generation_id in response: {create_json}")
        raise AlaiError("Alai create response missing generation_id")

    print(f"🚀 [ALAI] Generation created — generation_id={generation_id}")

    # ── STEP 2: Poll generation status (async) ───────────────

    status_json: dict[str, Any] = {}
    completed = False

    async with httpx.AsyncClient(timeout=15.0) as client:
        for poll_attempt in range(20):  # max ~60 seconds
            try:
                status_response = await client.get(
                    f"{ALAI_BASE_URL}/generations/{generation_id}",
                    headers={"Authorization": f"Bearer {ALAI_API_KEY}"},
                )
            except httpx.HTTPError as exc:
                print(f"❌ [ALAI] Poll request failed (attempt {poll_attempt + 1}): {exc}")
                raise AlaiError(f"Alai poll request failed: {exc}") from exc

            try:
                status_json = status_response.json()
            except ValueError as exc:
                print(f"❌ [ALAI] Poll response not valid JSON (attempt {poll_attempt + 1})")
                raise AlaiError("Alai poll response is not valid JSON") from exc

            current_status = status_json.get("status", "unknown")
            print(f"🔄 [ALAI] Polling generation_id={generation_id} — attempt {poll_attempt + 1}/20, status={current_status}")

            if current_status == "completed":
                completed = True
                break

            if current_status == "failed":
                error_detail = status_json.get("error", "Unknown error")
                print(f"❌ [ALAI] Generation FAILED: {error_detail}")
                raise AlaiError(f"Alai generation failed: {error_detail}")

            await asyncio.sleep(3)

    if not completed:
        print("❌ [ALAI] Polling TIMED OUT after 20 attempts (~60s)")
        raise AlaiError("Alai generation polling timed out — generation did not complete in time")

    # ── STEP 3: Extract output links ─────────────────────────
    formats = status_json.get("formats", {})

    view_url = formats.get("link", {}).get("url")
    pdf_url = formats.get("pdf", {}).get("url")

    if not view_url:
        print("❌ [ALAI] Missing view_url in completed response")
        raise AlaiError("Alai completed response missing presentation link (view_url)")

    if not pdf_url:
        print("❌ [ALAI] Missing pdf_url in completed response")
        raise AlaiError("Alai completed response missing PDF link (pdf_url)")

    result = {
        "generation_id": generation_id,
        "view_url": view_url,
        "pdf_url": pdf_url,
    }

    print(f"✅ [ALAI] Deck ready (PDF + Link) — generation_id={generation_id}")

    return result
