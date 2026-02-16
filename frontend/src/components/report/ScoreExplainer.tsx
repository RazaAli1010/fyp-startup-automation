"use client";

import { useState } from "react";
import type { NormalizedSignals, ModuleScores } from "@/lib/types";
import { SCORING_EXPLANATIONS } from "@/lib/scoring_explanations";

type ModuleKey = keyof Omit<ModuleScores, "final_viability_score">;

interface ScoreExplainerProps {
  moduleKey: ModuleKey;
  score: number;
  signals: NormalizedSignals;
}

function scoreColor(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 45) return "text-amber-400";
  return "text-red-400";
}

function scoreBg(score: number): string {
  if (score >= 70) return "bg-emerald-400";
  if (score >= 45) return "bg-amber-400";
  return "bg-red-400";
}

function weightBarColor(weight: number): string {
  if (weight >= 0.5) return "bg-indigo-400";
  if (weight >= 0.3) return "bg-purple-400";
  return "bg-cyan-400";
}

export function ScoreExplainer({ moduleKey, score, signals }: ScoreExplainerProps) {
  const [open, setOpen] = useState(false);
  const explanation = SCORING_EXPLANATIONS[moduleKey];

  if (!explanation) return null;

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 transition-all duration-200 hover:border-slate-600/50">
      {/* Header — always visible */}
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-slate-200">
            {explanation.label}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            {explanation.description}
          </p>
        </div>
        <div className="ml-4 flex items-center gap-3">
          <p className={`text-2xl font-bold tabular-nums ${scoreColor(score)}`}>
            {score.toFixed(1)}
          </p>
          <svg
            className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Progress bar */}
      <div className="mx-4 mb-3 h-1.5 overflow-hidden rounded-full bg-slate-700/50">
        <div
          className={`h-full rounded-full transition-all duration-500 ${scoreBg(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>

      {/* Expandable detail panel */}
      {open && (
        <div
          className="border-t border-slate-700/30 px-4 pb-4 pt-3"
          style={{ animation: "tooltipFadeIn 200ms ease-out" }}
        >
          {/* Formula */}
          <div className="mb-4">
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-400">
              Formula
            </p>
            <div className="rounded-lg border border-slate-700/50 bg-slate-900/60 px-3 py-2">
              <code className="text-xs leading-relaxed text-slate-300">
                {explanation.formula}
              </code>
            </div>
          </div>

          {/* Input signals */}
          <div className="mb-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-indigo-400">
              Input Signals
            </p>
            <div className="space-y-2">
              {explanation.inputs.map((input) => {
                const value = signals[input.key];
                return (
                  <div key={input.key} className="flex items-center gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-400">
                          {input.label}
                          <span className="ml-1 text-slate-600">
                            (w: {input.weight})
                          </span>
                        </span>
                        <span className={`text-sm font-semibold tabular-nums ${scoreColor(value)}`}>
                          {value.toFixed(1)}
                        </span>
                      </div>
                      <div className="mt-1 h-1 overflow-hidden rounded-full bg-slate-700/50">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${weightBarColor(input.weight)}`}
                          style={{ width: `${value}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Interpretation */}
          <div className="rounded-lg border border-slate-700/30 bg-slate-900/40 px-3 py-2">
            <p className="text-xs leading-relaxed text-slate-400">
              <span className="font-semibold text-slate-300">Interpretation: </span>
              {explanation.interpret(score)}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
