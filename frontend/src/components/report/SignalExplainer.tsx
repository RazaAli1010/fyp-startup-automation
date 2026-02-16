"use client";

import { useState } from "react";
import type { NormalizationExplanation } from "@/lib/types";
import { NORMALIZATION_FALLBACKS } from "@/lib/normalization_explanations";

interface SignalExplainerProps {
  signalKey: string;
  value: number;
  explanation?: NormalizationExplanation;
}

function scoreColor(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 45) return "text-amber-400";
  return "text-red-400";
}

function barColor(score: number): string {
  if (score >= 70) return "bg-emerald-400";
  if (score >= 45) return "bg-amber-400";
  return "bg-red-400";
}

export function SignalExplainer({
  signalKey,
  value,
  explanation,
}: SignalExplainerProps) {
  const [open, setOpen] = useState(false);

  const fallback =
    NORMALIZATION_FALLBACKS[
      signalKey as keyof typeof NORMALIZATION_FALLBACKS
    ];

  const label = fallback?.label ?? signalKey.replace(/_/g, " ");
  const formula = explanation?.formula ?? fallback?.formula ?? "—";
  const description =
    explanation?.description ?? fallback?.description ?? "—";
  const rawValue = explanation?.raw_value;

  return (
    <div className="rounded-lg border border-slate-700/40 bg-slate-800/30 transition-all duration-150 hover:border-slate-600/50">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left"
      >
        <div className="min-w-0 flex-1">
          <p className="text-xs capitalize text-slate-400">{label}</p>
        </div>
        <p
          className={`text-lg font-semibold tabular-nums ${scoreColor(value)}`}
        >
          {value.toFixed(1)}
        </p>
        <svg
          className={`h-3.5 w-3.5 flex-shrink-0 text-slate-500 transition-transform duration-150 ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Progress bar */}
      <div className="mx-3 mb-2 h-1 overflow-hidden rounded-full bg-slate-700/40">
        <div
          className={`h-full rounded-full transition-all duration-400 ${barColor(value)}`}
          style={{ width: `${value}%` }}
        />
      </div>

      {/* Expandable detail */}
      {open && (
        <div
          className="border-t border-slate-700/30 px-3 pb-3 pt-2.5"
          style={{ animation: "tooltipFadeIn 150ms ease-out" }}
        >
          {/* Raw value */}
          {rawValue !== undefined && (
            <div className="mb-2 flex items-center gap-2">
              <span className="text-xs font-semibold text-indigo-400">
                Raw Value
              </span>
              <span className="rounded bg-slate-900/60 px-1.5 py-0.5 font-mono text-xs text-slate-300">
                {rawValue}
              </span>
            </div>
          )}

          {/* Formula */}
          <div className="mb-2">
            <p className="mb-1 text-xs font-semibold text-indigo-400">
              Formula
            </p>
            <div className="rounded border border-slate-700/40 bg-slate-900/50 px-2.5 py-1.5">
              <code className="text-xs leading-relaxed text-slate-300">
                {formula}
              </code>
            </div>
          </div>

          {/* Description */}
          <p className="text-xs leading-relaxed text-slate-500">
            {description}
          </p>
        </div>
      )}
    </div>
  );
}
