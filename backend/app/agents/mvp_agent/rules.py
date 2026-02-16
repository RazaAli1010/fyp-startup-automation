"""MVP decision rules — deterministic, no LLM, no randomness.

Each rule inspects scores and idea metadata to produce MVP configuration
decisions. Rules are composable and applied sequentially.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MVPDecisionContext:
    """All inputs the rules engine needs."""

    # Idea metadata
    startup_name: str
    industry: str
    one_line_description: str
    target_customer_type: str
    geography: str
    customer_size: str
    revenue_model: str
    pricing_estimate: float
    team_size: int
    tech_complexity: float
    regulatory_risk: float

    # Evaluation scores (0-100)
    problem_intensity: float
    market_timing: float
    competition_pressure: float
    market_potential: float
    execution_feasibility: float
    final_viability_score: float

    # Market research
    market_confidence: str  # "high" | "medium" | "low"
    competitors: List[Dict[str, Any]] = field(default_factory=list)
    competitor_count: int = 0


# ── MVP type selection ────────────────────────────────────────────────

def decide_mvp_type(ctx: MVPDecisionContext) -> str:
    """Deterministically select MVP approach based on scores."""
    if ctx.market_confidence == "low" or ctx.execution_feasibility < 40:
        return "Concierge MVP"
    if ctx.problem_intensity < 50 and ctx.market_potential < 50:
        return "Landing Page + Waitlist"
    if ctx.tech_complexity > 0.7:
        return "Wizard of Oz MVP"
    if ctx.competition_pressure < 50:
        return "Single-Feature MVP"
    return "Functional Prototype"


# ── Feature scope ─────────────────────────────────────────────────────

def decide_core_features(ctx: MVPDecisionContext) -> List[Dict[str, str]]:
    """Determine core MVP features based on scores and idea context."""
    features: List[Dict[str, str]] = []

    # Always include the primary value proposition feature
    features.append({
        "name": "Core Value Delivery",
        "description": f"Primary feature that solves the core problem: {ctx.one_line_description}",
    })

    # User onboarding — always needed
    features.append({
        "name": "User Onboarding",
        "description": f"Simple signup and onboarding flow for {ctx.target_customer_type} users",
    })

    # Revenue model feature
    rev_feature = {
        "Subscription": {"name": "Subscription Billing", "description": "Basic subscription management and payment processing"},
        "One-time": {"name": "One-time Purchase", "description": "Simple checkout and payment flow"},
        "Marketplace Fee": {"name": "Marketplace Matching", "description": "Connect buyers and sellers with transaction fee"},
        "Ads": {"name": "Content Feed", "description": "Content display with basic ad placement slots"},
    }
    features.append(rev_feature.get(ctx.revenue_model, {"name": "Payment Integration", "description": "Basic payment processing"}))

    # Add analytics if feasibility allows
    if ctx.execution_feasibility >= 50:
        features.append({
            "name": "Basic Analytics Dashboard",
            "description": "Track key usage metrics and user engagement",
        })

    # Add differentiation feature if competition is high
    if ctx.competition_pressure < 50:
        features.append({
            "name": "Differentiator Feature",
            "description": f"Unique capability that distinguishes from {ctx.competitor_count} existing competitors in {ctx.industry}",
        })

    return features


def decide_excluded_features(ctx: MVPDecisionContext) -> List[str]:
    """Determine features to explicitly exclude from MVP."""
    excluded: List[str] = []

    excluded.append("Advanced reporting and business intelligence")
    excluded.append("Multi-language / internationalization support")
    excluded.append("Native mobile apps (web-first approach)")

    if ctx.execution_feasibility < 50:
        excluded.append("Complex automation workflows")
        excluded.append("AI/ML-powered features")

    if ctx.problem_intensity < 50:
        excluded.append("Advanced customization and personalization")

    if ctx.team_size <= 2:
        excluded.append("Admin panel with role-based access control")
        excluded.append("API integrations with third-party tools")

    if ctx.regulatory_risk > 0.6:
        excluded.append("Self-service compliance tools (handle manually first)")

    return excluded


# ── User flow ─────────────────────────────────────────────────────────

def decide_user_flow(ctx: MVPDecisionContext) -> List[str]:
    """Build the primary user journey for the MVP."""
    flow: List[str] = [
        f"User discovers {ctx.startup_name} via landing page",
        "User signs up with email or social auth",
    ]

    if ctx.target_customer_type == "B2B":
        flow.append("User completes company profile and team setup")
    else:
        flow.append("User completes personal profile setup")

    flow.append(f"User accesses core feature: {ctx.one_line_description}")

    if ctx.revenue_model == "Subscription":
        flow.append("User starts free trial or selects subscription plan")
    elif ctx.revenue_model == "Marketplace Fee":
        flow.append("User posts listing or browses marketplace")
    elif ctx.revenue_model == "One-time":
        flow.append("User completes one-time purchase")
    else:
        flow.append("User engages with free content")

    flow.append("User receives value and sees first result")
    flow.append("User provides feedback or shares with others")

    return flow


# ── Tech stack ────────────────────────────────────────────────────────

def decide_tech_stack(ctx: MVPDecisionContext) -> Dict[str, str]:
    """Recommend tech stack based on team size and complexity."""
    stack: Dict[str, str] = {}

    # Frontend
    if ctx.team_size <= 2:
        stack["frontend"] = "Next.js + TailwindCSS (rapid development)"
    else:
        stack["frontend"] = "React + TypeScript + TailwindCSS"

    # Backend
    if ctx.tech_complexity > 0.7:
        stack["backend"] = "Python (FastAPI) — good for data-heavy workloads"
    elif ctx.team_size <= 2:
        stack["backend"] = "Node.js (Express) or Python (FastAPI) — pick team's strongest language"
    else:
        stack["backend"] = "Python (FastAPI) + PostgreSQL"

    # Database
    stack["database"] = "PostgreSQL (reliable, scalable)"

    # Hosting
    if ctx.team_size <= 2:
        stack["hosting"] = "Vercel (frontend) + Railway or Render (backend)"
    else:
        stack["hosting"] = "AWS or GCP with managed services"

    # Auth
    stack["auth"] = "Clerk or Auth0 (avoid building auth from scratch)"

    # Payments
    if ctx.revenue_model in ("Subscription", "One-time", "Marketplace Fee"):
        stack["payments"] = "Stripe (industry standard for MVP)"

    return stack


# ── Build plan ────────────────────────────────────────────────────────

def decide_build_plan(ctx: MVPDecisionContext) -> Dict[str, Any]:
    """Create a phased build plan with timeline."""
    if ctx.team_size <= 2:
        weeks_multiplier = 1.5
    elif ctx.team_size <= 5:
        weeks_multiplier = 1.0
    else:
        weeks_multiplier = 0.75

    base_weeks = 4 if ctx.tech_complexity <= 0.5 else 6

    phases = [
        {
            "phase": "Phase 1: Foundation",
            "duration": f"{max(1, int(1 * weeks_multiplier))} week(s)",
            "tasks": [
                "Set up project repository and CI/CD",
                "Configure authentication and database",
                "Deploy skeleton app to staging",
            ],
        },
        {
            "phase": "Phase 2: Core Feature",
            "duration": f"{max(1, int(2 * weeks_multiplier))} week(s)",
            "tasks": [
                f"Implement core value: {ctx.one_line_description}",
                "Build primary user flow end-to-end",
                "Basic error handling and validation",
            ],
        },
        {
            "phase": "Phase 3: Polish & Launch",
            "duration": f"{max(1, int(1 * weeks_multiplier))} week(s)",
            "tasks": [
                "UI polish and responsive design",
                "Set up analytics and error tracking",
                "Soft launch to initial user cohort",
            ],
        },
    ]

    total_weeks = int(base_weeks * weeks_multiplier)

    return {
        "total_estimated_weeks": total_weeks,
        "team_size": ctx.team_size,
        "phases": phases,
    }


# ── Validation plan ──────────────────────────────────────────────────

def decide_validation_plan(ctx: MVPDecisionContext) -> Dict[str, Any]:
    """Create a validation plan to test the core hypothesis."""
    metrics: List[str] = []
    methods: List[str] = []

    # Always track these
    metrics.append("Signup conversion rate (target: >5%)")
    metrics.append("Weekly active users (WAU)")
    metrics.append("User retention at Day 7 and Day 30")

    if ctx.revenue_model == "Subscription":
        metrics.append("Free-to-paid conversion rate (target: >2%)")
        metrics.append("Monthly recurring revenue (MRR)")
    elif ctx.revenue_model == "Marketplace Fee":
        metrics.append("Transaction volume and gross merchandise value")
        metrics.append("Repeat transaction rate")
    else:
        metrics.append("Revenue per user")

    # Validation methods based on confidence
    methods.append("User interviews (minimum 10 users in first 2 weeks)")
    methods.append("In-app feedback widget for qualitative signals")

    if ctx.market_confidence == "low":
        methods.append("Smoke test: measure demand before building full feature")
        methods.append("Concierge delivery: manually fulfill first 20 orders")
    elif ctx.market_confidence == "medium":
        methods.append("A/B test landing page messaging")
        methods.append("Track feature usage heatmaps")
    else:
        methods.append("Cohort analysis on early adopters")
        methods.append("Net Promoter Score (NPS) survey at Day 14")

    success_criteria = "Achieve 100 signups and >5% activation rate within 4 weeks of launch"
    if ctx.problem_intensity >= 70:
        success_criteria = "Achieve 200 signups and >10% activation rate within 4 weeks of launch"
    elif ctx.problem_intensity < 40:
        success_criteria = "Achieve 50 signups and validate problem-solution fit via interviews"

    return {
        "success_criteria": success_criteria,
        "key_metrics": metrics,
        "validation_methods": methods,
        "timeline": "4-6 weeks post-launch",
    }


# ── Risk notes ────────────────────────────────────────────────────────

def decide_risk_notes(ctx: MVPDecisionContext) -> List[str]:
    """Generate risk notes based on scores and idea context."""
    risks: List[str] = []

    if ctx.problem_intensity < 50:
        risks.append(
            f"Low problem intensity ({ctx.problem_intensity:.0f}/100) — users may not feel the pain strongly enough to adopt. "
            "Mitigate by validating problem-solution fit before scaling."
        )

    if ctx.competition_pressure < 50:
        risks.append(
            f"High competition ({ctx.competition_pressure:.0f}/100 pressure score) — {ctx.competitor_count} competitors found. "
            "Mitigate by focusing on a narrow niche and strong differentiation."
        )

    if ctx.execution_feasibility < 50:
        risks.append(
            f"Execution challenges ({ctx.execution_feasibility:.0f}/100) — technical complexity or regulatory barriers. "
            "Mitigate by starting with manual processes and automating incrementally."
        )

    if ctx.market_confidence == "low":
        risks.append(
            "Low market confidence — limited reliable market data. "
            "Mitigate by running demand validation experiments before heavy investment."
        )

    if ctx.team_size <= 2:
        risks.append(
            f"Small team ({ctx.team_size} people) — resource constraints may slow iteration. "
            "Mitigate by ruthlessly prioritizing and using no-code/low-code tools where possible."
        )

    if ctx.regulatory_risk > 0.6:
        risks.append(
            f"Elevated regulatory risk ({ctx.regulatory_risk:.1f}) — compliance requirements in {ctx.industry}. "
            "Mitigate by consulting legal counsel early and building compliance into the process."
        )

    if ctx.pricing_estimate < 10 and ctx.revenue_model == "Subscription":
        risks.append(
            f"Low price point (${ctx.pricing_estimate:.0f}/mo) — may struggle to cover CAC. "
            "Mitigate by validating willingness to pay and exploring upsell tiers."
        )

    # Always include a general risk
    if not risks:
        risks.append(
            "General startup risk — market conditions and user preferences can shift. "
            "Mitigate by maintaining short iteration cycles and staying close to users."
        )

    return risks
