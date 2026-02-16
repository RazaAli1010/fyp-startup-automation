"""MVP Generator Agent — deterministic MVP blueprint generation.

Consumes validated idea + market research + evaluation scores.
No LLM calls, no randomness. Pure rule-based decisions.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .rules import (
    MVPDecisionContext,
    decide_build_plan,
    decide_core_features,
    decide_excluded_features,
    decide_mvp_type,
    decide_risk_notes,
    decide_tech_stack,
    decide_user_flow,
    decide_validation_plan,
)
from .schema import MVPBlueprint


def generate_mvp_blueprint(
    *,
    # Idea fields
    startup_name: str,
    one_line_description: str,
    industry: str,
    target_customer_type: str,
    geography: str,
    customer_size: str,
    revenue_model: str,
    pricing_estimate: float,
    team_size: int,
    tech_complexity: float,
    regulatory_risk: float,
    # Evaluation scores
    problem_intensity: float,
    market_timing: float,
    competition_pressure: float,
    market_potential: float,
    execution_feasibility: float,
    final_viability_score: float,
    # Market research
    market_confidence: str,
    competitors: Optional[List[Dict[str, Any]]] = None,
    competitor_count: int = 0,
) -> MVPBlueprint:
    """Generate a complete MVP blueprint using deterministic rules.

    Raises
    ------
    ValueError
        If required inputs are missing or invalid.
    """
    print(f"🛠️ [MVP] Generating MVP for startup={startup_name}")
    print(f"📦 [MVP] Using validated idea + market research")

    # ── Build decision context ────────────────────────────────
    ctx = MVPDecisionContext(
        startup_name=startup_name,
        one_line_description=one_line_description,
        industry=industry,
        target_customer_type=target_customer_type,
        geography=geography,
        customer_size=customer_size,
        revenue_model=revenue_model,
        pricing_estimate=pricing_estimate,
        team_size=team_size,
        tech_complexity=tech_complexity,
        regulatory_risk=regulatory_risk,
        problem_intensity=problem_intensity,
        market_timing=market_timing,
        competition_pressure=competition_pressure,
        market_potential=market_potential,
        execution_feasibility=execution_feasibility,
        final_viability_score=final_viability_score,
        market_confidence=market_confidence,
        competitors=competitors or [],
        competitor_count=competitor_count,
    )

    # ── Apply deterministic rules ─────────────────────────────
    mvp_type = decide_mvp_type(ctx)
    print(f"🛠️ [MVP] Selected type: {mvp_type}")

    core_features = decide_core_features(ctx)
    excluded_features = decide_excluded_features(ctx)
    user_flow = decide_user_flow(ctx)
    tech_stack = decide_tech_stack(ctx)
    build_plan = decide_build_plan(ctx)
    validation_plan = decide_validation_plan(ctx)
    risk_notes = decide_risk_notes(ctx)

    # ── Build hypothesis ──────────────────────────────────────
    core_hypothesis = (
        f"If we build a {mvp_type.lower()} for {target_customer_type} users in {industry}, "
        f"solving '{one_line_description}', then we can validate demand and achieve "
        f"product-market fit within the first 4-6 weeks of launch."
    )

    # ── Primary user ──────────────────────────────────────────
    size_label = {
        "Individual": "individual consumers",
        "SMB": "small and medium businesses",
        "Mid-Market": "mid-market companies",
        "Enterprise": "enterprise organizations",
    }.get(customer_size, customer_size)

    primary_user = f"{target_customer_type} — {size_label} in {industry} ({geography})"

    # ── Assemble blueprint ────────────────────────────────────
    blueprint = MVPBlueprint(
        mvp_type=mvp_type,
        core_hypothesis=core_hypothesis,
        primary_user=primary_user,
        core_features=core_features,
        excluded_features=excluded_features,
        user_flow=user_flow,
        recommended_tech_stack=tech_stack,
        build_plan=build_plan,
        validation_plan=validation_plan,
        risk_notes=risk_notes,
    )

    print(f"✅ [MVP] MVP blueprint generated — type={mvp_type}, features={len(core_features)}")

    return blueprint
