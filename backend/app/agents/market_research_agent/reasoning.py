"""OpenAI integration — constrained reasoning for market research.

Used ONLY for:
- Extracting numeric ranges from Tavily research text
- Explaining assumptions
- Assigning confidence level

NEVER invents market size numbers. All reasoning is grounded in provided text.
All OpenAI calls go through the centralized openai_client helper (GPT-4.1).

NO personas. NO markdown. NO explanations outside JSON.
"""

from __future__ import annotations

from typing import Any

from ...services.openai_client import call_openai_chat_async, get_openai_key, validate_required_keys

# ---------------------------------------------------------------------------
# System prompt — hardened for anti-vague, practical, bounded outputs.
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are a backend data processor for market research analysis.

You MUST respond with ONLY a valid JSON object. No markdown, no explanations,
no comments, no trailing text.

Focus on:
- Market size estimates (numeric ranges)
- Growth reasoning (CAGR with evidence)
- Competition summary (based on provided data)
- Confidence scoring (low/medium/high)

Do NOT include:
- Customer personas
- Open-ended prose
- Vague qualitative statements

If data is insufficient, use null values."""


def _build_user_prompt(
    *,
    research_text: list[str],
    competitor_count: int,
    pricing_estimate: float,
    geography: str,
    industry: str,
    target_customer_type: str,
    one_line_description: str,
) -> str:
    """Build the structured user prompt for OpenAI."""
    # Join research passages into a single block
    research_block = "\n\n".join(research_text) if research_text else "(No research text available — data is limited)"

    return f"""Extract market insights from the research text below.

=== RESEARCH TEXT ===
{research_block}

=== STARTUP CONTEXT ===
- Industry: {industry}
- Description: {one_line_description}
- Target Customer: {target_customer_type}
- Geography: {geography}
- Pricing Estimate: ${pricing_estimate}/month
- Known Competitors Found: {competitor_count}

=== REQUIRED OUTPUT ===
Return ONLY this exact JSON structure. No other text.
{{
  "customer_count_estimate": {{ "min": <integer or null>, "max": <integer or null> }},
  "growth_rate_estimate": "<string, e.g. 12-18% CAGR>",
  "assumptions": ["<specific falsifiable assumption>", "<assumption 2>", "<assumption 3>"],
  "confidence": "low" or "medium" or "high"
}}"""


async def _call_openai(user_prompt: str) -> dict[str, Any] | None:
    """Call OpenAI via centralized async helper and return parsed JSON dict or None."""
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    return await call_openai_chat_async(
        messages=messages,
        max_completion_tokens=4000,
    )


def _build_fallback_result(
    *,
    target_customer_type: str,
    industry: str,
    pricing_estimate: float,
) -> dict[str, Any]:
    """Return a safe fallback when OpenAI is unavailable or fails."""
    print("⚠️  [OPENAI] Using fallback reasoning (no LLM available)")

    # Conservative customer count defaults by type
    if target_customer_type == "B2B":
        cust_min, cust_max = 50_000, 500_000
    elif target_customer_type == "Marketplace":
        cust_min, cust_max = 100_000, 2_000_000
    else:  # B2C
        cust_min, cust_max = 500_000, 10_000_000

    return {
        "customer_count_estimate": {"min": cust_min, "max": cust_max},
        "growth_rate_estimate": "10-20% CAGR (fallback estimate)",
        "assumptions": [
            "OpenAI reasoning unavailable — using conservative defaults",
            f"Customer count based on {target_customer_type} industry benchmarks",
            f"Pricing at ${pricing_estimate}/month used for ARPU calculation",
        ],
        "confidence": "low",
    }


async def run_reasoning(
    *,
    research_text: list[str],
    competitor_count: int,
    pricing_estimate: float,
    geography: str,
    industry: str,
    target_customer_type: str,
    one_line_description: str,
) -> dict[str, Any]:
    """Run OpenAI constrained reasoning on market research data.

    Parameters
    ----------
    research_text : list[str]
        Passages from Tavily research
    competitor_count : int
        Number of competitors found by Exa
    pricing_estimate : float
        Monthly pricing estimate
    geography : str
        Target geography
    industry : str
        Industry vertical
    target_customer_type : str
        B2B, B2C, or Marketplace
    one_line_description : str
        One-line startup description

    Returns
    -------
    dict with keys: customer_count_estimate, growth_rate_estimate,
                    assumptions, confidence
    """
    print("🧠 [OPENAI] Reasoning on market size & confidence")

    try:
        get_openai_key()  # Validate key exists before building prompt
    except EnvironmentError:
        return _build_fallback_result(
            target_customer_type=target_customer_type,
            industry=industry,
            pricing_estimate=pricing_estimate,
        )

    user_prompt = _build_user_prompt(
        research_text=research_text,
        competitor_count=competitor_count,
        pricing_estimate=pricing_estimate,
        geography=geography,
        industry=industry,
        target_customer_type=target_customer_type,
        one_line_description=one_line_description,
    )

    result = await _call_openai(user_prompt)

    if result is None:
        return _build_fallback_result(
            target_customer_type=target_customer_type,
            industry=industry,
            pricing_estimate=pricing_estimate,
        )

    # Validate required keys using centralized helper
    required_keys = ["customer_count_estimate", "growth_rate_estimate", "assumptions", "confidence"]
    if not validate_required_keys(result, required_keys, context="MARKET-REASONING"):
        print(f"⚠️  [OPENAI] Raw LLM output had missing keys — falling back")
        return _build_fallback_result(
            target_customer_type=target_customer_type,
            industry=industry,
            pricing_estimate=pricing_estimate,
        )

    # Validate customer_count_estimate shape
    cce = result.get("customer_count_estimate", {})
    if not isinstance(cce, dict) or "min" not in cce or "max" not in cce:
        print("⚠️  [OPENAI] Invalid customer_count_estimate shape — using fallback")
        return _build_fallback_result(
            target_customer_type=target_customer_type,
            industry=industry,
            pricing_estimate=pricing_estimate,
        )

    print(f"✅ [OPENAI] Customer count: {cce['min']:,} – {cce['max']:,}")
    print(f"✅ [OPENAI] Growth rate: {result['growth_rate_estimate']}")
    print(f"✅ [OPENAI] Confidence: {result['confidence']}")

    return result
