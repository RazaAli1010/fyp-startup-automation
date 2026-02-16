"""Pitch Deck Generator — Alai Slides API, no silent fallbacks.

Consumes idea details and Idea Validation Agent results to produce
an investor-ready pitch deck presentation via the Alai Slides API.

Strategy:
  1. Require Alai API key
  2. Build input_text from idea + validation data
  3. Call Alai Slides API (POST /generations → poll → extract links)
  4. Return generation_id, view_url, pdf_url
  5. Fail loudly if anything goes wrong — NO silent fallback
"""

from __future__ import annotations

from .schema import (
    IdeaContext,
    ModuleScoresContext,
    PitchDeckInput,
    PitchDeckOutput,
    ValidationContext,
)

from ...services.alai_client import AlaiError, generate_pitch_deck_via_alai, is_alai_available


# ── Input text builder ───────────────────────────────────────────────────

def _build_input_text(ctx: PitchDeckInput) -> str:
    """Build the input_text string for the Alai Slides API.

    Combines idea description, validation signals, key strength/risk,
    and market timing into a structured text prompt.
    """
    idea = ctx.idea
    val = ctx.validation
    ms = val.module_scores

    lines = [
        f"Startup: {idea.name}",
        f"Industry: {idea.industry}",
        f"Description: {idea.description}",
        f"Target Customer: {idea.target_customer}",
        f"Geography: {idea.geography}",
        f"Revenue Model: {idea.revenue_model}",
        f"Pricing: ${idea.pricing_estimate:.0f}",
        f"Team Size: {idea.team_size}",
        "",
        "--- Validation Results ---",
        f"Overall Score: {val.final_score:.1f}/100 ({val.verdict})",
        f"Risk Level: {val.risk_level}",
        f"Key Strength: {val.key_strength}",
        f"Key Risk: {val.key_risk}",
        "",
        "--- Module Scores ---",
        f"Problem Intensity: {ms.problem_intensity:.1f}/100",
        f"Market Timing: {ms.market_timing:.1f}/100",
        f"Competition Pressure: {ms.competition_pressure:.1f}/100",
        f"Market Potential: {ms.market_potential:.1f}/100",
        f"Execution Feasibility: {ms.execution_feasibility:.1f}/100",
        "",
        "--- Instructions ---",
        "Create a professional, investor-grade pitch deck presentation.",
        "Use factual data only. Do not fabricate metrics or traction numbers.",
        "Tone: professional, concise, data-driven.",
        "Include slides for: problem, solution, market opportunity, business model,",
        "competitive landscape, traction/next steps, risks & mitigation, and the ask.",
    ]

    # Add conservative guidance for low scores
    if val.final_score < 55:
        lines.append("NOTE: This is an early-stage concept. Use conservative language.")
        lines.append("Avoid hype, unsubstantiated claims, or aggressive projections.")

    if ms.problem_intensity < 40:
        lines.append("NOTE: Problem intensity is low. Emphasize market education and awareness needs.")

    if ms.market_timing >= 65:
        lines.append("NOTE: Market timing is favorable. Highlight the timing advantage.")

    return "\n".join(lines)


# ── Public entry point ───────────────────────────────────────────────────

def generate_pitch_deck(
    *,
    idea_name: str,
    idea_description: str,
    idea_industry: str,
    idea_target_customer: str,
    idea_geography: str,
    idea_revenue_model: str,
    idea_pricing_estimate: float,
    idea_team_size: int,
    final_score: float,
    verdict: str,
    risk_level: str,
    key_strength: str,
    key_risk: str,
    problem_intensity: float,
    market_timing: float,
    competition_pressure: float,
    market_potential: float,
    execution_feasibility: float,
) -> PitchDeckOutput:
    """Generate a pitch deck via Alai Slides API.

    Builds input_text from idea + validation data, calls Alai to create
    a presentation, polls until complete, and returns links.
    Fails loudly — NO silent fallback.
    """
    print("============================================================")
    print("🎯 [PITCH] Pitch deck generation STARTED")
    print(f"🎯 [PITCH] Idea: {idea_name}")
    print(f"🎯 [PITCH] Score: {final_score:.1f}, Verdict: {verdict}")
    print("============================================================")

    ctx = PitchDeckInput(
        idea=IdeaContext(
            name=idea_name,
            description=idea_description,
            industry=idea_industry,
            target_customer=idea_target_customer,
            geography=idea_geography,
            revenue_model=idea_revenue_model,
            pricing_estimate=idea_pricing_estimate,
            team_size=idea_team_size,
        ),
        validation=ValidationContext(
            final_score=final_score,
            verdict=verdict,
            risk_level=risk_level,
            key_strength=key_strength,
            key_risk=key_risk,
            module_scores=ModuleScoresContext(
                problem_intensity=problem_intensity,
                market_timing=market_timing,
                competition_pressure=competition_pressure,
                market_potential=market_potential,
                execution_feasibility=execution_feasibility,
            ),
        ),
    )

    # ── Check Alai availability ──────────────────────────────
    if not is_alai_available():
        print("❌ [PITCH] ALAI_API_KEY is NOT set — cannot generate pitch deck")
        raise AlaiError("Alai API key missing — pitch deck generation unavailable")

    # ── Build input_text ─────────────────────────────────────
    input_text = _build_input_text(ctx)
    print("🎯 [PITCH] Built input_text for Alai Slides API")
    print(f"🎯 [PITCH] input_text length: {len(input_text)} chars")

    # ── Call Alai Slides API ─────────────────────────────────
    print("🎯 [PITCH] Calling Alai Slides API client")
    result = generate_pitch_deck_via_alai(
        input_text=input_text,
        deck_title=idea_name,
    )

    # ── Validate result ──────────────────────────────────────
    if not result or not isinstance(result, dict):
        print("❌ [PITCH] Invalid result received from Alai")
        raise AlaiError("Alai returned empty or invalid result")

    generation_id = result.get("generation_id", "")
    view_url = result.get("view_url", "")
    pdf_url = result.get("pdf_url", "")

    if not generation_id or not view_url or not pdf_url:
        print(f"❌ [PITCH] Missing fields in Alai result: {result}")
        raise AlaiError("Alai result missing required fields (generation_id, view_url, pdf_url)")

    # ── Build tagline ────────────────────────────────────────
    if final_score >= 75:
        qualifier = "A validated opportunity"
    elif final_score >= 55:
        qualifier = "An emerging opportunity"
    else:
        qualifier = "An early-stage concept"
    tagline = f"{qualifier} in {idea_industry} — {idea_description}"

    # ── Build output ─────────────────────────────────────────
    deck = PitchDeckOutput(
        deck_title=idea_name,
        tagline=tagline,
        slides=[],
        provider="alai",
        generation_id=generation_id,
        view_url=view_url,
        pdf_url=pdf_url,
    )

    print("📦 [PITCH] Pitch deck generation COMPLETE")
    print(f"📦 [PITCH] Title: {deck.deck_title}")
    print(f"📦 [PITCH] Tagline: {deck.tagline}")
    print(f"📦 [PITCH] Provider: {deck.provider}")
    print(f"📦 [PITCH] generation_id: {deck.generation_id}")
    print(f"📦 [PITCH] view_url: {deck.view_url}")
    print(f"📦 [PITCH] pdf_url: {deck.pdf_url}")
    print("============================================================")

    return deck
