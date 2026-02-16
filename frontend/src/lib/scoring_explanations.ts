/* ============================================================
 * StartBot — Scoring Explanation Config (Single Source of Truth)
 * ============================================================
 * These formulas MUST match backend scoring_engine.py exactly.
 * All values are on a 0-100 normalized scale.
 * ========================================================== */

import type { NormalizedSignals, ModuleScores } from "./types";

type ModuleKey = keyof Omit<ModuleScores, "final_viability_score">;
type SignalKey = keyof Omit<NormalizedSignals, "normalization_explanations">;

export interface ScoringExplanation {
  label: string;
  formula: string;
  inputs: { key: SignalKey; label: string; weight: number }[];
  description: string;
  /** Return a rule-based interpretation given the computed score. */
  interpret: (score: number) => string;
}

export const SCORING_EXPLANATIONS: Record<ModuleKey, ScoringExplanation> = {
  problem_intensity: {
    label: "Problem Intensity",
    formula:
      "0.30 × Search Intent + 0.25 × Complaint Signals + 0.25 × Manual Work Cost + 0.20 × Evidence Strength",
    inputs: [{ key: "pain_intensity", label: "Pain Intensity", weight: 1.0 }],
    description:
      "Measures how severe and frequent the problem is using search intent, evidence from industry articles, complaint patterns, and manual workflow cost.",
    interpret: (score) => {
      if (score >= 70)
        return "Strong problem signals — high search intent, clear complaints, and costly manual workflows.";
      if (score >= 45)
        return "Moderate problem signals — some search intent and complaints but evidence is mixed.";
      return "Weak problem signals — limited search intent, few complaints, and low manual cost.";
    },
  },

  market_timing: {
    label: "Market Timing",
    formula:
      "0.4 × Market Growth + 0.3 × Market Momentum + 0.3 × Demand Strength",
    inputs: [
      { key: "market_growth", label: "Market Growth", weight: 0.4 },
      { key: "market_momentum", label: "Market Momentum", weight: 0.3 },
      { key: "demand_strength", label: "Demand Strength", weight: 0.3 },
    ],
    description:
      "Measures whether the market is growing, accelerating, and actively searched.",
    interpret: (score) => {
      if (score >= 70)
        return "Excellent timing — the market is growing fast with strong recent momentum.";
      if (score >= 45)
        return "Decent timing — market interest is growing but momentum is moderate.";
      return "Poor timing — limited growth signals and weak demand trends.";
    },
  },

  competition_pressure: {
    label: "Competition Pressure",
    formula: "100 − (0.6 × Competition Density + 0.4 × Feature Overlap)",
    inputs: [
      { key: "competition_density", label: "Competition Density", weight: 0.6 },
      { key: "feature_overlap", label: "Feature Overlap", weight: 0.4 },
    ],
    description:
      "Measures how crowded the market is. Higher score = less competition pressure.",
    interpret: (score) => {
      if (score >= 70)
        return "Low competition — the market has room for new entrants.";
      if (score >= 45)
        return "Moderate competition — some established players but differentiation is possible.";
      return "High competition — crowded market with significant feature overlap.";
    },
  },

  market_potential: {
    label: "Market Potential",
    formula: "0.6 × Demand Strength + 0.4 × Market Growth",
    inputs: [
      { key: "demand_strength", label: "Demand Strength", weight: 0.6 },
      { key: "market_growth", label: "Market Growth", weight: 0.4 },
    ],
    description:
      "Measures the overall market opportunity based on demand and growth trajectory.",
    interpret: (score) => {
      if (score >= 70)
        return "High potential — strong demand combined with solid growth trajectory.";
      if (score >= 45)
        return "Moderate potential — some demand exists but growth could be stronger.";
      return "Low potential — weak demand signals and limited market growth.";
    },
  },

  execution_feasibility: {
    label: "Execution Feasibility",
    formula: "100 − (0.6 × Tech Complexity + 0.4 × Regulatory Risk)",
    inputs: [
      { key: "tech_complexity_score", label: "Tech Complexity", weight: 0.6 },
      { key: "regulatory_risk_score", label: "Regulatory Risk", weight: 0.4 },
    ],
    description:
      "Measures how feasible execution is given technical and regulatory barriers.",
    interpret: (score) => {
      if (score >= 70)
        return "Highly feasible — low technical barriers and minimal regulatory risk.";
      if (score >= 45)
        return "Moderately feasible — some technical or regulatory challenges to navigate.";
      return "Challenging execution — significant technical complexity or regulatory hurdles.";
    },
  },
};

export const FINAL_SCORE_FORMULA =
  "0.25 × Problem Intensity + 0.25 × Market Timing + 0.20 × Competition Pressure + 0.15 × Market Potential + 0.15 × Execution Feasibility";
