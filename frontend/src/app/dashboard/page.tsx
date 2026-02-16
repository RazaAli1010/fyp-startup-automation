"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getDashboard } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { RouteGuard } from "@/components/auth/route-guard";
import type { DashboardResponse } from "@/lib/types";

function DashboardContent() {
  const { user } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedIdeaId, setSelectedIdeaId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      console.log("[DASH] Fetching dashboard data");
      try {
        const res = await getDashboard();
        console.log(
          `[DASH] Received ${res.ideas.length} ideas, ${res.pitch_decks?.length ?? 0} decks`,
        );
        if (active) setData(res);
      } catch (err) {
        console.error("[DASH] Failed to fetch dashboard:", err);
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
        <Spinner size="lg" label="Loading dashboard..." />
      </div>
    );
  }

  const ideas = data?.ideas ?? [];
  const pitchDecks = data?.pitch_decks ?? [];
  const marketResearch = data?.market_research ?? [];
  const mvpReports = data?.mvp_reports ?? [];
  const legalDocuments = data?.legal_documents ?? [];
  const displayName = user?.username || user?.email?.split("@")[0] || "there";

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      {/* ── Gradient hero header ─────────────────────────────── */}
      <div className="relative mb-10 overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-indigo-500/10 via-purple-500/5 to-transparent p-8">
        <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-indigo-500/10 blur-3xl" />
        <div className="absolute -bottom-10 -left-10 h-32 w-32 rounded-full bg-purple-500/10 blur-3xl" />
        <div className="relative">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-xl font-bold text-white shadow-lg shadow-indigo-500/25">
              {displayName[0]?.toUpperCase() ?? "U"}
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-50">
                Welcome back, {displayName}
              </h1>
              <p className="mt-1 text-sm text-slate-400">
                Let&apos;s validate your next big idea
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Stats row ────────────────────────────────────────── */}
      <div className="mb-8 grid grid-cols-3 gap-4 sm:grid-cols-6">
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-center">
          <p className="text-2xl font-bold tabular-nums text-slate-50">
            {ideas.length}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">Total Ideas</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-center">
          <p className="text-2xl font-bold tabular-nums text-slate-50">
            {ideas.filter((i) => i.final_viability_score != null).length}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">Evaluated</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-center">
          <p className="text-2xl font-bold tabular-nums text-slate-50">
            {pitchDecks.filter((d) => d.status === "completed").length}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">Pitch Decks</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-center">
          <p className="text-2xl font-bold tabular-nums text-slate-50">
            {marketResearch.filter((r) => r.status === "completed").length}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">Research</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-center">
          <p className="text-2xl font-bold tabular-nums text-slate-50">
            {mvpReports.filter((m) => m.status === "generated").length}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">MVPs</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-center">
          <p className="text-2xl font-bold tabular-nums text-slate-50">
            {legalDocuments.filter((l) => l.status === "generated").length}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">Legal Docs</p>
        </div>
      </div>

      {/* ── Profile card ─────────────────────────────────────── */}
      <div className="mb-8 rounded-xl border border-white/10 bg-white/[0.02] p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <p className="text-sm font-medium text-slate-100">
                @{user?.username}
              </p>
              <p className="text-xs text-slate-500">{user?.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                user?.auth_provider === "google"
                  ? "bg-blue-500/10 text-blue-400"
                  : "bg-slate-500/10 text-slate-400"
              }`}
            >
              {user?.auth_provider === "google" ? "Google" : "Email"}
            </span>
            {user?.is_email_verified && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-400">
                <svg
                  className="h-3 w-3"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Verified
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Ideas section ────────────────────────────────────── */}
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-100">Your Ideas</h2>
        <Link href="/ideas/new">
          <Button size="sm">+ New Idea</Button>
        </Link>
      </div>

      {ideas.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.01] px-6 py-16 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-indigo-500/10">
            <svg
              className="h-7 w-7 text-indigo-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 4.5v15m7.5-7.5h-15"
              />
            </svg>
          </div>
          <h3 className="text-base font-semibold text-slate-200">
            You haven&apos;t validated any ideas yet
          </h3>
          <p className="mt-1.5 text-sm text-slate-500">
            Submit your first startup idea and let our AI agents evaluate it
            with real market data.
          </p>
          <Link href="/ideas/new" className="mt-6 inline-block">
            <Button>
              Validate New Idea
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
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {ideas.map((idea) => (
            <Link
              key={idea.id}
              href={`/ideas/${idea.id}`}
              className="group block rounded-xl border border-white/10 bg-white/[0.02] p-4 transition-all hover:bg-white/[0.04] hover:border-indigo-500/30"
            >
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-100 group-hover:text-indigo-300 transition-colors">
                    {idea.startup_name}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {idea.industry}
                  </p>
                </div>
                <div className="ml-4 flex items-center gap-3">
                  {idea.final_viability_score != null ? (
                    <span
                      className={`rounded-md px-2 py-0.5 text-sm font-bold tabular-nums ${
                        idea.final_viability_score >= 75
                          ? "bg-emerald-500/10 text-emerald-400"
                          : idea.final_viability_score >= 55
                            ? "bg-amber-500/10 text-amber-400"
                            : "bg-red-500/10 text-red-400"
                      }`}
                    >
                      {idea.final_viability_score.toFixed(1)}
                    </span>
                  ) : (
                    <span className="rounded-md bg-slate-500/10 px-2 py-0.5 text-xs font-medium text-slate-500">
                      Not evaluated
                    </span>
                  )}
                  {idea.created_at && (
                    <span className="text-xs text-slate-600">
                      {new Date(idea.created_at).toLocaleDateString()}
                    </span>
                  )}
                  <svg
                    className="h-4 w-4 text-slate-600 group-hover:text-indigo-400 transition-colors"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* ── Agent Hub ──────────────────────────────────────────── */}
      {ideas.length > 0 &&
        (() => {
          const activeIdea = selectedIdeaId
            ? ideas.find((i) => i.id === selectedIdeaId)
            : ideas[0];
          if (!activeIdea) return null;

          const isValidated = activeIdea.final_viability_score != null;
          const hasMR = marketResearch.some(
            (r) => r.idea_id === activeIdea.id && r.status === "completed",
          );
          const hasPD = pitchDecks.some(
            (d) => d.idea_id === activeIdea.id && d.status === "completed",
          );
          const hasMVP = mvpReports.some(
            (m) => m.idea_id === activeIdea.id && m.status === "generated",
          );
          const hasLegal = legalDocuments.some(
            (l) => l.idea_id === activeIdea.id && l.status === "generated",
          );

          const agents = [
            {
              key: "validation",
              label: "Idea Validation",
              desc: "AI-powered viability scoring",
              icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
              color: "indigo",
              enabled: true,
              done: isValidated,
              href: `/ideas/${activeIdea.id}`,
              tooltip: "",
            },
            {
              key: "research",
              label: "Market Research",
              desc: "TAM, SAM, SOM analysis",
              icon: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z",
              color: "teal",
              enabled: isValidated,
              done: hasMR,
              href: `/market-research/${activeIdea.id}`,
              tooltip: !isValidated ? "Validate idea first" : "",
            },
            {
              key: "pitch",
              label: "Pitch Deck",
              desc: "Investor-ready presentation",
              icon: "M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5",
              color: "purple",
              enabled: isValidated,
              done: hasPD,
              href: `/ideas/${activeIdea.id}/pitch-deck`,
              tooltip: !isValidated ? "Validate idea first" : "",
            },
            {
              key: "mvp",
              label: "MVP Generator",
              desc: "Build plan & tech stack",
              icon: "M11.42 15.17l-5.59-5.59a2.002 2.002 0 010-2.83l.81-.81a2.002 2.002 0 012.83 0L12 8.47l2.53-2.53a2.002 2.002 0 012.83 0l.81.81a2.002 2.002 0 010 2.83l-5.59 5.59a.996.996 0 01-1.41 0z",
              color: "orange",
              enabled: isValidated && hasMR,
              done: hasMVP,
              href: `/mvp/${activeIdea.id}`,
              tooltip: !isValidated
                ? "Validate idea first"
                : !hasMR
                  ? "Complete market research first"
                  : "",
            },
            {
              key: "legal",
              label: "Legal Generator",
              desc: "NDAs, agreements & more",
              icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z",
              color: "emerald",
              enabled: isValidated,
              done: hasLegal,
              href: `/legal/${activeIdea.id}`,
              tooltip: !isValidated ? "Validate idea first" : "",
            },
            {
              key: "chat",
              label: "AI Co-Founder",
              desc: "Strategic Q&A chat",
              icon: "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z",
              color: "cyan",
              enabled: isValidated,
              done: false,
              href: `/chat/${activeIdea.id}`,
              tooltip: !isValidated ? "Validate idea first" : "",
            },
          ];

          const colorMap: Record<
            string,
            {
              bg: string;
              text: string;
              border: string;
              shadow: string;
              gradient: string;
            }
          > = {
            indigo: {
              bg: "bg-indigo-500/10",
              text: "text-indigo-400",
              border: "border-indigo-500/30",
              shadow: "shadow-indigo-500/10",
              gradient: "from-indigo-500 to-indigo-600",
            },
            teal: {
              bg: "bg-teal-500/10",
              text: "text-teal-400",
              border: "border-teal-500/30",
              shadow: "shadow-teal-500/10",
              gradient: "from-teal-500 to-teal-600",
            },
            purple: {
              bg: "bg-purple-500/10",
              text: "text-purple-400",
              border: "border-purple-500/30",
              shadow: "shadow-purple-500/10",
              gradient: "from-purple-500 to-purple-600",
            },
            orange: {
              bg: "bg-orange-500/10",
              text: "text-orange-400",
              border: "border-orange-500/30",
              shadow: "shadow-orange-500/10",
              gradient: "from-orange-500 to-orange-600",
            },
            emerald: {
              bg: "bg-emerald-500/10",
              text: "text-emerald-400",
              border: "border-emerald-500/30",
              shadow: "shadow-emerald-500/10",
              gradient: "from-emerald-500 to-emerald-600",
            },
            cyan: {
              bg: "bg-cyan-500/10",
              text: "text-cyan-400",
              border: "border-cyan-500/30",
              shadow: "shadow-cyan-500/10",
              gradient: "from-cyan-500 to-cyan-600",
            },
          };

          return (
            <div className="mb-10 mt-10">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-100">
                    Agent Hub
                  </h2>
                  <p className="mt-0.5 text-xs text-slate-500">
                    Tools for{" "}
                    <span className="font-medium text-slate-300">
                      {activeIdea.startup_name}
                    </span>
                  </p>
                </div>
                {ideas.length > 1 && (
                  <select
                    value={activeIdea.id}
                    onChange={(e) => setSelectedIdeaId(e.target.value)}
                    className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300 outline-none focus:border-indigo-500/50"
                  >
                    {ideas.map((idea) => (
                      <option
                        key={idea.id}
                        value={idea.id}
                        className="bg-[#0f172a]"
                      >
                        {idea.startup_name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {agents.map((agent) => {
                  const c = colorMap[agent.color];
                  return (
                    <div key={agent.key} className="relative group">
                      <button
                        disabled={!agent.enabled}
                        onClick={() => router.push(agent.href)}
                        className={`relative w-full flex flex-col items-center gap-3 rounded-xl border p-5 transition-all duration-200 ${
                          agent.enabled
                            ? `border-white/10 bg-white/[0.02] hover:${c.border} hover:bg-white/[0.05] hover:-translate-y-1 hover:shadow-lg hover:${c.shadow} cursor-pointer`
                            : "border-white/5 bg-white/[0.01] opacity-50 cursor-not-allowed"
                        }`}
                      >
                        {agent.done && (
                          <span className="absolute top-2.5 right-2.5 flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                          </span>
                        )}
                        <div
                          className={`flex h-11 w-11 items-center justify-center rounded-xl ${agent.enabled ? c.bg : "bg-slate-500/10"} transition-transform duration-200 ${agent.enabled ? "group-hover:scale-110" : ""}`}
                        >
                          <svg
                            className={`h-5 w-5 ${agent.enabled ? c.text : "text-slate-600"}`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={1.5}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d={agent.icon}
                            />
                          </svg>
                        </div>
                        <div className="text-center">
                          <p
                            className={`text-sm font-semibold ${agent.enabled ? "text-slate-100" : "text-slate-500"}`}
                          >
                            {agent.label}
                          </p>
                          <p className="mt-0.5 text-[11px] text-slate-500">
                            {agent.desc}
                          </p>
                        </div>
                        {agent.done && (
                          <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                            Completed
                          </span>
                        )}
                        {!agent.enabled && (
                          <span className="rounded-full bg-slate-500/10 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                            Locked
                          </span>
                        )}
                        {agent.enabled && !agent.done && (
                          <span
                            className={`rounded-full bg-gradient-to-r ${c.gradient} px-3 py-0.5 text-[10px] font-semibold text-white shadow-sm`}
                          >
                            Launch
                          </span>
                        )}
                      </button>
                      {agent.tooltip && !agent.enabled && (
                        <div className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-800 px-2.5 py-1 text-[10px] font-medium text-slate-300 opacity-0 shadow-lg transition-opacity group-hover:opacity-100 z-10">
                          {agent.tooltip}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })()}

      {/* ── Pitch Deck History ─────────────────────────────────── */}
      <div className="mb-5 mt-10 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-100">Pitch Decks</h2>
      </div>

      {pitchDecks.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.01] px-6 py-12 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-purple-500/10">
            <svg
              className="h-7 w-7 text-purple-400"
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
          <h3 className="text-base font-semibold text-slate-200">
            No pitch decks yet
          </h3>
          <p className="mt-1.5 text-sm text-slate-500">
            Generate a pitch deck from any evaluated idea to see it here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {pitchDecks.map((deck) => (
            <Link
              key={deck.id}
              href={`/ideas/${deck.idea_id}/pitch-deck`}
              className="group block rounded-xl border border-white/10 bg-white/[0.02] p-4 transition-all hover:bg-white/[0.04] hover:border-purple-500/30"
            >
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-100 group-hover:text-purple-300 transition-colors">
                    {deck.title}
                  </p>
                  {deck.created_at && (
                    <p className="mt-0.5 text-xs text-slate-500">
                      {new Date(deck.created_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
                <div className="ml-4 flex items-center gap-3">
                  <span
                    className={`rounded-md px-2 py-0.5 text-xs font-medium ${
                      deck.status === "completed"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : deck.status === "pending"
                          ? "bg-amber-500/10 text-amber-400"
                          : "bg-red-500/10 text-red-400"
                    }`}
                  >
                    {deck.status === "completed"
                      ? "Ready"
                      : deck.status === "pending"
                        ? "Pending"
                        : "Failed"}
                  </span>
                  {deck.view_url && (
                    <a
                      href={deck.view_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="rounded-md bg-purple-500/10 px-2 py-0.5 text-xs font-medium text-purple-400 hover:bg-purple-500/20 transition-colors"
                    >
                      View
                    </a>
                  )}
                  <svg
                    className="h-4 w-4 text-slate-600 group-hover:text-purple-400 transition-colors"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
      {/* ── Market Research ─────────────────────────────────── */}
      <div className="mb-5 mt-10 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-100">
          Market Research
        </h2>
      </div>

      {marketResearch.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.01] px-6 py-12 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-teal-500/10">
            <svg
              className="h-7 w-7 text-teal-400"
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
          <h3 className="text-base font-semibold text-slate-200">
            No market research yet
          </h3>
          <p className="mt-1.5 text-sm text-slate-500">
            Generate market research from any idea to estimate TAM, SAM, SOM and
            market confidence.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {marketResearch.map((r) => (
            <Link
              key={r.id}
              href={`/market-research/${r.idea_id}`}
              className="group block rounded-xl border border-white/10 bg-white/[0.02] p-4 transition-all hover:bg-white/[0.04] hover:border-teal-500/30"
            >
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-100 group-hover:text-teal-300 transition-colors">
                    {ideas.find((i) => i.id === r.idea_id)?.startup_name ??
                      "Market Research"}
                  </p>
                  <div className="mt-1 flex items-center gap-3 text-xs text-slate-500">
                    {r.tam_max != null && (
                      <span>TAM: ${(r.tam_max / 1e9).toFixed(1)}B</span>
                    )}
                    {r.som_max != null && (
                      <span>SOM: ${(r.som_max / 1e6).toFixed(1)}M</span>
                    )}
                    {r.demand_strength != null && (
                      <span>Demand: {r.demand_strength.toFixed(0)}/100</span>
                    )}
                  </div>
                </div>
                <div className="ml-4 flex items-center gap-3">
                  <span
                    className={`rounded-md px-2 py-0.5 text-xs font-medium ${
                      r.status === "completed"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : r.status === "pending"
                          ? "bg-amber-500/10 text-amber-400"
                          : "bg-red-500/10 text-red-400"
                    }`}
                  >
                    {r.status === "completed"
                      ? "Ready"
                      : r.status === "pending"
                        ? "Pending"
                        : "Failed"}
                  </span>
                  <svg
                    className="h-4 w-4 text-slate-600 group-hover:text-teal-400 transition-colors"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* ── MVP Blueprints ────────────────────────────────────── */}
      <div className="mb-5 mt-10 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-100">MVP Blueprints</h2>
      </div>

      {mvpReports.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.01] px-6 py-12 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-orange-500/10">
            <svg
              className="h-7 w-7 text-orange-400"
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
          <h3 className="text-base font-semibold text-slate-200">
            No MVP blueprints yet
          </h3>
          <p className="mt-1.5 text-sm text-slate-500">
            Generate an MVP blueprint from any evaluated idea with completed
            market research.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {mvpReports.map((m) => (
            <Link
              key={m.id}
              href={`/mvp/${m.idea_id}`}
              className="group block rounded-xl border border-white/10 bg-white/[0.02] p-4 transition-all hover:bg-white/[0.04] hover:border-orange-500/30"
            >
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-100 group-hover:text-orange-300 transition-colors">
                    {ideas.find((i) => i.id === m.idea_id)?.startup_name ??
                      "MVP Blueprint"}
                  </p>
                  <div className="mt-1 flex items-center gap-3 text-xs text-slate-500">
                    {m.mvp_type && <span>Type: {m.mvp_type}</span>}
                    {m.created_at && (
                      <span>{new Date(m.created_at).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
                <div className="ml-4 flex items-center gap-3">
                  <span
                    className={`rounded-md px-2 py-0.5 text-xs font-medium ${
                      m.status === "generated"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : m.status === "pending"
                          ? "bg-amber-500/10 text-amber-400"
                          : "bg-red-500/10 text-red-400"
                    }`}
                  >
                    {m.status === "generated"
                      ? "Ready"
                      : m.status === "pending"
                        ? "Pending"
                        : "Failed"}
                  </span>
                  <svg
                    className="h-4 w-4 text-slate-600 group-hover:text-orange-400 transition-colors"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* ── Legal Documents ─────────────────────────────────── */}
      <h2 className="mb-4 mt-10 text-lg font-semibold text-slate-100">
        Legal Documents
      </h2>
      {legalDocuments.length === 0 ? (
        <div className="mb-8 rounded-xl border border-dashed border-white/10 bg-white/[0.01] px-6 py-8 text-center">
          <p className="text-sm text-slate-500">
            No legal documents yet. Generate NDAs, Founder Agreements, and more
            from any validated idea.
          </p>
        </div>
      ) : (
        <div className="mb-8 space-y-3">
          {legalDocuments.map((ld) => (
            <Link
              key={ld.id}
              href={`/legal/${ld.idea_id}`}
              className="group block rounded-xl border border-white/10 bg-white/[0.02] px-5 py-4 transition-all duration-200 hover:bg-white/[0.04] hover:-translate-y-0.5 hover:shadow-lg hover:shadow-emerald-500/5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
                    <svg
                      className="h-4.5 w-4.5 text-emerald-400"
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
                  <div>
                    <p className="text-sm font-medium text-slate-100">
                      {ld.document_type
                        .replace(/_/g, " ")
                        .replace(/\b\w/g, (c) => c.toUpperCase())}
                    </p>
                    <div className="mt-0.5 flex items-center gap-2">
                      {ld.jurisdiction && (
                        <span className="text-xs text-slate-500">
                          {ld.jurisdiction}
                        </span>
                      )}
                      <span
                        className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                          ld.status === "generated"
                            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                            : ld.status === "failed"
                              ? "border-red-500/30 bg-red-500/10 text-red-400"
                              : "border-amber-500/30 bg-amber-500/10 text-amber-400"
                        }`}
                      >
                        {ld.status}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {ld.created_at && (
                    <span className="text-xs text-slate-600">
                      {new Date(ld.created_at).toLocaleDateString()}
                    </span>
                  )}
                  <svg
                    className="h-4 w-4 text-slate-600 transition-transform group-hover:translate-x-0.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <RouteGuard>
      <DashboardContent />
    </RouteGuard>
  );
}
