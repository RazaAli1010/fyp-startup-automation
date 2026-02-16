/* ============================================================
 * StartBot — Normalization Explanation Config (Frontend Fallback)
 * ============================================================
 * These descriptions are used as fallbacks when the backend does
 * not provide normalization_explanations (e.g. older API versions).
 * The backend is the source of truth for raw_value and formula.
 * ========================================================== */

import type { NormalizedSignals } from "./types";

type SignalKey = keyof Omit<NormalizedSignals, "normalization_explanations">;

export interface NormalizationFallback {
  label: string;
  formula: string;
  description: string;
}

export const NORMALIZATION_FALLBACKS: Record<SignalKey, NormalizationFallback> =
  {
    pain_intensity: {
      label: "Pain Intensity",
      formula:
        "0.30 × Search Intent + 0.25 × Complaints + 0.25 × Manual Cost + 0.20 × Evidence",
      description:
        "Problem intensity from Tavily + SerpAPI signals (search intent, complaints, manual cost, evidence), already 0-100.",
    },
    demand_strength: {
      label: "Demand Strength",
      formula: "normalized = raw × 100",
      description:
        "Derived from search demand proxies (e.g. total results / keyword volume).",
    },
    market_growth: {
      label: "Market Growth",
      formula: "normalized = min((raw / 0.35) ^ 0.7, 1.0) × 100",
      description:
        "Market growth is normalized using a soft saturation curve to prevent unrealistically perfect scores. Exceptionally fast-growing markets approach 100, while typical markets remain below.",
    },
    market_momentum: {
      label: "Market Momentum",
      formula: "normalized = raw × 100",
      description:
        "Recent 6-month acceleration relative to prior 6 months, scaled to 0-100.",
    },
    competition_density: {
      label: "Competition Density",
      formula: "normalized = raw × 100",
      description:
        "Market crowding score (0-1) based on competitor count, scaled to 0-100.",
    },
    feature_overlap: {
      label: "Feature Overlap",
      formula: "normalized = raw × 100",
      description:
        "Jaccard similarity of competitor features vs. your industry keywords, scaled to 0-100.",
    },
    tech_complexity_score: {
      label: "Tech Complexity",
      formula: "normalized = raw × 100 (inferred: low→20, medium→50, high→75)",
      description:
        "Technical complexity inferred by OpenAI from business description, mapped to 0-100.",
    },
    regulatory_risk_score: {
      label: "Regulatory Risk",
      formula: "normalized = raw × 100 (inferred: low→20, medium→50, high→80)",
      description:
        "Regulatory risk inferred by OpenAI from business description, mapped to 0-100.",
    },
  };
