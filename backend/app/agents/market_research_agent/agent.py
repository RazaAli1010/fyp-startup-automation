"""Market Research Agent v2 — orchestrates Tavily + Exa + OpenAI + Calculator.

Entry point: run_market_research(idea) -> MarketResearchResult

Flow:
  1. Fetch Tavily research text (market size, growth, reports)
  2. Fetch Exa competitors (semantic discovery)
  3. Call OpenAI reasoning (extract ranges, confidence)
  4. Run deterministic TAM/SAM/SOM calculator
  5. Build unified result

No personas. If any step fails, agent continues with degraded confidence — never crashes.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from .calculator import MarketSizeResult, calculate_market_size
from .competitors import fetch_competitors
from .reasoning import run_reasoning
from .research import fetch_market_research_text


@dataclass
class MarketResearchResult:
    """Full output of the market research agent."""

    tam_min: float
    tam_max: float
    sam_min: float
    sam_max: float
    som_min: float
    som_max: float
    arpu_annual: float
    growth_rate_estimate: float
    demand_strength: float
    assumptions: list[str]
    confidence: dict[str, Any]
    sources: list[str]
    competitors: list[dict[str, Any]] = field(default_factory=list)
    competitor_count: int = 0


def _compute_demand_strength(
    *,
    growth_rate_min: float,
    growth_rate_max: float,
    som_min: float,
    som_max: float,
    pricing_estimate: float,
    competitor_count: int,
) -> float:
    """Compute a 0–100 demand strength score from growth, SOM, and competition."""
    avg_growth = (growth_rate_min + growth_rate_max) / 2.0
    # Normalize growth to 0–40 range (30% growth = 40 points)
    growth_score = min(avg_growth / 30.0 * 40.0, 40.0)

    # SOM size contributes 0–25 points ($100M+ SOM_max = 25 points)
    som_avg = (som_min + som_max) / 2.0
    som_score = min(som_avg / 100_000_000 * 25.0, 25.0)

    # Pricing reasonableness contributes 0–15 points
    if 10 <= pricing_estimate <= 500:
        price_score = 15.0
    elif pricing_estimate < 10:
        price_score = 8.0
    else:
        price_score = 12.0

    # Competition signal: 3-10 competitors = healthy market = +20 pts
    if 3 <= competitor_count <= 10:
        comp_score = 20.0
    elif competitor_count > 10:
        comp_score = 15.0  # crowded but validated
    elif competitor_count > 0:
        comp_score = 10.0  # emerging
    else:
        comp_score = 5.0  # unvalidated

    return round(min(growth_score + som_score + price_score + comp_score, 100.0), 1)


def _compute_confidence(
    *,
    calc: MarketSizeResult,
    industry: str,
    geography: str,
    customer_size: str,
    openai_confidence: str,
    has_tavily_data: bool,
    has_exa_data: bool,
) -> dict[str, Any]:
    """Compute confidence scores based on data quality from all sources."""
    known_industries = {
        "SaaS", "Fintech", "Healthtech", "E-commerce", "AI/ML",
        "Marketplace", "Enterprise", "Saas/Marketplace",
    }

    # Base TAM confidence from industry recognition
    tam_base = 70 if industry in known_industries else 45
    # Boost if Tavily provided real data
    tam_boost = 15 if has_tavily_data else 0
    tam_confidence = min(tam_base + tam_boost, 90)
    tam_explanation = (
        f"Industry '{industry}' — "
        + ("well-documented market data" if industry in known_industries else "limited public data")
        + (" + Tavily research passages available" if has_tavily_data else " (no external research data)")
    )

    # SAM confidence
    sam_base = 65 if geography != "Global" else 55
    sam_boost = 10 if has_exa_data else 0
    sam_confidence = min(sam_base + sam_boost, 85)
    sam_explanation = (
        f"Geography '{geography}' — "
        + ("clear market boundary" if geography != "Global" else "global scope increases uncertainty")
        + (" + competitor data validates segment" if has_exa_data else "")
    )

    # SOM confidence — always conservative
    som_confidence = 45
    som_explanation = (
        "SOM is speculative for pre-revenue startups. "
        "Actual capture depends on execution, timing, and competition."
    )

    # Adjust overall based on OpenAI confidence signal
    confidence_map = {"high": 10, "medium": 5, "low": -5}
    openai_adj = confidence_map.get(openai_confidence, 0)

    overall = round(
        (tam_confidence + sam_confidence + som_confidence) / 3.0 + openai_adj, 0
    )
    overall = max(10, min(overall, 95))

    data_sources_used = []
    if has_tavily_data:
        data_sources_used.append("Tavily research")
    if has_exa_data:
        data_sources_used.append("Exa competitor data")
    data_sources_used.append("deterministic calculator")

    return {
        "overall": overall,
        "tam": {"score": tam_confidence, "explanation": tam_explanation},
        "sam": {"score": sam_confidence, "explanation": sam_explanation},
        "som": {"score": som_confidence, "explanation": som_explanation},
        "note": (
            f"Estimates use {', '.join(data_sources_used)}. "
            f"OpenAI confidence: {openai_confidence}."
        ),
    }


def _build_sources(
    *,
    industry: str,
    geography: str,
    has_tavily_data: bool,
    has_exa_data: bool,
    tavily_passage_count: int,
    competitor_count: int,
) -> list[str]:
    """Return list of data sources actually used."""
    sources = []
    if has_tavily_data:
        sources.append(f"Tavily advanced search ({tavily_passage_count} research passages)")
    if has_exa_data:
        sources.append(f"Exa semantic competitor discovery ({competitor_count} competitors)")
    sources.append("OpenAI constrained reasoning (range extraction & confidence)")
    sources.append(f"Deterministic calculator (industry: {industry}, geography: {geography})")
    sources.append("Revenue model growth rate benchmarks")
    return sources


async def run_market_research(
    *,
    startup_name: str,
    one_line_description: str,
    industry: str,
    target_customer_type: str,
    geography: str,
    customer_size: str,
    revenue_model: str,
    pricing_estimate: float,
    team_size: int,
) -> MarketResearchResult:
    """Run the full market research pipeline (v2, async).

    1. Fetch Tavily research text + Exa competitors IN PARALLEL
    2. Call OpenAI reasoning (depends on step 1 results)
    3. Run deterministic TAM/SAM/SOM calculator
    4. Return unified result
    """
    print(f" [MR] Pipeline START: {startup_name} | {industry} | {geography} | {target_customer_type}")

    # ── Steps 1 & 2: Fetch Tavily + Exa IN PARALLEL ─────────
    print(" [MR] Steps 1-2/4: Tavily + Exa in parallel")

    async def _tavily_task() -> list[str]:
        try:
            return await fetch_market_research_text({
                "industry": industry,
                "one_line_description": one_line_description,
                "geography": geography,
                "startup_name": startup_name,
                "target_customer_type": target_customer_type,
            })
        except Exception as exc:
            print(f" [MR] Tavily failed: {exc}")
            return []

    async def _exa_task() -> dict:
        try:
            return await fetch_competitors({
                "startup_name": startup_name,
                "one_line_description": one_line_description,
                "industry": industry,
                "target_customer_type": target_customer_type,
                "revenue_model": revenue_model,
            })
        except Exception as exc:
            print(f" [MR] Exa failed: {exc}")
            return {"competitors": [], "competitor_count": 0}

    tavily_result, exa_result = await asyncio.gather(
        _tavily_task(),
        _exa_task(),
        return_exceptions=True,
    )

    research_passages = tavily_result if isinstance(tavily_result, list) else []
    if isinstance(exa_result, Exception):
        exa_result = {"competitors": [], "competitor_count": 0}
    has_tavily = len(research_passages) > 0
    competitors = exa_result.get("competitors", [])
    competitor_count = exa_result.get("competitor_count", 0)
    has_exa = competitor_count > 0
    print(f"{'' if has_tavily else ''} [MR] Tavily: {len(research_passages)} passages")
    print(f"{'' if has_exa else ''} [MR] Exa: {competitor_count} competitors")

    # ── Step 3: Call OpenAI reasoning (depends on Tavily + Exa results) ─
    try:
        reasoning = await run_reasoning(
            research_text=research_passages,
            competitor_count=competitor_count,
            pricing_estimate=pricing_estimate,
            geography=geography,
            industry=industry,
            target_customer_type=target_customer_type,
            one_line_description=one_line_description,
        )
    except Exception as exc:
        print(f"⚠️  [MR] OpenAI failed: {exc}")
        reasoning = {
            "customer_count_estimate": None,
            "growth_rate_estimate": "unknown",
            "assumptions": [f"OpenAI reasoning failed: {exc}"],
            "confidence": "low",
        }
    openai_confidence = reasoning.get("confidence", "low")
    print(f"🧠 [MR] LLM confidence: {openai_confidence}")

    # ── Step 4: Run deterministic calculator ───────────────────
    print("🔬 [MR] Step 4/4: Deterministic calculator")

    # Extract customer_count from OpenAI if available
    cce = reasoning.get("customer_count_estimate")
    cust_min = None
    cust_max = None
    if isinstance(cce, dict) and "min" in cce and "max" in cce:
        try:
            cust_min = int(cce["min"])
            cust_max = int(cce["max"])
        except (ValueError, TypeError):
            cust_min = None
            cust_max = None

    calc = calculate_market_size(
        industry=industry,
        geography=geography,
        customer_size=customer_size,
        revenue_model=revenue_model,
        pricing_estimate=pricing_estimate,
        team_size=team_size,
        customer_count_min=cust_min,
        customer_count_max=cust_max,
    )
    print("✅ [MR] Calculations complete")

    # ── Compute demand strength ────────────────────────────────
    demand = _compute_demand_strength(
        growth_rate_min=calc.growth_rate_min,
        growth_rate_max=calc.growth_rate_max,
        som_min=calc.som_min,
        som_max=calc.som_max,
        pricing_estimate=pricing_estimate,
        competitor_count=competitor_count,
    )

    # ── Build confidence ───────────────────────────────────────
    confidence = _compute_confidence(
        calc=calc,
        industry=industry,
        geography=geography,
        customer_size=customer_size,
        openai_confidence=openai_confidence,
        has_tavily_data=has_tavily,
        has_exa_data=has_exa,
    )

    # ── Merge assumptions ──────────────────────────────────────
    all_assumptions = list(calc.assumptions)
    openai_assumptions = reasoning.get("assumptions", [])
    if openai_assumptions:
        all_assumptions.extend(openai_assumptions)

    # ── Build sources ──────────────────────────────────────────
    sources = _build_sources(
        industry=industry,
        geography=geography,
        has_tavily_data=has_tavily,
        has_exa_data=has_exa,
        tavily_passage_count=len(research_passages),
        competitor_count=competitor_count,
    )

    avg_growth = (calc.growth_rate_min + calc.growth_rate_max) / 2.0

    print(f"✅ [MR] COMPLETE: TAM=${calc.tam_min/1e9:.1f}–{calc.tam_max/1e9:.1f}B, "
          f"SOM=${calc.som_min/1e6:.1f}–{calc.som_max/1e6:.1f}M, "
          f"Demand={demand}/100, Growth={avg_growth:.1f}%, "
          f"Confidence={confidence['overall']}/100")

    return MarketResearchResult(
        tam_min=calc.tam_min,
        tam_max=calc.tam_max,
        sam_min=calc.sam_min,
        sam_max=calc.sam_max,
        som_min=calc.som_min,
        som_max=calc.som_max,
        arpu_annual=calc.arpu_annual,
        growth_rate_estimate=avg_growth,
        demand_strength=demand,
        assumptions=all_assumptions,
        confidence=confidence,
        sources=sources,
        competitors=competitors,
        competitor_count=competitor_count,
    )
