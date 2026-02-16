"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { generatePitchDeck, getPitchDeckByIdea, ApiError } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { RouteGuard } from "@/components/auth/route-guard";
import { BackButton } from "@/components/ui/back-button";
import type { PitchDeckRecord } from "@/lib/types";

type Status = "idle" | "loading" | "generating" | "success" | "error";

function PitchDeckContent() {
  const params = useParams();
  const ideaId = params.id as string;

  const [status, setStatus] = useState<Status>("loading");
  const [deck, setDeck] = useState<PitchDeckRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Load existing deck on mount
  useEffect(() => {
    if (!ideaId) {
      console.error("[DECK] No ideaId — cannot load");
      setError("Missing idea ID");
      setStatus("error");
      return;
    }

    let active = true;

    async function loadDeck() {
      console.log(`[DECK] Loading pitch deck for idea: ${ideaId}`);
      setStatus("loading");
      setError(null);
      try {
        const data = await getPitchDeckByIdea(ideaId);
        console.log("[DECK] Loaded existing deck:", data.id, data.status);
        if (active) {
          setDeck(data);
          setStatus(data.status === "completed" ? "success" : "idle");
        }
      } catch (err: unknown) {
        if (active) {
          if (err instanceof ApiError && err.status === 404) {
            console.log(
              "[DECK] No existing pitch deck — showing generate button",
            );
            setStatus("idle");
          } else {
            console.error("[DECK] Failed to load pitch deck:", err);
            setError(
              err instanceof Error ? err.message : "Failed to load deck",
            );
            setStatus("error");
          }
        }
      }
    }

    loadDeck();
    return () => {
      active = false;
    };
  }, [ideaId]);

  const handleGenerate = useCallback(async () => {
    console.log(`[DECK] Generate pitch deck clicked → idea_id: ${ideaId}`);
    setStatus("generating");
    setError(null);
    try {
      const data = await generatePitchDeck(ideaId);
      console.log("[DECK] Pitch deck generated:", data.id, data.status);
      setDeck(data);
      setStatus("success");
    } catch (err: unknown) {
      console.error("[DECK] Pitch deck generation failed:", err);
      const message =
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Pitch deck generation failed.";
      setError(message);
      setStatus("error");
    }
  }, [ideaId]);

  const handleCopyLink = useCallback(async () => {
    if (!deck?.view_url) return;
    try {
      await navigator.clipboard.writeText(deck.view_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.error("[DECK] Failed to copy link");
    }
  }, [deck]);

  // ── Loading state ──────────────────────────────────────────
  if (status === "loading") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
        <Spinner size="lg" label="Loading pitch deck..." />
      </div>
    );
  }

  // ── Generating state ───────────────────────────────────────
  if (status === "generating") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
        <Spinner
          size="lg"
          label="Generating your pitch deck..."
          sublabel="Running validation pipeline and building slides via Alai"
        />
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────
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

  // ── Idle state (no deck yet) ───────────────────────────────
  if (status === "idle" || !deck || deck.status !== "completed") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-6">
        <Card className="max-w-md text-center">
          <CardContent className="py-10">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-500/20">
              <svg
                className="h-8 w-8 text-indigo-400"
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
            <h2 className="mb-2 text-lg font-semibold text-slate-100">
              Generate Pitch Deck
            </h2>
            <p className="mb-6 text-sm text-slate-400">
              Create an investor-ready pitch deck based on your validated idea.
              All content is derived from real market signals.
            </p>
            <Button onClick={handleGenerate} size="lg">
              Generate Pitch Deck
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Success — completed deck with Alai links ───────────────
  const hasLinks = deck.view_url && deck.pdf_url;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <BackButton fallback="/dashboard" />

      {/* Header */}
      <div className="mb-6 mt-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-purple-400">
              Pitch Deck
            </p>
            <h1 className="text-2xl font-bold tracking-tight text-slate-50">
              {deck.title}
            </h1>
            {deck.created_at && (
              <p className="mt-1 text-sm text-slate-500">
                Created {new Date(deck.created_at).toLocaleDateString()}
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
          </div>
        </div>

        {/* Status badge + Provider */}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Completed
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-xs font-semibold text-purple-300">
            <span className="h-1.5 w-1.5 rounded-full bg-purple-400" />
            Generated using Alai AI
          </span>
        </div>
        <div className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-2.5">
          <p className="text-xs text-amber-400/80">
            This pitch deck is auto-generated based on validated market signals.
            No speculative metrics or invented claims are included.
          </p>
        </div>
      </div>

      {/* Presentation view + actions */}
      {hasLinks ? (
        <div className="space-y-6">
          <div className="overflow-hidden rounded-xl border border-slate-800/60 bg-[#0f172a]/80">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-600 px-6 py-4">
              <h2 className="text-lg font-bold text-white">
                Your Presentation is Ready
              </h2>
              <p className="text-sm text-white/70">
                View, share, or download your investor-grade pitch deck
              </p>
            </div>
            <div className="p-6">
              {/* Embed the presentation */}
              <div className="mb-6 aspect-video w-full overflow-hidden rounded-lg border border-slate-700/50">
                <iframe
                  src={deck.view_url!}
                  className="h-full w-full"
                  title="Pitch Deck Presentation"
                  allowFullScreen
                />
              </div>

              {/* Action buttons */}
              <div className="flex flex-wrap gap-3">
                <a
                  href={deck.view_url!}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all hover:shadow-xl hover:shadow-indigo-500/40 hover:brightness-110 hover:scale-[1.02] active:scale-[0.98]"
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
                      d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
                    />
                  </svg>
                  Open Presentation
                </a>
                <a
                  href={deck.pdf_url!}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold text-slate-100 transition-all hover:bg-white/10 hover:border-white/20"
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
                      d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                    />
                  </svg>
                  Download PDF
                </a>
                <Link
                  href={`/chat/${ideaId}`}
                  className="inline-flex items-center gap-2 rounded-xl border border-indigo-500/20 bg-indigo-500/10 px-5 py-2.5 text-sm font-semibold text-indigo-300 transition-all hover:bg-indigo-500/20 hover:border-indigo-500/30"
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
                      d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
                    />
                  </svg>
                  AI Co-Founder
                </Link>
                <button
                  onClick={handleCopyLink}
                  className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold text-slate-100 transition-all hover:bg-white/10 hover:border-white/20"
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
                      d="M8.25 7.5V6.108c0-1.135.845-2.098 1.976-2.192.373-.03.748-.057 1.123-.08M15.75 18H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08M15.75 18.75v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5A3.375 3.375 0 006.375 7.5H5.25m11.9-3.664A2.251 2.251 0 0015 2.25h-1.5a2.251 2.251 0 00-2.15 1.586m5.8 0c.065.21.1.433.1.664v.75h-6V4.5c0-.231.035-.454.1-.664M6.75 7.5H4.875c-.621 0-1.125.504-1.125 1.125v12c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V16.5a9 9 0 00-9-9z"
                    />
                  </svg>
                  {copied ? "Copied!" : "Copy Share Link"}
                </button>
              </div>

              {/* Generation metadata */}
              {deck.generation_id && (
                <p className="mt-4 text-xs text-slate-600">
                  Generation ID: {deck.generation_id}
                </p>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-8 text-center">
          <p className="text-sm text-amber-400">
            Deck was generated but links are not available. Try regenerating.
          </p>
          <Button
            variant="secondary"
            size="sm"
            className="mt-4"
            onClick={handleGenerate}
          >
            Regenerate
          </Button>
        </div>
      )}
    </div>
  );
}

export default function PitchDeckPage() {
  return (
    <RouteGuard>
      <PitchDeckContent />
    </RouteGuard>
  );
}
