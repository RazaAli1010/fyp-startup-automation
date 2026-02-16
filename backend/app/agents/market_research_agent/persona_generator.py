"""Rule-based persona generator for market research.

Generates 2–3 customer personas based on idea metadata and computed market
numbers. Uses deterministic rules — no LLM dependency required.
"""

from __future__ import annotations

from typing import Any


# ── Persona templates by customer type ───────────────────────────────────

_B2C_PERSONAS = [
    {
        "name": "Early Adopter Emma",
        "age_range": "22–35",
        "role": "Tech-savvy consumer",
        "pain_points": [
            "Frustrated with existing solutions that are too complex",
            "Wants a simple, mobile-first experience",
            "Price-conscious but willing to pay for quality",
        ],
        "goals": [
            "Save time on routine tasks",
            "Find a reliable, trustworthy platform",
            "Get value quickly without a steep learning curve",
        ],
        "channels": ["Social media", "App stores", "Word of mouth", "Influencer reviews"],
    },
    {
        "name": "Mainstream Mike",
        "age_range": "30–50",
        "role": "Average consumer",
        "pain_points": [
            "Doesn't trust new platforms easily",
            "Needs social proof before committing",
            "Wants customer support when things go wrong",
        ],
        "goals": [
            "Solve a specific problem reliably",
            "Feel confident the product is safe and tested",
            "Share the experience with family or friends",
        ],
        "channels": ["Google search", "Review sites", "Email newsletters", "Facebook"],
    },
    {
        "name": "Budget-Conscious Ben",
        "age_range": "18–40",
        "role": "Price-sensitive user",
        "pain_points": [
            "Current solutions are too expensive",
            "Free alternatives lack key features",
            "Wants transparency in pricing",
        ],
        "goals": [
            "Get the best value for money",
            "Access premium features at fair prices",
            "Compare options easily before purchasing",
        ],
        "channels": ["Comparison websites", "Reddit", "YouTube reviews", "Deal sites"],
    },
]

_B2B_PERSONAS = [
    {
        "name": "Decision-Maker Dana",
        "age_range": "35–55",
        "role": "VP / Director / C-level",
        "pain_points": [
            "Needs ROI justification for every purchase",
            "Overwhelmed by vendor noise and feature bloat",
            "Integration with existing tools is critical",
        ],
        "goals": [
            "Reduce operational costs by 20%+",
            "Streamline team workflows",
            "Demonstrate results to board / stakeholders",
        ],
        "channels": ["Industry conferences", "LinkedIn", "Analyst reports", "Peer referrals"],
    },
    {
        "name": "Technical Lead Tom",
        "age_range": "28–45",
        "role": "Engineering Manager / Tech Lead",
        "pain_points": [
            "Needs API-first, developer-friendly tools",
            "Security and compliance are non-negotiable",
            "Hates vendor lock-in",
        ],
        "goals": [
            "Evaluate technical fit quickly",
            "Ensure scalability for growing team",
            "Minimize migration risk",
        ],
        "channels": ["GitHub", "Stack Overflow", "Hacker News", "Technical blogs"],
    },
    {
        "name": "End-User Emily",
        "age_range": "25–40",
        "role": "Team member / IC",
        "pain_points": [
            "Current tools slow down daily work",
            "Training on new tools is time-consuming",
            "Wants intuitive UX without reading docs",
        ],
        "goals": [
            "Complete tasks faster",
            "Reduce friction in daily workflow",
            "Feel empowered by the tool, not burdened",
        ],
        "channels": ["Slack communities", "Product Hunt", "Peer recommendations", "YouTube tutorials"],
    },
]

_MARKETPLACE_PERSONAS = [
    {
        "name": "Seller Sam",
        "age_range": "25–50",
        "role": "Service provider / Merchant",
        "pain_points": [
            "Needs a steady stream of qualified leads",
            "Platform fees eat into margins",
            "Wants fair visibility and ranking",
        ],
        "goals": [
            "Grow customer base without heavy marketing spend",
            "Build reputation through ratings and reviews",
            "Maximize revenue per transaction",
        ],
        "channels": ["Platform SEO", "Social media marketing", "Industry forums", "Email"],
    },
    {
        "name": "Buyer Bella",
        "age_range": "20–45",
        "role": "Consumer / Purchaser",
        "pain_points": [
            "Hard to compare options across providers",
            "Trust and safety concerns with unknown sellers",
            "Wants transparent pricing and terms",
        ],
        "goals": [
            "Find the best provider quickly",
            "Feel safe transacting on the platform",
            "Get reliable quality and timely delivery",
        ],
        "channels": ["Google search", "App stores", "Social media", "Friend referrals"],
    },
    {
        "name": "Power User Pat",
        "age_range": "28–45",
        "role": "Frequent buyer / Repeat seller",
        "pain_points": [
            "Wants bulk or loyalty discounts",
            "Needs better tools for managing transactions",
            "Frustrated by platform limitations at scale",
        ],
        "goals": [
            "Optimize workflow on the platform",
            "Unlock premium features for high-volume usage",
            "Build long-term relationships through the platform",
        ],
        "channels": ["Platform newsletters", "Power user forums", "Direct outreach", "LinkedIn"],
    },
]


def generate_personas(
    *,
    target_customer_type: str,
    industry: str,
    geography: str,
    startup_name: str,
    som_min: float,
    som_max: float,
) -> list[dict[str, Any]]:
    """Generate 2–3 customer personas based on idea metadata.

    Returns a list of persona dicts with name, role, pain_points, goals, channels.
    """
    print(f"👤 [PERSONA] Generating personas for {startup_name} "
          f"(type={target_customer_type}, industry={industry})")

    # Select persona templates
    if target_customer_type == "B2B":
        templates = _B2B_PERSONAS
    elif target_customer_type == "Marketplace":
        templates = _MARKETPLACE_PERSONAS
    else:
        templates = _B2C_PERSONAS

    # Take 2–3 personas
    personas = []
    for template in templates[:3]:
        persona = dict(template)
        # Customize with idea context
        persona["context"] = (
            f"Potential customer of {startup_name} in the {industry} space, "
            f"operating in {geography}. Addressable market opportunity: "
            f"${som_min/1e6:.1f}M–${som_max/1e6:.1f}M."
        )
        personas.append(persona)

    print(f"👤 [PERSONA] Generated {len(personas)} personas")
    return personas
