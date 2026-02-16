/* ============================================================
 * StartBot — Centralised API client
 * ============================================================
 * Every backend call goes through this module.
 * No fetch() calls should exist in components.
 * ========================================================== */

import type {
  StartupIdeaInput,
  CreateIdeaResponse,
  IdeaEvaluationReport,
  PitchDeckRecord,
  PitchDeckListResponse,
  MarketResearchRecord,
  MarketResearchListResponse,
  MVPReportRecord,
  MVPReportListResponse,
  LegalDocumentRecord,
  LegalDocumentListResponse,
  AuthResponse,
  MessageResponse,
  DashboardResponse,
  UserPublic,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Debug flag (set to false to disable all API logs) ────
const DEBUG_API = true;

// ── Token helpers ──────────────────────────────────────────

const TOKEN_KEY = "startbot_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ── Generic helpers ────────────────────────────────────────

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs: number = 120_000,
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const method = options.method ?? "GET";

  if (DEBUG_API) {
    console.log(`[API] ${method} ${path} → ${url}`);
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  // Attach JWT if available
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Abort controller for timeout — prevents infinite hang if backend dies
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (networkErr) {
    clearTimeout(timer);
    if (
      networkErr instanceof DOMException &&
      networkErr.name === "AbortError"
    ) {
      if (DEBUG_API) {
        console.error(
          `[API] Request timed out after ${timeoutMs}ms: ${method} ${path}`,
        );
      }
      throw new Error(
        `Request timed out — the server took too long to respond`,
      );
    }
    if (DEBUG_API) {
      console.error(
        "[API] Network error — backend unreachable or CORS blocked",
        networkErr,
      );
    }
    throw networkErr;
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response may not be JSON
    }
    if (DEBUG_API) {
      console.error(`[API] HTTP ${res.status} — ${detail}`);
    }

    // Auto-clear token on 401
    if (res.status === 401) {
      clearToken();
    }

    throw new ApiError(res.status, detail);
  }

  const data = (await res.json()) as T;

  if (DEBUG_API) {
    console.log(`[API] ${method} ${path} ✓ ${res.status}`, data);
  }

  return data;
}

// ── Auth API functions ─────────────────────────────────────

export async function signup(
  email: string,
  username: string,
  password: string,
): Promise<MessageResponse> {
  return request<MessageResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, username, password }),
  });
}

export async function login(
  email: string,
  password: string,
): Promise<AuthResponse> {
  const data = await request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function getMe(): Promise<UserPublic> {
  return request<UserPublic>("/auth/me");
}

export async function getDashboard(): Promise<DashboardResponse> {
  return request<DashboardResponse>("/auth/dashboard");
}

export function getGoogleLoginUrl(): string {
  return `${API_BASE_URL}/auth/google/login`;
}

export async function getGoogleAuthStatus(): Promise<{
  google_auth_enabled: boolean;
}> {
  return request<{ google_auth_enabled: boolean }>("/auth/google/status");
}

// ── Idea API functions ─────────────────────────────────────

export async function createIdea(
  data: StartupIdeaInput,
): Promise<CreateIdeaResponse> {
  if (DEBUG_API) {
    console.log("[API] createIdea → POST /ideas/", {
      startup_name: data.startup_name,
      industry: data.industry,
      target_customer_type: data.target_customer_type,
    });
  }
  return request<CreateIdeaResponse>("/ideas/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getEvaluation(
  ideaId: string,
): Promise<IdeaEvaluationReport> {
  if (DEBUG_API) {
    console.log(`[API] getEvaluation → GET /ideas/${ideaId}/evaluation`);
  }
  return request<IdeaEvaluationReport>(`/ideas/${ideaId}/evaluation`);
}

export async function evaluateIdea(
  ideaId: string,
): Promise<IdeaEvaluationReport> {
  if (DEBUG_API) {
    console.log(`[API] evaluateIdea → POST /ideas/${ideaId}/evaluate`);
  }
  return request<IdeaEvaluationReport>(`/ideas/${ideaId}/evaluate`, {
    method: "POST",
  });
}

// ── Pitch Deck API functions ──────────────────────────────

export async function generatePitchDeck(
  ideaId: string,
): Promise<PitchDeckRecord> {
  if (DEBUG_API) {
    console.log(
      `[API] generatePitchDeck → POST /pitch-deck/generate?idea_id=${ideaId}`,
    );
  }
  return request<PitchDeckRecord>(`/pitch-deck/generate?idea_id=${ideaId}`, {
    method: "POST",
  });
}

export async function getPitchDeckByIdea(
  ideaId: string,
): Promise<PitchDeckRecord> {
  if (DEBUG_API) {
    console.log(`[API] getPitchDeckByIdea → GET /pitch-deck/idea/${ideaId}`);
  }
  return request<PitchDeckRecord>(`/pitch-deck/idea/${ideaId}`);
}

export async function getPitchDeck(
  pitchDeckId: string,
): Promise<PitchDeckRecord> {
  if (DEBUG_API) {
    console.log(`[API] getPitchDeck → GET /pitch-deck/${pitchDeckId}`);
  }
  return request<PitchDeckRecord>(`/pitch-deck/${pitchDeckId}`);
}

export async function listPitchDecks(): Promise<PitchDeckListResponse> {
  if (DEBUG_API) {
    console.log("[API] listPitchDecks → GET /pitch-deck/");
  }
  return request<PitchDeckListResponse>("/pitch-deck/");
}

// ── Market Research API functions ─────────────────────────

export async function generateMarketResearch(
  ideaId: string,
): Promise<MarketResearchRecord> {
  if (DEBUG_API) {
    console.log(
      `[API] generateMarketResearch → POST /market-research/generate?idea_id=${ideaId}`,
    );
  }
  return request<MarketResearchRecord>(
    `/market-research/generate?idea_id=${ideaId}`,
    { method: "POST" },
  );
}

export async function getMarketResearchByIdea(
  ideaId: string,
): Promise<MarketResearchRecord> {
  if (DEBUG_API) {
    console.log(
      `[API] getMarketResearchByIdea → GET /market-research/idea/${ideaId}`,
    );
  }
  return request<MarketResearchRecord>(`/market-research/idea/${ideaId}`);
}

export async function listMarketResearch(): Promise<MarketResearchListResponse> {
  if (DEBUG_API) {
    console.log("[API] listMarketResearch → GET /market-research/");
  }
  return request<MarketResearchListResponse>("/market-research/");
}

// ── MVP API functions ────────────────────────────────────

export async function generateMVP(ideaId: string): Promise<MVPReportRecord> {
  if (DEBUG_API) {
    console.log(`[API] generateMVP → POST /mvp/generate?idea_id=${ideaId}`);
  }
  return request<MVPReportRecord>(`/mvp/generate?idea_id=${ideaId}`, {
    method: "POST",
  });
}

export async function getMVPByIdea(ideaId: string): Promise<MVPReportRecord> {
  if (DEBUG_API) {
    console.log(`[API] getMVPByIdea → GET /mvp/idea/${ideaId}`);
  }
  return request<MVPReportRecord>(`/mvp/idea/${ideaId}`);
}

export async function listMVPs(): Promise<MVPReportListResponse> {
  if (DEBUG_API) {
    console.log("[API] listMVPs → GET /mvp/");
  }
  return request<MVPReportListResponse>("/mvp/");
}

// ── Legal Document API functions ──────────────────────────

export interface GenerateLegalRequest {
  document_type: string;
  jurisdiction?: string;
  company_name?: string;
  founder_count?: number;
}

export async function generateLegalDocument(
  ideaId: string,
  body: GenerateLegalRequest,
): Promise<LegalDocumentRecord> {
  if (DEBUG_API) {
    console.log(
      `[API] generateLegalDocument → POST /legal/generate?idea_id=${ideaId}`,
    );
  }
  return request<LegalDocumentRecord>(`/legal/generate?idea_id=${ideaId}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getLegalByIdea(
  ideaId: string,
): Promise<LegalDocumentListResponse> {
  if (DEBUG_API) {
    console.log(`[API] getLegalByIdea → GET /legal/idea/${ideaId}`);
  }
  return request<LegalDocumentListResponse>(`/legal/idea/${ideaId}`);
}

export async function getLegalDocument(
  documentId: string,
): Promise<LegalDocumentRecord> {
  if (DEBUG_API) {
    console.log(`[API] getLegalDocument → GET /legal/${documentId}`);
  }
  return request<LegalDocumentRecord>(`/legal/${documentId}`);
}

export { ApiError };
