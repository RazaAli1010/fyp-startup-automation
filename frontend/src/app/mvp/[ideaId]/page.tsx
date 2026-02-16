"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  generateMVP,
  getMVPByIdea,
  getPitchDeckByIdea,
  ApiError,
} from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { RouteGuard } from "@/components/auth/route-guard";
import { BackButton } from "@/components/ui/back-button";
import type { MVPReportRecord, MVPBlueprintResponse } from "@/lib/types";

type Status = "idle" | "loading" | "generating" | "success" | "error";

function MVPContent() {
  const params = useParams();
  const router = useRouter();
  const ideaId = params.ideaId as string;

  const [status, setStatus] = useState<Status>("loading");
  const [report, setReport] = useState<MVPReportRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Agent status check
  const [hasPD, setHasPD] = useState<boolean | null>(null);

  useEffect(() => {
    if (!ideaId) return;
    getPitchDeckByIdea(ideaId)
      .then((r) => setHasPD(r.status === "completed"))
      .catch(() => setHasPD(false));
  }, [ideaId]);

  useEffect(() => {
    if (!ideaId) {
      console.error("[MVP] No ideaId");
      setError("Missing idea ID");
      setStatus("error");
      return;
    }

    let active = true;

    async function load() {
      console.log(`[MVP] Loading MVP for idea: ${ideaId}`);
      setStatus("loading");
      setError(null);
      try {
        const data = await getMVPByIdea(ideaId);
        console.log("[MVP] Loaded:", data.id, data.status);
        if (active) {
          setReport(data);
          setStatus(data.status === "generated" ? "success" : "idle");
        }
      } catch (err: unknown) {
        if (active) {
          if (err instanceof ApiError && err.status === 404) {
            console.log("[MVP] No existing MVP — showing generate button");
            setStatus("idle");
          } else {
            console.error("[MVP] Failed to load:", err);
            setError(err instanceof Error ? err.message : "Failed to load MVP");
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
    console.log(`[MVP] Generate clicked for idea: ${ideaId}`);
    setStatus("generating");
    setError(null);
    try {
      const data = await generateMVP(ideaId);
      console.log("[MVP] Generated:", data.id, data.status);
      setReport(data);
      setStatus("success");
    } catch (err: unknown) {
      console.error("[MVP] Generation failed:", err);
      const message =
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "MVP generation failed.";
      setError(message);
      setStatus("error");
    }
  }, [ideaId]);

  // ── Loading ──────────────────────────────────────────────
  if (status === "loading") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
        <Spinner size="lg" label="Loading MVP blueprint..." />
      </div>
    );
  }

  // ── Generating ───────────────────────────────────────────
  if (status === "generating") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
        <Spinner
          size="lg"
          label="Generating MVP blueprint..."
          sublabel="Analyzing scores, market research, and competitors"
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

  // ── Idle (no MVP yet) ────────────────────────────────────
  if (status === "idle" || !report || report.status !== "generated") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-6">
        <Card className="max-w-md text-center">
          <CardContent className="py-10">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-orange-500/20 to-amber-500/20">
              <svg
                className="h-8 w-8 text-orange-400"
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
            <h2 className="mb-2 text-lg font-semibold text-slate-100">
              Generate MVP Blueprint
            </h2>
            <p className="mb-6 text-sm text-slate-400">
              Create a structured MVP plan based on your evaluation scores and
              market research. Requires completed evaluation and market
              research.
            </p>
            <Button onClick={handleGenerate} size="lg">
              Generate MVP Blueprint
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Success — render blueprint ────────────────────────────
  const bp: MVPBlueprintResponse = report.blueprint!;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <BackButton fallback="/dashboard" />

      {/* Header */}
      <div className="mb-6 mt-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-orange-400">
              MVP Blueprint
            </p>
            <h1 className="text-2xl font-bold tracking-tight text-slate-50">
              {bp.mvp_type}
            </h1>
            {report.created_at && (
              <p className="mt-1 text-sm text-slate-500">
                Generated {new Date(report.created_at).toLocaleDateString()}
              </p>
            )}
          </div>
          <div className="flex gap-2">
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

        {/* Status badge */}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            MVP Ready
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-orange-500/30 bg-orange-500/10 px-3 py-1 text-xs font-semibold text-orange-300">
            {bp.mvp_type}
          </span>
        </div>
      </div>

      {/* ── Core Hypothesis + Primary User ─────────────────── */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="relative overflow-hidden rounded-xl border border-orange-500/20 bg-gradient-to-br from-orange-500/5 to-transparent p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-orange-500/10">
              <svg
                className="h-3.5 w-3.5 text-orange-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
                />
              </svg>
            </div>
            <p className="text-xs font-semibold uppercase tracking-wider text-orange-400">
              Core Hypothesis
            </p>
          </div>
          <p className="text-sm leading-relaxed text-slate-300">
            {bp.core_hypothesis}
          </p>
        </div>
        <div className="relative overflow-hidden rounded-xl border border-amber-500/20 bg-gradient-to-br from-amber-500/5 to-transparent p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/10">
              <svg
                className="h-3.5 w-3.5 text-amber-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
                />
              </svg>
            </div>
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-400">
              Primary User
            </p>
          </div>
          <p className="text-sm leading-relaxed text-slate-300">
            {bp.primary_user}
          </p>
        </div>
      </div>

      {/* ── Core Features ───────────────────────────────────── */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10">
            <svg
              className="h-4 w-4 text-indigo-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
              />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-slate-100">
            Core Features
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {bp.core_features.map((feat, idx) => (
            <div
              key={idx}
              className="group relative overflow-hidden rounded-xl border border-white/10 bg-white/[0.02] p-4 transition-all duration-200 hover:border-indigo-500/20 hover:bg-white/[0.04]"
            >
              <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-indigo-500 to-purple-500 opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-indigo-500/10 text-xs font-bold text-indigo-400">
                  {idx + 1}
                </span>
                <div>
                  <p className="text-sm font-semibold text-slate-100">
                    {feat.name}
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">
                    {feat.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Excluded Features ───────────────────────────────── */}
      {bp.excluded_features.length > 0 && (
        <div className="mb-8">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">
            Excluded Features
          </h2>
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
            <ul className="space-y-2">
              {bp.excluded_features.map((feat, i) => (
                <li key={i} className="flex gap-2 text-sm text-slate-500">
                  <span className="shrink-0 text-red-500/60">✕</span>
                  {feat}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* ── User Flow ───────────────────────────────────────── */}
      <div className="mb-8">
        <h2 className="mb-4 text-lg font-semibold text-slate-100">User Flow</h2>
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
          <ol className="space-y-3">
            {bp.user_flow.map((step, i) => (
              <li key={i} className="flex gap-3 text-sm text-slate-300">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-orange-500/10 text-xs font-bold text-orange-400">
                  {i + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </div>
      </div>

      {/* ── Tech Stack ──────────────────────────────────────── */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/10">
            <svg
              className="h-4 w-4 text-cyan-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z"
              />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-slate-100">
            Recommended Tech Stack
          </h2>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {Object.entries(bp.recommended_tech_stack).map(([key, value]) => (
            <div
              key={key}
              className="rounded-xl border border-cyan-500/10 bg-cyan-500/5 px-4 py-3 transition-all duration-200 hover:border-cyan-500/20"
            >
              <p className="text-[10px] font-bold uppercase tracking-widest text-cyan-400">
                {key}
              </p>
              <p className="mt-1 text-sm font-medium text-slate-200">{value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Build Plan ──────────────────────────────────────── */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10">
            <svg
              className="h-4 w-4 text-purple-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5"
              />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-slate-100">Build Plan</h2>
        </div>
        <div className="mb-4 flex items-center gap-4 pl-10">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-500/10 px-3 py-1 text-xs font-semibold text-purple-300">
            ~{bp.build_plan.total_estimated_weeks} weeks
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-300">
            {bp.build_plan.team_size} team member
            {bp.build_plan.team_size > 1 ? "s" : ""}
          </span>
        </div>
        <div className="space-y-3">
          {bp.build_plan.phases.map((phase, i) => (
            <div
              key={i}
              className="relative rounded-xl border border-white/10 bg-white/[0.02] p-4 pl-5"
            >
              <div className="absolute left-0 top-0 bottom-0 w-1 rounded-l-xl bg-gradient-to-b from-purple-500 to-indigo-500" />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-purple-500/10 text-xs font-bold text-purple-400">
                    {i + 1}
                  </span>
                  <p className="text-sm font-semibold text-slate-100">
                    {phase.phase}
                  </p>
                </div>
                <span className="rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-xs font-medium text-indigo-400">
                  {phase.duration}
                </span>
              </div>
              <ul className="mt-2 ml-8 space-y-1">
                {phase.tasks.map((task, j) => (
                  <li
                    key={j}
                    className="flex items-start gap-2 text-xs text-slate-400"
                  >
                    <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-purple-400/60" />
                    {task}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* ── Validation Plan ─────────────────────────────────── */}
      <div className="mb-8">
        <h2 className="mb-4 text-lg font-semibold text-slate-100">
          Validation Plan
          <span className="ml-2 text-sm font-normal text-slate-500">
            {bp.validation_plan.timeline}
          </span>
        </h2>
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
          <div className="mb-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              Success Criteria
            </p>
            <p className="mt-1 text-sm text-slate-300">
              {bp.validation_plan.success_criteria}
            </p>
          </div>

          <div className="mb-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
              Key Metrics
            </p>
            <ul className="mt-2 space-y-1">
              {bp.validation_plan.key_metrics.map((m, i) => (
                <li key={i} className="flex gap-2 text-sm text-slate-400">
                  <span className="shrink-0 text-cyan-500/60">-</span>
                  {m}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-purple-400">
              Validation Methods
            </p>
            <ul className="mt-2 space-y-1">
              {bp.validation_plan.validation_methods.map((m, i) => (
                <li key={i} className="flex gap-2 text-sm text-slate-400">
                  <span className="shrink-0 text-purple-500/60">-</span>
                  {m}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* ── Risk Notes ──────────────────────────────────────── */}
      {bp.risk_notes.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10">
              <svg
                className="h-4 w-4 text-amber-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-slate-100">Risk Notes</h2>
          </div>
          <div className="space-y-2">
            {bp.risk_notes.map((note, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3"
              >
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/10 text-[10px] font-bold text-amber-400">
                  {i + 1}
                </span>
                <p className="text-sm leading-relaxed text-amber-400/80">
                  {note}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Agent Actions ─────────────────────────────────── */}
      <div className="mb-8 rounded-2xl border border-white/10 bg-white/[0.02] p-6">
        <h2 className="mb-1 text-lg font-semibold text-slate-100">
          Related Tools
        </h2>
        <p className="mb-5 text-sm text-slate-500">
          Your MVP blueprint is ready. Explore other reports.
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
              View Market Research
            </span>
            <span className="text-xs text-slate-500">
              TAM, SAM, SOM analysis
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

export default function MVPPage() {
  return (
    <RouteGuard>
      <MVPContent />
    </RouteGuard>
  );
}
