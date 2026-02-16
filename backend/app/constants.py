"""Centralized constants shared across all agents and routes.

This module is the SINGLE SOURCE OF TRUTH for industry taxonomy,
country lists, and customer type enums. Reused by:
  - Idea Validation Agent
  - Market Research Agent
  - Frontend (mirrored in frontend/src/lib/constants.ts)
"""

from __future__ import annotations

# ── Standardized Industry Taxonomy ──────────────────────────────────────
# Multi-select. Used to drive queries, competitor discovery, and market sizing.
# LOCKED — changes here must be mirrored in frontend/src/lib/constants.ts.

INDUSTRIES: list[str] = [
    "SaaS",
    "Artificial Intelligence",
    "FinTech",
    "HealthTech",
    "MedTech",
    "BioTech",
    "EdTech",
    "LegalTech",
    "InsurTech",
    "PropTech",
    "ClimateTech",
    "AgriTech",
    "FoodTech",
    "GovTech",
    "HRTech",
    "TravelTech",
    "E-commerce",
    "Marketplaces",
    "Logistics & Supply Chain",
    "Mobility & Transportation",
    "Real Estate",
    "Cybersecurity",
    "Developer Tools",
    "Data & Analytics",
    "Cloud Infrastructure",
    "Hardware / IoT",
    "Consumer Apps",
    "Creator Economy",
    "Gaming",
    "Media & Entertainment",
    "Social Platforms",
    "Web3 / Blockchain",
    "Payments",
    "Banking",
    "Lending",
    "WealthTech",
    "RegTech",
    "Manufacturing",
    "Retail",
    "Telecommunications",
    "Energy",
    "Smart Cities",
    "Non-Profit / Social Impact",
]

# Frozen set for fast membership checks
INDUSTRIES_SET: frozenset[str] = frozenset(INDUSTRIES)

# ── Target Customer Types ───────────────────────────────────────────────
CUSTOMER_TYPES: list[str] = ["B2B", "B2C", "B2B2C"]

# ── OpenAI Inference: complexity / risk level mapping ───────────────────
# These map the LLM-inferred levels to 0-1 values stored on the Idea model.
# The normalization engine then multiplies by 100 to get 0-100 scores.

TECH_COMPLEXITY_MAP: dict[str, float] = {
    "low": 0.20,      # → 20 after normalization
    "medium": 0.50,    # → 50 after normalization
    "high": 0.75,      # → 75 after normalization
}

REGULATORY_RISK_MAP: dict[str, float] = {
    "low": 0.20,       # → 20 after normalization
    "medium": 0.50,    # → 50 after normalization
    "high": 0.80,      # → 80 after normalization
}

# ── Revenue Model Defaults ──────────────────────────────────────────────
# Used when OpenAI infers a revenue_model string — map to known categories
# for the market research calculator.
KNOWN_REVENUE_MODELS: list[str] = [
    "Subscription",
    "One-time",
    "Marketplace Fee",
    "Ads",
    "Freemium",
    "Usage-based",
    "Licensing",
    "Transaction Fee",
]

# Default pricing estimates (USD/month) by revenue model — used when user
# does not provide pricing (which is now always, since we removed that input).
DEFAULT_PRICING: dict[str, float] = {
    "Subscription": 49.0,
    "One-time": 99.0,
    "Marketplace Fee": 100.0,
    "Ads": 0.0,
    "Freemium": 29.0,
    "Usage-based": 50.0,
    "Licensing": 199.0,
    "Transaction Fee": 50.0,
}
DEFAULT_PRICING_FALLBACK: float = 49.0

# Default customer size mapping from target_customer_type
CUSTOMER_TYPE_TO_SIZE: dict[str, str] = {
    "B2B": "SMB",
    "B2C": "Individual",
    "B2B2C": "SMB",
}

DEFAULT_TEAM_SIZE: int = 5
