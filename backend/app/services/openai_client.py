"""Centralized OpenAI client — GPT-4.1 stable configuration.

All agents MUST use `call_openai_chat()` (sync) or
`call_openai_chat_async()` (async) from this module.
This ensures:
  - Model, temperature, timeout, and token limits are read from env.
  - JSON response format is enforced via response_format.
  - 1 retry on failure (timeout or invalid JSON), then return None.
  - Consistent logging across all agents.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import httpx

# ---------------------------------------------------------------------------
# Constants — all read from environment with safe defaults
# ---------------------------------------------------------------------------
_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_openai_key() -> str:
    """Read OPENAI_API_KEY from the environment. Raises EnvironmentError if missing."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        print("⚠️  [OPENAI] API key missing (OPENAI_API_KEY)")
        raise EnvironmentError("OPENAI_API_KEY environment variable not set")
    return key


def get_openai_model() -> str:
    """Read OPENAI_MODEL from the environment (default: gpt-4.1)."""
    return os.getenv("OPENAI_MODEL", "gpt-4.1").strip()


def _get_temperature() -> float:
    return _env_float("OPENAI_TEMPERATURE", 0.7)


def _get_timeout() -> float:
    return _env_float("OPENAI_REQUEST_TIMEOUT", 40.0)


def _get_default_max_tokens() -> int:
    return _env_int("OPENAI_MAX_COMPLETION_TOKENS", 4000)


# ---------------------------------------------------------------------------
# JSON sanitizer — extracts valid JSON from LLM output
# ---------------------------------------------------------------------------
def sanitize_json(raw: str) -> str:
    """Extract a JSON object from raw LLM output.

    Handles:
      - Markdown fences (```json ... ```)
      - Leading/trailing whitespace and BOM
      - Prose before/after JSON
      - Trailing commas before } or ]

    Raises ValueError if no JSON object is found.
    """
    import re

    text = raw.strip().lstrip("\ufeff")

    # 1. Strip markdown fences
    if text.startswith("```"):
        # Remove opening fence line (```json or ```)
        parts = text.split("```")
        # parts: ["", "json\n{...}", ""] or ["", "{...}", ""]
        if len(parts) >= 3:
            text = parts[1]
        else:
            text = text[3:]

    # 2. Strip language identifier (e.g., "json\n")
    text = text.strip()
    if text.lower().startswith("json"):
        text = text[4:].strip()

    # 3. Find first '{' — everything before it is prose
    brace_idx = text.find("{")
    if brace_idx == -1:
        raise ValueError("LLM did not return a JSON object — no '{' found")
    text = text[brace_idx:]

    # 4. Find matching closing '}' from the end
    rbrace_idx = text.rfind("}")
    if rbrace_idx == -1:
        raise ValueError("LLM did not return a JSON object — no '}' found")
    text = text[: rbrace_idx + 1]

    # 5. Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    return text


def validate_required_keys(
    parsed: dict,
    required_keys: list[str],
    context: str = "OpenAI",
) -> bool:
    """Check that all required keys exist in parsed dict.

    Logs missing keys and returns False if any are missing.
    """
    missing = [k for k in required_keys if k not in parsed]
    if missing:
        print(f"⚠️  [{context}] Missing required keys: {missing}")
        return False
    return True


def build_payload(
    *,
    model: str,
    messages: List[Dict[str, str]],
    max_completion_tokens: int,
    temperature: float,
) -> Dict[str, Any]:
    """Build an OpenAI chat completions payload (GPT-4.1 safe mode).

    Uses:
      - model, messages, max_tokens, temperature
      - response_format: json_object (ensures valid JSON output)
    """
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_completion_tokens,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    print(f"🧠 [OPENAI] Model: {model}")
    print(f"🧠 [OPENAI] Tokens requested: {max_completion_tokens}")

    return payload


def call_openai_chat(
    *,
    messages: List[Dict[str, str]],
    max_completion_tokens: int = 0,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Call OpenAI chat completions and return parsed JSON dict, or None on failure.

    Parameters
    ----------
    messages : list[dict]
        The messages array (system + user).
    max_completion_tokens : int
        Token limit for the response. 0 = use env default.
    api_key : str, optional
        Override API key (default: from env).
    model : str, optional
        Override model name (default: from env).

    Returns
    -------
    dict or None
        Parsed JSON response content, or None if all retries exhausted.
    """
    if api_key is None:
        api_key = get_openai_key()
    if model is None:
        model = get_openai_model()
    if max_completion_tokens <= 0:
        max_completion_tokens = _get_default_max_tokens()

    temperature = _get_temperature()
    timeout = _get_timeout()
    max_retries = 1  # 1 retry only (2 attempts total)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = build_payload(
        model=model,
        messages=messages,
        max_completion_tokens=max_completion_tokens,
        temperature=temperature,
    )

    for attempt in range(max_retries + 1):
        t0 = time.time()
        try:
            print(f"🧠 [OPENAI] Calling {model} (attempt {attempt + 1}/{max_retries + 1})")
            response = httpx.post(
                _OPENAI_API_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            duration = time.time() - t0
            print(f"📦 [OPENAI] HTTP {response.status_code} ({duration:.1f}s)")

            if response.status_code != 200:
                error_body = response.text[:400]
                print(f"⚠️  [OPENAI] Error response: {error_body}")
                if attempt < max_retries:
                    print("🔄 [OPENAI] Retrying...")
                    continue
                return None

            data = response.json()

            # Log token usage if available
            usage = data.get("usage")
            if usage:
                print(f"🧠 [OPENAI] Tokens used: prompt={usage.get('prompt_tokens', '?')}, completion={usage.get('completion_tokens', '?')}, total={usage.get('total_tokens', '?')}")

            raw_content = (data["choices"][0]["message"]["content"] or "").strip()
            print(f"🧠 [OPENAI] Raw output length: {len(raw_content)} chars")

            if not raw_content:
                print(f"⚠️  [OPENAI] Empty response (attempt {attempt + 1})")
                if attempt < max_retries:
                    continue
                return None

            # Sanitize: strip markdown fences, find JSON object
            try:
                sanitized = sanitize_json(raw_content)
            except ValueError as ve:
                print(f"❌ [OPENAI] JSON parse failed — retrying: {ve}")
                print(f"⚠️  [OPENAI] Raw (first 300 chars): {raw_content[:300]}")
                if attempt < max_retries:
                    continue
                return None

            parsed = json.loads(sanitized)
            print("🧠 [OPENAI] Success")
            return parsed

        except json.JSONDecodeError as exc:
            print(f"❌ [OPENAI] JSON parse failed — retrying: {exc}")
            if attempt < max_retries:
                continue
            return None

        except httpx.TimeoutException:
            duration = time.time() - t0
            print(f"❌ [OPENAI] Timeout — aborting ({duration:.1f}s)")
            if attempt < max_retries:
                continue
            return None

        except Exception as exc:
            print(f"❌ [OPENAI] Unexpected error: {exc}")
            return None

    return None


# ---------------------------------------------------------------------------
# Async version — identical logic, non-blocking I/O
# ---------------------------------------------------------------------------
async def call_openai_chat_async(
    *,
    messages: List[Dict[str, str]],
    max_completion_tokens: int = 0,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Async version of call_openai_chat. Same behaviour, non-blocking I/O."""
    if api_key is None:
        api_key = get_openai_key()
    if model is None:
        model = get_openai_model()
    if max_completion_tokens <= 0:
        max_completion_tokens = _get_default_max_tokens()

    temperature = _get_temperature()
    timeout = _get_timeout()
    max_retries = 1

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = build_payload(
        model=model,
        messages=messages,
        max_completion_tokens=max_completion_tokens,
        temperature=temperature,
    )

    for attempt in range(max_retries + 1):
        t0 = time.time()
        try:
            print(f"🧠 [OPENAI] Calling {model} (attempt {attempt + 1}/{max_retries + 1})")
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    _OPENAI_API_URL,
                    headers=headers,
                    json=payload,
                )
            duration = time.time() - t0
            print(f"📦 [OPENAI] HTTP {response.status_code} ({duration:.1f}s)")

            if response.status_code != 200:
                error_body = response.text[:400]
                print(f"⚠️  [OPENAI] Error response: {error_body}")
                if attempt < max_retries:
                    print("🔄 [OPENAI] Retrying...")
                    continue
                return None

            data = response.json()

            usage = data.get("usage")
            if usage:
                print(f"🧠 [OPENAI] Tokens used: prompt={usage.get('prompt_tokens', '?')}, completion={usage.get('completion_tokens', '?')}, total={usage.get('total_tokens', '?')}")

            raw_content = (data["choices"][0]["message"]["content"] or "").strip()
            print(f"🧠 [OPENAI] Raw output length: {len(raw_content)} chars")

            if not raw_content:
                print(f"⚠️  [OPENAI] Empty response (attempt {attempt + 1})")
                if attempt < max_retries:
                    continue
                return None

            try:
                sanitized = sanitize_json(raw_content)
            except ValueError as ve:
                print(f"❌ [OPENAI] JSON parse failed — retrying: {ve}")
                print(f"⚠️  [OPENAI] Raw (first 300 chars): {raw_content[:300]}")
                if attempt < max_retries:
                    continue
                return None

            parsed = json.loads(sanitized)
            print("🧠 [OPENAI] Success")
            return parsed

        except json.JSONDecodeError as exc:
            print(f"❌ [OPENAI] JSON parse failed — retrying: {exc}")
            if attempt < max_retries:
                continue
            return None

        except httpx.TimeoutException:
            duration = time.time() - t0
            print(f"❌ [OPENAI] Timeout — aborting ({duration:.1f}s)")
            if attempt < max_retries:
                continue
            return None

        except Exception as exc:
            print(f"❌ [OPENAI] Unexpected error: {exc}")
            return None

    return None
