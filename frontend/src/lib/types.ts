/* ============================================================
 * StartBot — TypeScript types matching backend Pydantic schemas
 * ============================================================
 * These interfaces are a 1:1 mapping of the FastAPI backend models.
 * Do NOT add or omit fields.
 * ========================================================== */

// ── Auth ────────────────────────────────────────────────────

export interface UserPublic {
  id: string;
  email: string;
  username: string;
  auth_provider: "local" | "google";
  is_email_verified: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserPublic;
}

export interface MessageResponse {
  message: string;
}

export interface UserDashboardIdea {
  id: string;
  startup_name: string;
  industry: string;
  created_at?: string | null;
  final_viability_score?: number | null;
}

// ── Request: POST /ideas/ ──────────────────────────────────
export interface StartupIdeaInput {
  startup_name: string;
  one_line_description: string;
  industry: string;
  target_customer_type: "B2B" | "B2C" | "Marketplace";
  geography: string;
  customer_size: "Individual" | "SMB" | "Mid-Market" | "Enterprise";
  revenue_model: "Subscription" | "One-time" | "Marketplace Fee" | "Ads";
  pricing_estimate: number;
  estimated_cac: number;
  estimated_ltv: number;
  team_size: number;
  tech_complexity: number;
  regulatory_risk: number;
}

// ── Response: POST /ideas/ ─────────────────────────────────
export interface CreateIdeaResponse {
  idea_id: string;
  message: string;
}

// ── Response: POST /ideas/{id}/evaluate ────────────────────

export interface NormalizationExplanation {
  raw_value: number;
  formula: string;
  description: string;
}

export interface NormalizedSignals {
  pain_intensity: number;
  demand_strength: number;
  market_growth: number;
  market_momentum: number;
  competition_density: number;
  feature_overlap: number;
  tech_complexity_score: number;
  regulatory_risk_score: number;
  normalization_explanations?: Record<string, NormalizationExplanation>;
}

export interface ModuleScores {
  problem_intensity: number;
  market_timing: number;
  competition_pressure: number;
  market_potential: number;
  execution_feasibility: number;
  final_viability_score: number;
}

export interface EvaluationSummary {
  verdict: "Strong" | "Moderate" | "Weak";
  risk_level: "Low" | "Medium" | "High";
  key_strength: string;
  key_risk: string;
}

export interface IdeaEvaluationReport {
  idea_id: string;
  normalized_signals: NormalizedSignals;
  module_scores: ModuleScores;
  competitor_names: string[];
  trend_data_available?: boolean;
  trend_data_source_tier?: string | null;
  summary: EvaluationSummary;
}

// ── Pitch Deck ──────────────────────────────────────────────

export type SlideType =
  | "title"
  | "problem"
  | "solution"
  | "market"
  | "business_model"
  | "competition"
  | "traction"
  | "risks"
  | "ask";

export interface SlideOutput {
  type: SlideType;
  title: string;
  content: string[];
}

export interface PitchDeckOutput {
  deck_title: string;
  tagline: string;
  slides: SlideOutput[];
  provider: "alai" | "rule_based";
  generation_id: string;
  view_url: string;
  pdf_url: string;
}

// ── Pitch Deck Record (DB-backed metadata) ──────────────────

export interface PitchDeckRecord {
  id: string;
  idea_id: string;
  title: string;
  status: "pending" | "completed" | "failed";
  provider: string;
  generation_id: string | null;
  view_url: string | null;
  pdf_url: string | null;
  created_at: string;
}

export interface PitchDeckListResponse {
  pitch_decks: PitchDeckRecord[];
}

export interface UserDashboardPitchDeck {
  id: string;
  idea_id: string;
  title: string;
  status: string;
  view_url: string | null;
  pdf_url: string | null;
  created_at: string | null;
}

// ── Market Research ────────────────────────────────────────

export interface MarketResearchRecord {
  id: string;
  idea_id: string;
  status: "pending" | "completed" | "failed";
  tam_min: number | null;
  tam_max: number | null;
  sam_min: number | null;
  sam_max: number | null;
  som_min: number | null;
  som_max: number | null;
  arpu_annual: number | null;
  growth_rate_estimate: number | null;
  demand_strength: number | null;
  assumptions: string[] | null;
  confidence: MarketConfidence | null;
  sources: string[] | null;
  competitors: MarketCompetitor[] | null;
  competitor_count: number | null;
  created_at: string;
}

export interface MarketCompetitor {
  name: string;
  description: string;
}

export interface MarketConfidence {
  overall: number;
  tam: { score: number; explanation: string };
  sam: { score: number; explanation: string };
  som: { score: number; explanation: string };
  note: string;
}

export interface MarketResearchListResponse {
  records: MarketResearchRecord[];
}

export interface UserDashboardMarketResearch {
  id: string;
  idea_id: string;
  status: string;
  tam_max: number | null;
  sam_max: number | null;
  som_max: number | null;
  demand_strength: number | null;
  created_at: string | null;
}

// ── MVP ───────────────────────────────────────────────────

export interface MVPBlueprintResponse {
  mvp_type: string;
  core_hypothesis: string;
  primary_user: string;
  core_features: { name: string; description: string }[];
  excluded_features: string[];
  user_flow: string[];
  recommended_tech_stack: Record<string, string>;
  build_plan: {
    total_estimated_weeks: number;
    team_size: number;
    phases: { phase: string; duration: string; tasks: string[] }[];
  };
  validation_plan: {
    success_criteria: string;
    key_metrics: string[];
    validation_methods: string[];
    timeline: string;
  };
  risk_notes: string[];
}

export interface MVPReportRecord {
  id: string;
  idea_id: string;
  status: "pending" | "generated" | "failed";
  blueprint: MVPBlueprintResponse | null;
  created_at: string;
}

export interface MVPReportListResponse {
  records: MVPReportRecord[];
}

export interface UserDashboardMVP {
  id: string;
  idea_id: string;
  status: string;
  mvp_type: string | null;
  created_at: string | null;
}

// ── Legal Documents ───────────────────────────────────────

export interface LegalDocumentSection {
  title: string;
  content: string;
}

export interface LegalDocumentResponse {
  document_type: string;
  jurisdiction: string;
  governing_law: string;
  disclaimer: string;
  sections: LegalDocumentSection[];
  customization_notes: string[];
  legal_risk_notes: string[];
  generated_at: string | null;
}

export interface LegalDocumentRecord {
  id: string;
  idea_id: string;
  document_type: string;
  jurisdiction: string | null;
  status: "pending" | "generated" | "failed";
  document: LegalDocumentResponse | null;
  created_at: string;
}

export interface LegalDocumentListResponse {
  records: LegalDocumentRecord[];
}

export interface UserDashboardLegal {
  id: string;
  idea_id: string;
  document_type: string;
  jurisdiction: string | null;
  status: string;
  created_at: string | null;
}

export interface DashboardResponse {
  user: UserPublic;
  ideas: UserDashboardIdea[];
  pitch_decks: UserDashboardPitchDeck[];
  market_research: UserDashboardMarketResearch[];
  mvp_reports: UserDashboardMVP[];
  legal_documents: UserDashboardLegal[];
}

// ── AI Chat Co-Founder ──────────────────────────────────────

export interface ChatResponse {
  answer: string;
  sources: string[];
  indexed_agents: string[];
}

export interface ChatStatusResponse {
  idea_id: string;
  indexed_agents: string[];
  ready: boolean;
}
