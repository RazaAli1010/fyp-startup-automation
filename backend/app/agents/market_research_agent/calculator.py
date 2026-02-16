"""Deterministic TAM / SAM / SOM calculator.

Two modes:
  1. **Bottom-up** (preferred): Uses customer_count from OpenAI reasoning + ARPU.
     TAM = customer_count × ARPU. More defensible.
  2. **Top-down** (fallback): Uses industry base × geography × segment multipliers.
     Used when OpenAI reasoning is unavailable.

SOM is always capped at 5% of SAM. All values are ranges (min/max).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ── Industry base market sizes (USD, global) — top-down fallback ──────────
_INDUSTRY_BASE: dict[str, tuple[float, float]] = {
    "SaaS": (80_000_000_000, 250_000_000_000),
    "Saas/Marketplace": (50_000_000_000, 180_000_000_000),
    "Fintech": (100_000_000_000, 350_000_000_000),
    "Healthtech": (60_000_000_000, 200_000_000_000),
    "Edtech": (30_000_000_000, 120_000_000_000),
    "E-commerce": (200_000_000_000, 600_000_000_000),
    "AI/ML": (50_000_000_000, 200_000_000_000),
    "Marketplace": (80_000_000_000, 300_000_000_000),
    "Social": (40_000_000_000, 150_000_000_000),
    "Enterprise": (100_000_000_000, 400_000_000_000),
    "Consumer": (60_000_000_000, 250_000_000_000),
    "Hardware": (40_000_000_000, 150_000_000_000),
    "Biotech": (50_000_000_000, 180_000_000_000),
    "Cleantech": (30_000_000_000, 120_000_000_000),
    "Logistics": (60_000_000_000, 200_000_000_000),
}
_DEFAULT_BASE = (40_000_000_000, 150_000_000_000)

# ── Geography multipliers (fraction of global TAM) ───────────────────────
_GEO_MULT: dict[str, tuple[float, float]] = {
    "Global": (0.8, 1.0),
    "North America": (0.30, 0.40),
    "United States": (0.25, 0.35),
    "Europe": (0.20, 0.30),
    "Asia": (0.25, 0.35),
    "South America": (0.05, 0.10),
    "Africa": (0.02, 0.05),
    "Middle East": (0.03, 0.07),
    "Oceania": (0.02, 0.04),
}
_DEFAULT_GEO = (0.10, 0.20)

# ── Customer size multipliers (SAM fraction of geo-adjusted TAM) ─────────
_CUST_SIZE_MULT: dict[str, tuple[float, float]] = {
    "Individual": (0.10, 0.25),
    "SMB": (0.15, 0.30),
    "Mid-Market": (0.20, 0.35),
    "Enterprise": (0.25, 0.40),
}
_DEFAULT_CUST = (0.15, 0.30)

# ── Revenue model growth rate estimates (annual %) ───────────────────────
_GROWTH_RATES: dict[str, tuple[float, float]] = {
    "Subscription": (12.0, 25.0),
    "One-time": (5.0, 12.0),
    "Marketplace Fee": (15.0, 30.0),
    "Ads": (8.0, 18.0),
}
_DEFAULT_GROWTH = (8.0, 20.0)

# ── SOM cap ──────────────────────────────────────────────────────────────
SOM_MAX_FRACTION = 0.05  # SOM never exceeds 5% of SAM


@dataclass
class MarketSizeResult:
    """Output of the TAM/SAM/SOM calculation."""

    tam_min: float
    tam_max: float
    sam_min: float
    sam_max: float
    som_min: float
    som_max: float
    arpu_annual: float
    growth_rate_min: float
    growth_rate_max: float
    assumptions: list[str]


def calculate_market_size(
    *,
    industry: str,
    geography: str,
    customer_size: str,
    revenue_model: str,
    pricing_estimate: float,
    team_size: int,
    customer_count_min: Optional[int] = None,
    customer_count_max: Optional[int] = None,
) -> MarketSizeResult:
    """Compute TAM/SAM/SOM ranges.

    If customer_count_min/max are provided (from OpenAI reasoning), uses
    bottom-up: TAM = customer_count × ARPU. Otherwise falls back to
    top-down industry heuristics.
    """
    print(f"📊 [CALC] Inputs: industry={industry}, geo={geography}, "
          f"cust={customer_size}, rev={revenue_model}, price={pricing_estimate}")

    # ── ARPU (computed first — needed for bottom-up) ──────────
    if revenue_model == "Subscription":
        arpu_annual = pricing_estimate * 12
    elif revenue_model == "Marketplace Fee":
        arpu_annual = pricing_estimate * 12 * 0.15  # 15% take rate
    else:
        arpu_annual = pricing_estimate

    assumptions: list[str] = []
    assumptions.append(f"ARPU (annual): ${arpu_annual:,.0f} based on {revenue_model} model")
    print(f"📊 [CALC] ARPU: ${arpu_annual:,.0f}/year")

    # ── TAM ───────────────────────────────────────────────────
    use_bottom_up = (
        customer_count_min is not None
        and customer_count_max is not None
        and customer_count_min > 0
        and customer_count_max > 0
    )

    if use_bottom_up:
        print("📊 [CALC] Using BOTTOM-UP mode (customer_count × ARPU)")
        tam_min = customer_count_min * arpu_annual
        tam_max = customer_count_max * arpu_annual
        assumptions.append(
            f"TAM (bottom-up): {customer_count_min:,}–{customer_count_max:,} customers × ${arpu_annual:,.0f} ARPU"
        )
    else:
        print("📊 [CALC] Using TOP-DOWN fallback (industry × geography)")
        base_min, base_max = _INDUSTRY_BASE.get(industry, _DEFAULT_BASE)
        geo_min, geo_max = _GEO_MULT.get(geography, _DEFAULT_GEO)
        tam_min = base_min * geo_min
        tam_max = base_max * geo_max
        assumptions.append(
            f"Industry base market: ${base_min/1e9:.0f}B–${base_max/1e9:.0f}B (global)"
        )
        assumptions.append(
            f"Geography filter ({geography}): {geo_min*100:.0f}%–{geo_max*100:.0f}% of global"
        )

    print(f"📊 [CALC] TAM: ${tam_min/1e9:.1f}B – ${tam_max/1e9:.1f}B")

    # ── SAM ───────────────────────────────────────────────────
    cust_min, cust_max = _CUST_SIZE_MULT.get(customer_size, _DEFAULT_CUST)

    sam_min = tam_min * cust_min
    sam_max = tam_max * cust_max

    assumptions.append(
        f"Customer segment ({customer_size}): {cust_min*100:.0f}%–{cust_max*100:.0f}% of TAM"
    )

    print(f"📊 [CALC] SAM: ${sam_min/1e9:.1f}B – ${sam_max/1e9:.1f}B")

    # ── SOM (capped at 5% of SAM) ────────────────────────────
    if team_size <= 3:
        som_fraction_min, som_fraction_max = 0.001, 0.005
    elif team_size <= 10:
        som_fraction_min, som_fraction_max = 0.003, 0.01
    elif team_size <= 50:
        som_fraction_min, som_fraction_max = 0.005, 0.02
    else:
        som_fraction_min, som_fraction_max = 0.01, 0.05

    # Enforce SOM cap
    som_fraction_max = min(som_fraction_max, SOM_MAX_FRACTION)

    som_min = sam_min * som_fraction_min
    som_max = sam_max * som_fraction_max

    assumptions.append(
        f"SOM capture rate: {som_fraction_min*100:.2f}%–{som_fraction_max*100:.2f}% of SAM "
        f"(team size: {team_size}, capped at {SOM_MAX_FRACTION*100:.0f}%)"
    )

    print(f"📊 [CALC] SOM: ${som_min/1e6:.1f}M – ${som_max/1e6:.1f}M")

    # ── Growth rate ───────────────────────────────────────────
    growth_min, growth_max = _GROWTH_RATES.get(revenue_model, _DEFAULT_GROWTH)

    assumptions.append(
        f"Growth rate estimate: {growth_min:.0f}%–{growth_max:.0f}% annually ({revenue_model})"
    )

    print(f"📊 [CALC] Growth: {growth_min:.0f}%–{growth_max:.0f}%")

    return MarketSizeResult(
        tam_min=tam_min,
        tam_max=tam_max,
        sam_min=sam_min,
        sam_max=sam_max,
        som_min=som_min,
        som_max=som_max,
        arpu_annual=arpu_annual,
        growth_rate_min=growth_min,
        growth_rate_max=growth_max,
        assumptions=assumptions,
    )
