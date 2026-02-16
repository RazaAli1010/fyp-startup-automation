"use client";

import { useState, useEffect } from "react";

const LOADING_MESSAGES = [
  "Collecting market signals\u2026",
  "Analyzing user pain points\u2026",
  "Evaluating competition landscape\u2026",
  "Assessing market timing\u2026",
  "Computing viability score\u2026",
  "Finalizing insights\u2026",
];

interface EvaluationLoaderProps {
  isLoading: boolean;
}

export function EvaluationLoader({ isLoading }: EvaluationLoaderProps) {
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    if (!isLoading) return;

    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % LOADING_MESSAGES.length);
    }, 1800);

    return () => clearInterval(interval);
  }, [isLoading]);

  if (!isLoading) return null;

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-6">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0c1425] p-10 text-center">
        {/* Unified spinner — matches Spinner component */}
        <div className="relative mx-auto mb-8 h-16 w-16">
          <div
            className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-indigo-500 border-r-purple-500"
            style={{ animationDuration: "1.2s" }}
          />
          <div
            className="absolute inset-2 animate-spin rounded-full border-2 border-transparent border-b-cyan-400 border-l-indigo-400"
            style={{ animationDuration: "1.8s", animationDirection: "reverse" }}
          />
          <div className="absolute inset-[30%] rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 shadow-lg shadow-indigo-500/30 animate-pulse" />
        </div>

        {/* Status badge */}
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-3 py-1">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
            Analysis in Progress
          </span>
        </div>

        {/* Rotating message */}
        <div className="h-6">
          <p
            key={messageIndex}
            className="text-sm font-medium text-slate-300"
            style={{ animation: "tooltipFadeIn 300ms ease-out" }}
          >
            {LOADING_MESSAGES[messageIndex]}
          </p>
        </div>

        {/* Subtitle */}
        <p className="mt-3 text-xs text-slate-500">
          AI agents are collecting and scoring real market data.
        </p>

        {/* Shimmer bar */}
        <div className="mx-auto mt-6 h-1 w-48 overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full w-1/3 rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400"
            style={{
              animation: "shimmer 1.5s ease-in-out infinite",
            }}
          />
        </div>
      </div>
    </div>
  );
}
