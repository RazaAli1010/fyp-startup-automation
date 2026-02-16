"use client";

import { useState, useRef, useEffect, useCallback } from "react";

export interface TooltipContent {
  description: string;
  impact: string;
}

interface InfoTooltipProps {
  content: TooltipContent;
}

export function InfoTooltip({ content }: InfoTooltipProps) {
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState<"bottom" | "top">("bottom");
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const updatePosition = useCallback(() => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    setPosition(spaceBelow < 160 ? "top" : "bottom");
  }, []);

  useEffect(() => {
    if (visible) {
      updatePosition();
    }
  }, [visible, updatePosition]);

  return (
    <span className="relative inline-flex">
      <button
        ref={triggerRef}
        type="button"
        className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-600/50 bg-slate-800/80 text-[10px] leading-none text-slate-400 transition-all duration-200 hover:border-indigo-500/50 hover:text-indigo-300 hover:shadow-sm hover:shadow-indigo-500/20 focus:outline-none"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        onClick={(e) => {
          e.preventDefault();
          setVisible((v) => !v);
        }}
        aria-label="Field information"
      >
        i
      </button>

      {visible && (
        <div
          ref={tooltipRef}
          role="tooltip"
          className={`
            absolute left-1/2 z-50 w-64 -translate-x-1/2
            rounded-xl border border-indigo-500/20 bg-[#0c1425] p-3.5
            shadow-xl shadow-indigo-500/5
            animate-in fade-in duration-150
            ${position === "bottom" ? "top-full mt-2" : "bottom-full mb-2"}
          `}
          style={{
            animation: "tooltipFadeIn 150ms ease-out",
          }}
        >
          <p className="text-xs leading-relaxed text-slate-300">
            {content.description}
          </p>
          <p className="mt-2 text-[11px] italic leading-relaxed text-indigo-400/80">
            {content.impact}
          </p>

          {/* Arrow */}
          <div
            className={`
              absolute left-1/2 -translate-x-1/2 h-2 w-2 rotate-45
              border-indigo-500/20 bg-[#0c1425]
              ${position === "bottom" ? "-top-1 border-l border-t" : "-bottom-1 border-b border-r"}
            `}
          />
        </div>
      )}
    </span>
  );
}
