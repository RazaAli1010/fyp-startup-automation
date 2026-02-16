"""OpenAI Structured Inference for Idea Input.

From the user's detailed business description, infer:
  - revenue_model (string)
  - technical_complexity_level (low | medium | high)
  - regulatory_risk_level (low | medium | high)
  - core_problem_keywords (list[str])
  - market_keywords (list[str])

STRICT RULES:
  - OpenAI must NOT score
  - OpenAI must NOT judge viability
  - OpenAI must ONLY output structured JSON
  - Retry once on parse failure → fallback to defaults
"""

from __future__ import annotations

from typing import Any, Optional

from .openai_client import call_openai_chat_async, get_openai_key, validate_required_keys
from ..constants import TECH_COMPLEXITY_MAP, REGULATORY_RISK_MAP, DEFAULT_PRICING, DEFAULT_PRICING_FALLBACK


# ── JSON Schema for inference output ────────────────────────────────────
_SYSTEM_PROMPT = """You are a backend data classifier. You receive a startup business description and must extract structured attributes.

You MUST respond with ONLY a valid JSON object. No markdown, no explanations, no comments.

RULES:
- Do NOT score or judge viability
- Do NOT provide opinions
- ONLY classify and extract keywords
- If uncertain, use "medium" for levels and generic keywords"""


def _build_user_prompt(
    *,
    description: str,
    industry: str,
    target_customer_type: str,
) -> str:
    """Build the structured user prompt for inference."""
    return f"""Classify this startup idea and extract structured attributes.

=== BUSINESS DESCRIPTION ===
{description}

=== CONTEXT ===
- Industry: {industry}
- Target Customer: {target_customer_type}

=== REQUIRED OUTPUT ===
Return ONLY this exact JSON structure. No other text.
{{
  "revenue_model": "<string: e.g. Subscription, Marketplace Fee, Ads, Freemium, Usage-based, One-time, Licensing, Transaction Fee>",
  "technical_complexity_level": "<low | medium | high>",
  "regulatory_risk_level": "<low | medium | high>",
  "core_problem_keywords": ["<keyword1>", "<keyword2>", "<keyword3>"],
  "market_keywords": ["<keyword1>", "<keyword2>", "<keyword3>"]
}}"""


# ── Fallback defaults ───────────────────────────────────────────────────

def _default_inference() -> dict[str, Any]:
    """Safe fallback when OpenAI is unavailable or fails."""
    return {
        "revenue_model": "Subscription",
        "technical_complexity_level": "medium",
        "regulatory_risk_level": "medium",
        "core_problem_keywords": ["startup", "automation", "efficiency"],
        "market_keywords": ["market", "growth", "demand"],
    }


# ── Public API ──────────────────────────────────────────────────────────

async def infer_idea_attributes(
    *,
    description: str,
    industry: str,
    target_customer_type: str,
) -> dict[str, Any]:
    """Infer structured attributes from the business description via OpenAI.

    Returns dict with keys:
        revenue_model, technical_complexity_level, regulatory_risk_level,
        core_problem_keywords, market_keywords

    Falls back to defaults if OpenAI is unavailable or returns invalid JSON.
    """
    print("🧠 [INFERENCE] Inferring idea attributes from description")

    try:
        get_openai_key()
    except EnvironmentError:
        print("⚠️  [INFERENCE] No OpenAI key — using defaults")
        return _default_inference()

    user_prompt = _build_user_prompt(
        description=description,
        industry=industry,
        target_customer_type=target_customer_type,
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    result = await call_openai_chat_async(
        messages=messages,
        max_completion_tokens=1000,
    )

    if result is None:
        print("⚠️  [INFERENCE] OpenAI returned None — using defaults")
        return _default_inference()

    required_keys = [
        "revenue_model",
        "technical_complexity_level",
        "regulatory_risk_level",
        "core_problem_keywords",
        "market_keywords",
    ]
    if not validate_required_keys(result, required_keys, context="INFERENCE"):
        print("⚠️  [INFERENCE] Missing required keys — using defaults")
        return _default_inference()

    # Validate levels are within expected values
    tcl = result.get("technical_complexity_level", "medium")
    if tcl not in ("low", "medium", "high"):
        print(f"⚠️  [INFERENCE] Invalid tech complexity '{tcl}' — defaulting to 'medium'")
        result["technical_complexity_level"] = "medium"

    rrl = result.get("regulatory_risk_level", "medium")
    if rrl not in ("low", "medium", "high"):
        print(f"⚠️  [INFERENCE] Invalid regulatory risk '{rrl}' — defaulting to 'medium'")
        result["regulatory_risk_level"] = "medium"

    # Ensure keyword lists are actually lists
    for key in ("core_problem_keywords", "market_keywords"):
        if not isinstance(result.get(key), list):
            result[key] = _default_inference()[key]

    print(f"✅ [INFERENCE] revenue_model={result['revenue_model']}")
    print(f"✅ [INFERENCE] tech_complexity={result['technical_complexity_level']}")
    print(f"✅ [INFERENCE] regulatory_risk={result['regulatory_risk_level']}")
    print(f"✅ [INFERENCE] problem_keywords={result['core_problem_keywords']}")
    print(f"✅ [INFERENCE] market_keywords={result['market_keywords']}")

    return result


def map_complexity_to_numeric(level: str) -> float:
    """Map inferred complexity level to 0-1 numeric value for the Idea model.

    low → 0.20, medium → 0.50, high → 0.75
    """
    return TECH_COMPLEXITY_MAP.get(level, 0.50)


def map_regulatory_to_numeric(level: str) -> float:
    """Map inferred regulatory risk level to 0-1 numeric value for the Idea model.

    low → 0.20, medium → 0.50, high → 0.80
    """
    return REGULATORY_RISK_MAP.get(level, 0.50)


def map_revenue_model_to_pricing(revenue_model: str) -> float:
    """Map inferred revenue model to a default pricing estimate (USD/month)."""
    return DEFAULT_PRICING.get(revenue_model, DEFAULT_PRICING_FALLBACK)


def normalize_revenue_model(raw: str) -> str:
    """Normalize the LLM-inferred revenue model to a known category.

    Falls back to 'Subscription' if unrecognized.
    """
    raw_lower = raw.strip().lower()
    mapping = {
        "subscription": "Subscription",
        "saas": "Subscription",
        "one-time": "One-time",
        "one time": "One-time",
        "marketplace fee": "Marketplace Fee",
        "marketplace": "Marketplace Fee",
        "ads": "Ads",
        "advertising": "Ads",
        "freemium": "Subscription",
        "usage-based": "Subscription",
        "usage based": "Subscription",
        "licensing": "One-time",
        "transaction fee": "Marketplace Fee",
        "transaction": "Marketplace Fee",
    }
    normalized = mapping.get(raw_lower)
    if normalized:
        return normalized

    # Fuzzy fallback: check if any known key is a substring
    for key, val in mapping.items():
        if key in raw_lower:
            return val

    print(f"⚠️  [INFERENCE] Unknown revenue model '{raw}' — defaulting to 'Subscription'")
    return "Subscription"
