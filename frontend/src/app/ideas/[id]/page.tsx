"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  getEvaluation,
  evaluateIdea,
  getMarketResearchByIdea,
  getPitchDeckByIdea,
  getMVPByIdea,
  ApiError,
} from "@/lib/api";
import { GatingModal } from "@/components/ui/gating-modal";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EvaluationLoader } from "@/components/ui/evaluation-loader";
import { CompetitorList } from "@/components/report/CompetitorList";
import { ScoreExplainer } from "@/components/report/ScoreExplainer";
import { SignalExplainer } from "@/components/report/SignalExplainer";
import { FINAL_SCORE_FORMULA } from "@/lib/scoring_explanations";
import { RouteGuard } from "@/components/auth/route-guard";
import type {
  IdeaEvaluationReport,
  ModuleScores,
  NormalizedSignals,
} from "@/lib/types";

type Status = "idle" | "loading" | "success" | "error";

const MODULE_LABELS: Record<
  keyof Omit<ModuleScores, "final_viability_score">,
  string
> = {
  problem_intensity: "Problem Intensity",
  market_timing: "Market Timing",
  competition_pressure: "Competition Pressure",
  market_potential: "Market Potential",
  execution_feasibility: "Execution Feasibility",
};

const MODULE_DESCRIPTIONS: Record<
  keyof Omit<ModuleScores, "final_viability_score">,
  string
> = {
  problem_intensity: "Problem intensity from Tavily + SerpAPI signals",
  market_timing: "Growth trends and demand momentum",
  competition_pressure: "Market density and feature overlap",
  market_potential: "Demand strength and growth trajectory",
  execution_feasibility: "Technical and regulatory barriers",
};

function scoreColor(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 45) return "text-amber-400";
  return "text-red-400";
}

function scoreBg(score: number): string {
  if (score >= 70) return "bg-gradient-to-r from-emerald-400 to-emerald-500";
  if (score >= 45) return "bg-gradient-to-r from-amber-400 to-orange-400";
  return "bg-gradient-to-r from-red-400 to-red-500";
}

function verdictBadge(verdict: string): string {
  switch (verdict) {
    case "Strong":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
    case "Moderate":
      return "border-amber-500/30 bg-amber-500/10 text-amber-400";
    default:
      return "border-red-500/30 bg-red-500/10 text-red-400";
  }
}

function riskBadge(risk: string): string {
  switch (risk) {
    case "Low":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
    case "Medium":
      return "border-amber-500/30 bg-amber-500/10 text-amber-400";
    default:
      return "border-red-500/30 bg-red-500/10 text-red-400";
  }
}

function EvaluationContent() {
  const params = useParams();
  const router = useRouter();
  const ideaId = params.id as string;

  const [status, setStatus] = useState<Status>("loading");
  const [report, setReport] = useState<IdeaEvaluationReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [trendBannerDismissed, setTrendBannerDismissed] = useState(false);
  const dismissTrendBanner = useCallback(
    () => setTrendBannerDismissed(true),
    [],
  );

  // Agent status checks
  const [hasMR, setHasMR] = useState<boolean | null>(null);
  const [hasPD, setHasPD] = useState<boolean | null>(null);
  const [hasMVP, setHasMVP] = useState<boolean | null>(null);
  const [mvpGateOpen, setMvpGateOpen] = useState(false);

  useEffect(() => {
    if (!ideaId) return;
    getMarketResearchByIdea(ideaId)
      .then((r) => setHasMR(r.status === "completed"))
      .catch(() => setHasMR(false));
    getPitchDeckByIdea(ideaId)
      .then((r) => setHasPD(r.status === "completed"))
      .catch(() => setHasPD(false));
    getMVPByIdea(ideaId)
      .then((r) => setHasMVP(r.status === "generated"))
      .catch(() => setHasMVP(false));
  }, [ideaId]);

  useEffect(() => {
    if (!ideaId) {
      console.error("[EVAL] No ideaId — cannot evaluate");
      setError("Missing idea ID");
      setStatus("error");
      return;
    }

    let active = true;
    const controller = new AbortController();

    console.log(`[EVAL] useEffect fired — starting evaluation for ${ideaId}`);

    async function run() {
      setStatus("loading");
      setError(null);

      try {
        // 1. Try to load stored evaluation (GET — never re-runs pipeline)
        console.log(`[EVAL] Trying GET /ideas/${ideaId}/evaluation (stored)`);
        let data: IdeaEvaluationReport;
        try {
          data = await getEvaluation(ideaId);
          console.log("[EVAL] ✅ Loaded stored evaluation");
        } catch (getErr: unknown) {
          // 2. If 404, run evaluation (POST)
          if (getErr instanceof ApiError && getErr.status === 404) {
            console.log(
              `[EVAL] No stored evaluation — running POST /ideas/${ideaId}/evaluate`,
            );
            data = await evaluateIdea(ideaId);
            console.log("[EVAL] ✅ Evaluation completed");
          } else {
            throw getErr;
          }
        }

        // Validate response shape
        if (
          !data ||
          !data.module_scores ||
          typeof data.module_scores.final_viability_score !== "number"
        ) {
          throw new Error(
            "Invalid evaluation response — missing module_scores or final_viability_score",
          );
        }

        if (active) {
          setReport(data);
          setStatus("success");
          console.log("[EVAL] ✅ State set to SUCCESS");
        }
      } catch (err: unknown) {
        console.error("[EVAL] ❌ Evaluation error:", err);
        if (active) {
          setError(err instanceof Error ? err.message : "Evaluation failed");
          setStatus("error");
        }
      }
    }

    run();

    return () => {
      console.log("[EVAL] Cleanup — marking inactive");
      active = false;
      controller.abort();
    };
  }, [ideaId]);

  // ── Loading ──────────────────────────────────────────────
  if (status === "loading") {
    return <EvaluationLoader isLoading />;
  }

  // ── Error ────────────────────────────────────────────────
  if (status === "error") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center gap-4 px-6">
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-6 py-4 text-center">
          <p className="text-sm font-medium text-red-400">{error}</p>
        </div>
        <Link href="/ideas/new">
          <Button variant="secondary" size="sm">
            Try Another Idea
          </Button>
        </Link>
      </div>
    );
  }

  // ── Success ──────────────────────────────────────────────
  const {
    module_scores,
    summary,
    normalized_signals,
    competitor_names,
    trend_data_available,
  } = report!;
  const finalScore = module_scores.final_viability_score;

  const moduleKeys = Object.keys(MODULE_LABELS) as Array<
    keyof Omit<ModuleScores, "final_viability_score">
  >;

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      {/* Header */}
      <div className="mb-10">
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-indigo-400">
          Evaluation Report
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-50">
          Startup Viability Analysis
        </h1>
        <p className="mt-1 text-sm text-slate-500 font-mono">{ideaId}</p>
      </div>

      {/* ── Trend data warning banner ───────────────────── */}
      {trend_data_available === false && !trendBannerDismissed && (
        <div className="mb-6 flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
          <svg
            className="mt-0.5 h-4 w-4 shrink-0 text-amber-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-amber-300">
              Market trend data unavailable
            </p>
            <p className="mt-0.5 text-xs leading-relaxed text-amber-400/80">
              Market timing and potential scores may be incomplete due to
              insufficient external trend data.
            </p>
          </div>
          <button
            type="button"
            onClick={dismissTrendBanner}
            className="shrink-0 rounded p-0.5 text-amber-400/60 transition-colors hover:text-amber-300"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      )}

      {/* ── Hero score ────────────────────────────────────── */}
      <Card className="mb-8 text-center">
        <CardContent className="py-8">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-indigo-400">
            Final Viability Score
          </p>
          <p
            className={`text-6xl font-bold tabular-nums ${scoreColor(finalScore)}`}
          >
            {finalScore.toFixed(1)}
          </p>
          <p className="mt-1 text-sm text-slate-500">out of 100</p>

          <div className="mx-auto mt-4 h-2 w-48 overflow-hidden rounded-full bg-slate-800">
            <div
              className={`h-full rounded-full transition-all duration-700 ${scoreBg(finalScore)}`}
              style={{ width: `${finalScore}%` }}
            />
          </div>
        </CardContent>
      </Card>

      {/* ── Summary badges ────────────────────────────────── */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="space-y-1.5 text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Verdict
          </p>
          <span
            className={`inline-block rounded-full border px-3 py-1 text-sm font-semibold ${verdictBadge(summary.verdict)}`}
          >
            {summary.verdict}
          </span>
        </div>
        <div className="space-y-1.5 text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Risk Level
          </p>
          <span
            className={`inline-block rounded-full border px-3 py-1 text-sm font-semibold ${riskBadge(summary.risk_level)}`}
          >
            {summary.risk_level}
          </span>
        </div>
        <div className="space-y-1.5 text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Key Strength
          </p>
          <span className="inline-block rounded-full border border-indigo-500/20 bg-indigo-500/10 px-3 py-1 text-sm font-medium text-indigo-300">
            {summary.key_strength}
          </span>
        </div>
        <div className="space-y-1.5 text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Key Risk
          </p>
          <span className="inline-block rounded-full border border-red-500/20 bg-red-500/10 px-3 py-1 text-sm font-medium text-red-300">
            {summary.key_risk}
          </span>
        </div>
      </div>

      {/* ── Module score cards (expandable) ───────────────── */}
      <div className="mb-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-100">
            Module Scores
          </h2>
          <p className="text-xs text-slate-500">Click to expand formula</p>
        </div>
        <div className="space-y-3">
          {moduleKeys.map((key) => (
            <ScoreExplainer
              key={key}
              moduleKey={key}
              score={module_scores[key]}
              signals={normalized_signals}
            />
          ))}
        </div>

        {/* Final score formula */}
        <div className="mt-4 rounded-lg border border-slate-700/30 bg-slate-900/40 px-4 py-3">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-indigo-400">
            Final Viability Formula
          </p>
          <code className="text-xs leading-relaxed text-slate-400">
            {FINAL_SCORE_FORMULA}
          </code>
        </div>
      </div>

      {/* ── Discovered Competitors ─────────────────────── */}
      <div className="mb-8">
        <h2 className="mb-4 text-lg font-semibold text-slate-100">
          🏢 Discovered Competitors
        </h2>
        <CompetitorList competitors={competitor_names ?? []} />
      </div>

      {/* ── Normalized signals (expandable) ─────────────────── */}
      <div className="mb-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-100">
            Normalized Signals
          </h2>
          <p className="text-xs text-slate-500">Click to inspect formula</p>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {(Object.keys(normalized_signals) as Array<keyof NormalizedSignals>)
            .filter((key) => key !== "normalization_explanations")
            .map((key) => {
              const value = normalized_signals[key];
              if (typeof value !== "number") return null;
              const explanation =
                normalized_signals.normalization_explanations?.[key];
              return (
                <SignalExplainer
                  key={key}
                  signalKey={key}
                  value={value}
                  explanation={explanation}
                />
              );
            })}
        </div>
      </div>

      {/* ── Chart placeholder ─────────────────────────────── */}
      <Card className="mb-8">
        <CardContent className="flex h-48 items-center justify-center">
          <p className="text-sm text-slate-600">
            Radar chart & detailed visualizations coming soon
          </p>
        </CardContent>
      </Card>

      {/* ── Agent Actions ─────────────────────────────────── */}
      <div className="mb-8 rounded-2xl border border-white/10 bg-white/[0.02] p-6">
        <h2 className="mb-1 text-lg font-semibold text-slate-100">
          Next Steps
        </h2>
        <p className="mb-5 text-sm text-slate-500">
          Your idea is validated. Unlock the tools below.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {/* Pitch Deck */}
          <button
            onClick={() => router.push(`/ideas/${ideaId}/pitch-deck`)}
            className="group flex flex-col items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.02] p-5 transition-all duration-200 hover:bg-white/[0.05] hover:border-purple-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-purple-500/10"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10 transition-transform duration-200 group-hover:scale-110">
              <svg
                className="h-5 w-5 text-purple-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold text-slate-100">
              {hasPD ? "View Pitch Deck" : "Generate Pitch Deck"}
            </span>
            <span className="text-xs text-slate-500">Investor-ready deck</span>
          </button>

          {/* Market Research */}
          <button
            onClick={() => router.push(`/market-research/${ideaId}`)}
            className="group flex flex-col items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.02] p-5 transition-all duration-200 hover:bg-white/[0.05] hover:border-teal-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-teal-500/10"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-500/10 transition-transform duration-200 group-hover:scale-110">
              <svg
                className="h-5 w-5 text-teal-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold text-slate-100">
              {hasMR ? "View Market Research" : "Run Market Research"}
            </span>
            <span className="text-xs text-slate-500">
              TAM, SAM, SOM analysis
            </span>
          </button>

          {/* MVP Generator */}
          <button
            onClick={() => {
              if (hasMR) {
                router.push(`/mvp/${ideaId}`);
              } else {
                setMvpGateOpen(true);
              }
            }}
            className={`group flex flex-col items-center gap-2.5 rounded-xl border p-5 transition-all duration-200 ${
              hasMR
                ? "border-white/10 bg-white/[0.02] hover:bg-white/[0.05] hover:border-orange-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-orange-500/10"
                : "border-white/5 bg-white/[0.01] opacity-60 cursor-not-allowed"
            }`}
            title={hasMR ? undefined : "Requires completed market research"}
          >
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/10 transition-transform duration-200 ${hasMR ? "group-hover:scale-110" : ""}`}
            >
              <svg
                className="h-5 w-5 text-orange-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M11.42 15.17l-5.59-5.59a2.002 2.002 0 010-2.83l.81-.81a2.002 2.002 0 012.83 0L12 8.47l2.53-2.53a2.002 2.002 0 012.83 0l.81.81a2.002 2.002 0 010 2.83l-5.59 5.59a.996.996 0 01-1.41 0z"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold text-slate-100">
              {hasMVP ? "View MVP Blueprint" : "Generate MVP"}
            </span>
            <span className="text-xs text-slate-500">
              {hasMR
                ? "Feature plan & tech stack"
                : "Needs market research first"}
            </span>
          </button>

          {/* Legal Documents */}
          <button
            onClick={() => router.push(`/legal/${ideaId}`)}
            className="group flex flex-col items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.02] p-5 transition-all duration-200 hover:bg-white/[0.05] hover:border-emerald-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-emerald-500/10"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 transition-transform duration-200 group-hover:scale-110">
              <svg
                className="h-5 w-5 text-emerald-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold text-slate-100">
              Legal Documents
            </span>
            <span className="text-xs text-slate-500">
              NDAs, agreements & more
            </span>
          </button>

          {/* AI Chat Co-Founder */}
          <button
            onClick={() => router.push(`/chat/${ideaId}`)}
            className="group flex flex-col items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.02] p-5 transition-all duration-200 hover:bg-white/[0.05] hover:border-indigo-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-indigo-500/10"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10 transition-transform duration-200 group-hover:scale-110">
              <svg
                className="h-5 w-5 text-indigo-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold text-slate-100">
              AI Co-Founder
            </span>
            <span className="text-xs text-slate-500">
              Ask strategic questions
            </span>
          </button>
        </div>
      </div>

      {/* MVP Gating Modal */}
      <GatingModal
        open={mvpGateOpen}
        onClose={() => setMvpGateOpen(false)}
        title="Prerequisites Required"
        message="MVP generation requires a validated idea and completed market research. Run market research first to unlock this tool."
        icon={
          <svg
            className="h-7 w-7 text-amber-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
        }
        actions={[
          {
            label: "Run Market Research",
            href: `/market-research/${ideaId}`,
          },
        ]}
      />

      {/* ── Quick links ─────────────────────────────────────── */}
      <div className="flex justify-center gap-4">
        <Link href="/ideas/new">
          <Button variant="secondary">Evaluate Another Idea</Button>
        </Link>
        <Link href="/dashboard">
          <Button variant="ghost">Dashboard</Button>
        </Link>
      </div>
    </div>
  );
}

export default function EvaluationPage() {
  return (
    <RouteGuard>
      <EvaluationContent />
    </RouteGuard>
  );
}
