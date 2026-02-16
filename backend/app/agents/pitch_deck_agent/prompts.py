"""Prompt templates for pitch deck slide generation.

Contains both:
1. Rule-based string templates (deterministic fallback)
2. Alai API prompt builder (structured LLM prompt with deterministic rules)
"""

from __future__ import annotations

from typing import Any

from .schema import PitchDeckInput


# ── Alai API prompt construction ─────────────────────────────────────────

ALAI_SYSTEM_INSTRUCTION = """\
You are an investor pitch deck generator for early-stage startups.

RULES — you MUST follow all of these:
1. Output valid JSON ONLY — no markdown, no explanation, no preamble.
2. Follow the provided output schema EXACTLY.
3. Be conservative and realistic. Do NOT invent revenue, traction, funding, or user numbers.
4. Do NOT claim the startup has customers, revenue, or product traction unless explicitly stated in the input.
5. All content must be derived from the provided idea details and validation signals.
6. Use professional, investor-grade language.
7. Each slide must have 2-4 bullet points.
8. The tagline must be a single sentence.

OUTPUT SCHEMA:
{
  "deck_title": "string — startup name",
  "tagline": "string — one-line value proposition",
  "slides": [
    {
      "type": "problem | solution | market | business_model | competition | traction | risks | ask",
      "title": "string — slide heading",
      "content": ["string — bullet point", "string — bullet point"]
    }
  ]
}

REQUIRED SLIDES (in order): problem, solution, market, business_model, competition, traction, risks, ask.
"""


def build_alai_payload(ctx: PitchDeckInput) -> dict[str, Any]:
    """Build the structured input payload for the Alai API.

    Applies deterministic rules BEFORE sending to Alai so the LLM
    receives explicit guidance based on validation scores.
    """
    ms = ctx.validation.module_scores

    # ── Deterministic rule-based guidance ─────────────────────
    guidance: list[str] = []

    if ms.problem_intensity < 40:
        guidance.append(
            "IMPORTANT: Problem intensity is LOW (<40). The 'problem' slide MUST "
            "emphasize that market awareness is still emerging and significant "
            "customer education will be required. The 'risks' slide MUST include "
            "low problem awareness as a key risk."
        )

    if ms.market_timing > 60:
        guidance.append(
            "Market timing is FAVORABLE (>60). The 'market' slide MUST highlight "
            "timing advantage — growth trends and demand momentum support entry now."
        )

    if ms.competition_pressure < 40:
        guidance.append(
            "Competition pressure is HIGH (low openness score <40). The 'competition' "
            "slide MUST emphasize the need for clear differentiation and niche-entry "
            "strategy against strong incumbents."
        )
    elif ms.competition_pressure >= 70:
        guidance.append(
            "Competition pressure is LOW (high openness score >=70). The 'competition' "
            "slide should highlight significant whitespace and first-mover advantage."
        )

    if ctx.validation.final_score < 50:
        guidance.append(
            "CRITICAL: Final validation score is BELOW 50. Use CONSERVATIVE language "
            "throughout. Do NOT make aggressive growth claims. The 'ask' slide should "
            "request advisory support and small-scale validation funding only. "
            "The 'traction' slide must state that no traction data is available."
        )
    elif ctx.validation.final_score >= 75:
        guidance.append(
            "Final validation score is STRONG (>=75). Confident language is acceptable "
            "but still grounded in validated signals — no invented metrics."
        )

    if ms.execution_feasibility < 40:
        guidance.append(
            "Execution feasibility is LOW (<40). The 'risks' slide MUST flag "
            "technical complexity or regulatory barriers as significant concerns."
        )

    return {
        "idea": {
            "name": ctx.idea.name,
            "description": ctx.idea.description,
            "industry": ctx.idea.industry,
            "target_customer": ctx.idea.target_customer,
            "geography": ctx.idea.geography,
            "revenue_model": ctx.idea.revenue_model,
            "pricing_estimate": ctx.idea.pricing_estimate,
            "team_size": ctx.idea.team_size,
        },
        "validation": {
            "final_score": ctx.validation.final_score,
            "verdict": ctx.validation.verdict,
            "risk_level": ctx.validation.risk_level,
            "key_strength": ctx.validation.key_strength,
            "key_risk": ctx.validation.key_risk,
            "module_scores": {
                "problem_intensity": ms.problem_intensity,
                "market_timing": ms.market_timing,
                "competition_pressure": ms.competition_pressure,
                "market_potential": ms.market_potential,
                "execution_feasibility": ms.execution_feasibility,
            },
        },
        "rules": {
            "no_revenue_claims": True,
            "no_traction_claims": True,
            "conservative_language": ctx.validation.final_score < 50,
        },
        "guidance": guidance,
    }


# ── Helper: tone qualifier based on final score ──────────────────────────

def _tone(score: float) -> str:
    """Return a conservative or confident qualifier based on final score."""
    if score >= 75:
        return "strong"
    if score >= 55:
        return "moderate"
    return "early-stage"


def _score_label(score: float) -> str:
    """Human-readable label for a 0-100 module score."""
    if score >= 70:
        return "high"
    if score >= 45:
        return "moderate"
    return "low"


# ── Slide builders ───────────────────────────────────────────────────────

def build_title_bullets(ctx: PitchDeckInput) -> list[str]:
    return [
        f"Industry: {ctx.idea.industry}",
        f"Target: {ctx.idea.target_customer} customers in {ctx.idea.geography}",
        f"Validation Score: {ctx.validation.final_score:.1f}/100 ({ctx.validation.verdict})",
    ]


def build_problem_bullets(ctx: PitchDeckInput) -> list[str]:
    bullets: list[str] = []
    pi = ctx.validation.module_scores.problem_intensity

    if pi < 40:
        bullets.append(
            "Market awareness of this problem is still emerging — "
            "significant education and awareness effort will be required"
        )
        bullets.append(
            f"Problem intensity score: {pi:.0f}/100 — indicates the pain point "
            "is not yet widely recognized by target customers"
        )
    elif pi < 60:
        bullets.append(
            f"Moderate problem intensity detected ({pi:.0f}/100) — "
            "real user pain exists but is not yet acute"
        )
        bullets.append(
            "Early adopters acknowledge the pain point; broader market "
            "validation is still needed"
        )
    else:
        bullets.append(
            f"Strong problem signal detected ({pi:.0f}/100) — "
            "target users actively seek solutions"
        )
        bullets.append(
            "Community discussions and complaint volumes confirm "
            "genuine, recurring pain in this space"
        )

    bullets.append(f"{ctx.idea.description}")
    return bullets


def build_solution_bullets(ctx: PitchDeckInput) -> list[str]:
    tone = _tone(ctx.validation.final_score)
    bullets = [
        f"{ctx.idea.name} addresses this gap for {ctx.idea.target_customer} "
        f"customers in the {ctx.idea.industry} space",
        f"Revenue model: {ctx.idea.revenue_model} at ~${ctx.idea.pricing_estimate:.0f} price point",
    ]
    if tone == "early-stage":
        bullets.append(
            "This is an early-stage concept — further validation of "
            "product-market fit is recommended before scaling"
        )
    elif tone == "moderate":
        bullets.append(
            "Signals suggest a viable opportunity worth pursuing with "
            "focused MVP development"
        )
    else:
        bullets.append(
            "Validation signals indicate strong alignment between the "
            "proposed solution and market needs"
        )
    return bullets


def build_market_bullets(ctx: PitchDeckInput) -> list[str]:
    mp = ctx.validation.module_scores.market_potential
    mt = ctx.validation.module_scores.market_timing
    bullets = [
        f"Market potential score: {mp:.0f}/100 ({_score_label(mp)})",
    ]

    if mt > 60:
        bullets.append(
            f"Favorable market timing detected ({mt:.0f}/100) — "
            "growth trends and demand momentum support entry now"
        )
    elif mt > 40:
        bullets.append(
            f"Market timing is adequate ({mt:.0f}/100) — "
            "no strong urgency but conditions are acceptable"
        )
    else:
        bullets.append(
            f"Market timing score is low ({mt:.0f}/100) — "
            "consider whether the market is ready for this solution"
        )

    bullets.append(
        f"Target geography: {ctx.idea.geography} | "
        f"Customer segment: {ctx.idea.target_customer}"
    )
    return bullets


def build_business_model_bullets(ctx: PitchDeckInput) -> list[str]:
    return [
        f"Revenue model: {ctx.idea.revenue_model}",
        f"Estimated pricing: ~${ctx.idea.pricing_estimate:.0f} per unit/period",
        f"Team size: {ctx.idea.team_size} member(s)",
        "Note: Revenue projections are not provided — actual financials "
        "depend on go-to-market execution and market adoption",
    ]


def build_competition_bullets(ctx: PitchDeckInput) -> list[str]:
    cp = ctx.validation.module_scores.competition_pressure
    bullets: list[str] = []

    if cp >= 70:
        bullets.append(
            f"Competition pressure is low ({cp:.0f}/100 openness score) — "
            "significant whitespace exists in this market"
        )
        bullets.append(
            "Few direct competitors identified; first-mover advantage is plausible"
        )
    elif cp >= 45:
        bullets.append(
            f"Moderate competitive landscape ({cp:.0f}/100 openness score) — "
            "established players exist but differentiation is achievable"
        )
        bullets.append(
            "Differentiation strategy should focus on the identified "
            f"key strength: {ctx.validation.key_strength}"
        )
    else:
        bullets.append(
            f"Highly competitive market ({cp:.0f}/100 openness score) — "
            "strong incumbents are present"
        )
        bullets.append(
            "A clear differentiation and niche-entry strategy is essential "
            "to gain market foothold"
        )

    return bullets


def build_traction_bullets(ctx: PitchDeckInput) -> list[str]:
    """Traction slide — conservative by design, no invented metrics."""
    tone = _tone(ctx.validation.final_score)
    bullets = [
        "No revenue or user traction data is available at this stage",
    ]
    if tone == "strong":
        bullets.append(
            "Validation signals are encouraging — next step is to build "
            "an MVP and acquire early design partners"
        )
    elif tone == "moderate":
        bullets.append(
            "Recommended next step: conduct customer discovery interviews "
            "and build a lightweight prototype"
        )
    else:
        bullets.append(
            "Recommended next step: validate core assumptions through "
            "problem-solution interviews before building"
        )
    bullets.append(
        "All metrics shown are based on market signal analysis, "
        "not actual product performance"
    )
    return bullets


def build_risks_bullets(ctx: PitchDeckInput) -> list[str]:
    ef = ctx.validation.module_scores.execution_feasibility
    bullets = [
        f"Key risk area: {ctx.validation.key_risk}",
        f"Risk level: {ctx.validation.risk_level}",
    ]
    if ef < 40:
        bullets.append(
            f"Execution feasibility is low ({ef:.0f}/100) — "
            "technical complexity or regulatory barriers are significant"
        )
    elif ef < 60:
        bullets.append(
            f"Execution feasibility is moderate ({ef:.0f}/100) — "
            "manageable with the right team and resources"
        )
    else:
        bullets.append(
            f"Execution feasibility is favorable ({ef:.0f}/100) — "
            "no major technical or regulatory blockers identified"
        )

    pi = ctx.validation.module_scores.problem_intensity
    if pi < 40:
        bullets.append(
            "Additional risk: low problem awareness may require significant "
            "customer education investment"
        )
    return bullets


def build_ask_bullets(ctx: PitchDeckInput) -> list[str]:
    tone = _tone(ctx.validation.final_score)
    bullets: list[str] = []

    if tone == "strong":
        bullets.append(
            "Seeking seed funding to accelerate MVP development "
            "and early customer acquisition"
        )
    elif tone == "moderate":
        bullets.append(
            "Seeking pre-seed funding or partnerships to validate "
            "product-market fit through a focused pilot"
        )
    else:
        bullets.append(
            "Seeking advisory support and small-scale funding to "
            "conduct deeper market validation"
        )

    bullets.append(
        f"Key strength to leverage: {ctx.validation.key_strength}"
    )
    bullets.append(
        "This deck is auto-generated from validated market signals — "
        "no speculative claims are included"
    )
    return bullets
