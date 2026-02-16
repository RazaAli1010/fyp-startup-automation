"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  generateMarketResearch,
  getMarketResearchByIdea,
  getPitchDeckByIdea,
  getMVPByIdea,
  ApiError,
} from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { RouteGuard } from "@/components/auth/route-guard";
import type { MarketResearchRecord, MarketCompetitor } from "@/lib/types";

type Status = "idle" | "loading" | "generating" | "success" | "error";

function formatCurrency(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function confidenceColor(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 50) return "text-amber-400";
  return "text-red-400";
}

function demandColor(score: number): string {
  if (score >= 70) return "text-emerald-400 bg-emerald-500/10";
  if (score >= 45) return "text-amber-400 bg-amber-500/10";
  return "text-red-400 bg-red-500/10";
}

function MarketResearchContent() {
  const params = useParams();
  const router = useRouter();
  const ideaId = params.ideaId as string;

  const [status, setStatus] = useState<Status>("loading");
  const [research, setResearch] = useState<MarketResearchRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Agent status checks
  const [hasPD, setHasPD] = useState<boolean | null>(null);
  const [hasMVP, setHasMVP] = useState<boolean | null>(null);

  useEffect(() => {
    if (!ideaId) return;
    getPitchDeckByIdea(ideaId)
      .then((r) => setHasPD(r.status === "completed"))
      .catch(() => setHasPD(false));
    getMVPByIdea(ideaId)
      .then((r) => setHasMVP(r.status === "generated"))
      .catch(() => setHasMVP(false));
  }, [ideaId]);

  useEffect(() => {
    if (!ideaId) {
      console.error("[RESEARCH] No ideaId");
      setError("Missing idea ID");
      setStatus("error");
      return;
    }

    let active = true;

    async function load() {
      console.log(`[RESEARCH] Loading research for idea: ${ideaId}`);
      setStatus("loading");
      setError(null);
      try {
        const data = await getMarketResearchByIdea(ideaId);
        console.log("[RESEARCH] Loaded:", data.id, data.status);
        if (active) {
          setResearch(data);
          setStatus(data.status === "completed" ? "success" : "idle");
        }
      } catch (err: unknown) {
        if (active) {
          if (err instanceof ApiError && err.status === 404) {
            console.log(
              "[RESEARCH] No existing research — showing generate button",
            );
            setStatus("idle");
          } else {
            console.error("[RESEARCH] Failed to load:", err);
            setError(
              err instanceof Error ? err.message : "Failed to load research",
            );
            setStatus("error");
          }
        }
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [ideaId]);

  const handleGenerate = useCallback(async () => {
    console.log(`[RESEARCH] Generate clicked for idea: ${ideaId}`);
    setStatus("generating");
    setError(null);
    try {
      const data = await generateMarketResearch(ideaId);
      console.log("[RESEARCH] Generated:", data.id, data.status);
      setResearch(data);
      setStatus("success");
    } catch (err: unknown) {
      console.error("[RESEARCH] Generation failed:", err);
      const message =
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Market research generation failed.";
      setError(message);
      setStatus("error");
    }
  }, [ideaId]);

  // ── Loading ──────────────────────────────────────────────
  if (status === "loading") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
        <Spinner size="lg" label="Loading market research..." />
      </div>
    );
  }

  // ── Generating ───────────────────────────────────────────
  if (status === "generating") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
        <Spinner
          size="lg"
          label="Generating market research..."
          sublabel="Calculating TAM/SAM/SOM and market confidence"
        />
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────
  if (status === "error") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center gap-4 px-6">
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-6 py-4 text-center">
          <p className="text-sm font-medium text-red-400">{error}</p>
        </div>
        <div className="flex gap-3">
          <Button variant="secondary" size="sm" onClick={handleGenerate}>
            Try Again
          </Button>
          <Link href={`/ideas/${ideaId}`}>
            <Button variant="ghost" size="sm">
              Back to Evaluation
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  // ── Idle (no research yet) ──────────────────────────────
  if (status === "idle" || !research || research.status !== "completed") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-6">
        <Card className="max-w-md text-center">
          <CardContent className="py-10">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-teal-500/20 to-cyan-500/20">
              <svg
                className="h-8 w-8 text-teal-400"
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
            <h2 className="mb-2 text-lg font-semibold text-slate-100">
              Generate Market Research
            </h2>
            <p className="mb-6 text-sm text-slate-400">
              Estimate TAM, SAM, SOM, growth rates, and market confidence based
              on your idea&apos;s market data.
            </p>
            <Button onClick={handleGenerate} size="lg">
              Generate Market Research
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Success — completed research ─────────────────────────
  const r = research;
  const competitors: MarketCompetitor[] = r.competitors ?? [];
  const assumptions: string[] = r.assumptions ?? [];
  const confidence = r.confidence;
  const sources: string[] = r.sources ?? [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-teal-400">
              Market Research
            </p>
            <h1 className="text-2xl font-bold tracking-tight text-slate-50">
              Market Size & Opportunity Analysis
            </h1>
            {r.created_at && (
              <p className="mt-1 text-sm text-slate-500">
                Generated {new Date(r.created_at).toLocaleDateString()}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={handleGenerate}>
              Regenerate
            </Button>
            <Link href={`/ideas/${ideaId}`}>
              <Button variant="ghost" size="sm">
                Back to Evaluation
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">
                Dashboard
              </Button>
            </Link>
          </div>
        </div>

        {/* Status badges */}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Completed
          </span>
          {r.demand_strength != null && (
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border border-white/10 px-3 py-1 text-xs font-semibold ${demandColor(r.demand_strength)}`}
            >
              Demand: {r.demand_strength.toFixed(0)}/100
            </span>
          )}
          {confidence && (
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border border-white/10 px-3 py-1 text-xs font-semibold ${confidenceColor(confidence.overall)}`}
            >
              Confidence: {confidence.overall}%
            </span>
          )}
        </div>
      </div>

      {/* ── TAM / SAM / SOM Cards ─────────────────────────── */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* TAM */}
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-teal-400">
            Total Addressable Market (TAM)
          </p>
          <p className="mt-2 text-2xl font-bold tabular-nums text-slate-50">
            {r.tam_min != null && r.tam_max != null
              ? `${formatCurrency(r.tam_min)} – ${formatCurrency(r.tam_max)}`
              : "N/A"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Total market demand for your product category
          </p>
          {confidence?.tam && (
            <p
              className={`mt-2 text-xs ${confidenceColor(confidence.tam.score)}`}
            >
              Confidence: {confidence.tam.score}%
            </p>
          )}
        </div>

        {/* SAM */}
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
            Serviceable Addressable Market (SAM)
          </p>
          <p className="mt-2 text-2xl font-bold tabular-nums text-slate-50">
            {r.sam_min != null && r.sam_max != null
              ? `${formatCurrency(r.sam_min)} – ${formatCurrency(r.sam_max)}`
              : "N/A"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Market segment you can realistically target
          </p>
          {confidence?.sam && (
            <p
              className={`mt-2 text-xs ${confidenceColor(confidence.sam.score)}`}
            >
              Confidence: {confidence.sam.score}%
            </p>
          )}
        </div>

        {/* SOM */}
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
            Serviceable Obtainable Market (SOM)
          </p>
          <p className="mt-2 text-2xl font-bold tabular-nums text-slate-50">
            {r.som_min != null && r.som_max != null
              ? `${formatCurrency(r.som_min)} – ${formatCurrency(r.som_max)}`
              : "N/A"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Realistic short-term revenue capture (capped at 5% SAM)
          </p>
          {confidence?.som && (
            <p
              className={`mt-2 text-xs ${confidenceColor(confidence.som.score)}`}
            >
              Confidence: {confidence.som.score}%
            </p>
          )}
        </div>
      </div>

      {/* ── Growth & Revenue ──────────────────────────────── */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            ARPU (Annual)
          </p>
          <p className="mt-2 text-2xl font-bold tabular-nums text-slate-50">
            {r.arpu_annual != null ? formatCurrency(r.arpu_annual) : "N/A"}
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Growth Rate (Est.)
          </p>
          <p className="mt-2 text-2xl font-bold tabular-nums text-slate-50">
            {r.growth_rate_estimate != null
              ? `${r.growth_rate_estimate.toFixed(1)}%`
              : "N/A"}
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Demand Strength
          </p>
          <p
            className={`mt-2 text-2xl font-bold tabular-nums ${
              r.demand_strength != null
                ? demandColor(r.demand_strength).split(" ")[0]
                : "text-slate-50"
            }`}
          >
            {r.demand_strength != null
              ? `${r.demand_strength.toFixed(1)}/100`
              : "N/A"}
          </p>
        </div>
      </div>

      {/* ── Competitors ─────────────────────────────────── */}
      {competitors.length > 0 && (
        <div className="mb-8">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">
            Competitors ({r.competitor_count ?? competitors.length})
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {competitors.map((comp, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-white/10 bg-white/[0.02] p-4"
              >
                <p className="text-sm font-semibold text-slate-100">
                  {comp.name}
                </p>
                {comp.description && (
                  <p className="mt-1 line-clamp-3 text-xs text-slate-500">
                    {comp.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Confidence Breakdown ──────────────────────────── */}
      {confidence && (
        <div className="mb-8">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">
            Confidence Assessment
          </h2>
          <div className="space-y-3">
            {(["tam", "sam", "som"] as const).map((key) => {
              const c = confidence[key];
              if (!c) return null;
              return (
                <div
                  key={key}
                  className="rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold uppercase text-slate-300">
                      {key.toUpperCase()}
                    </p>
                    <span
                      className={`text-sm font-bold tabular-nums ${confidenceColor(c.score)}`}
                    >
                      {c.score}%
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{c.explanation}</p>
                </div>
              );
            })}
            {confidence.note && (
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-2.5">
                <p className="text-xs text-amber-400/80">{confidence.note}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Assumptions ───────────────────────────────────── */}
      {assumptions.length > 0 && (
        <div className="mb-8">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">
            Assumptions
          </h2>
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
            <ul className="space-y-2">
              {assumptions.map((a, i) => (
                <li key={i} className="flex gap-2 text-sm text-slate-400">
                  <span className="shrink-0 text-teal-500">-</span>
                  {a}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* ── Sources ───────────────────────────────────────── */}
      {sources.length > 0 && (
        <div className="mb-8">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">
            Data Sources
          </h2>
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
            <ul className="space-y-1">
              {sources.map((s, i) => (
                <li key={i} className="text-sm text-slate-500">
                  - {s}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* ── Agent Actions ─────────────────────────────────── */}
      <div className="mb-8 rounded-2xl border border-white/10 bg-white/[0.02] p-6">
        <h2 className="mb-1 text-lg font-semibold text-slate-100">
          Continue Building
        </h2>
        <p className="mb-5 text-sm text-slate-500">
          Market research is complete. Use these tools next.
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

          {/* MVP Blueprint */}
          <button
            onClick={() => router.push(`/mvp/${ideaId}`)}
            className="group flex flex-col items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.02] p-5 transition-all duration-200 hover:bg-white/[0.05] hover:border-orange-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-orange-500/10"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/10 transition-transform duration-200 group-hover:scale-110">
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
              {hasMVP ? "View MVP Blueprint" : "Generate MVP Blueprint"}
            </span>
            <span className="text-xs text-slate-500">
              Feature plan & tech stack
            </span>
          </button>

          {/* View Evaluation */}
          <button
            onClick={() => router.push(`/ideas/${ideaId}`)}
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
                  d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold text-slate-100">
              View Evaluation
            </span>
            <span className="text-xs text-slate-500">Viability scores</span>
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

      {/* ── Quick links ─────────────────────────────────────── */}
      <div className="flex justify-center gap-4">
        <Link href="/dashboard">
          <Button variant="ghost">Dashboard</Button>
        </Link>
      </div>
    </div>
  );
}

export default function MarketResearchPage() {
  return (
    <RouteGuard>
      <MarketResearchContent />
    </RouteGuard>
  );
}
