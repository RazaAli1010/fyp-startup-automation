"use client";

import { useEffect, useCallback } from "react";
import { Button } from "./button";

interface GatingAction {
  label: string;
  href?: string;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "ghost";
}

interface GatingModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  message: string;
  actions: GatingAction[];
  icon?: React.ReactNode;
}

export function GatingModal({
  open,
  onClose,
  title,
  message,
  actions,
  icon,
}: GatingModalProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 mx-4 w-full max-w-md animate-in zoom-in-95 fade-in duration-200">
        <div className="rounded-2xl border border-white/10 bg-[#0f172a] p-8 shadow-2xl shadow-black/40">
          {/* Icon */}
          {icon && (
            <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-amber-500/20 to-orange-500/20">
              {icon}
            </div>
          )}

          {/* Title */}
          <h3 className="mb-2 text-center text-lg font-bold text-slate-100">
            {title}
          </h3>

          {/* Message */}
          <p className="mb-6 text-center text-sm leading-relaxed text-slate-400">
            {message}
          </p>

          {/* Actions */}
          <div className="flex flex-col gap-2.5">
            {actions.map((action, i) => (
              <Button
                key={i}
                variant={action.variant ?? (i === 0 ? "primary" : "secondary")}
                fullWidth
                onClick={() => {
                  if (action.onClick) action.onClick();
                  if (action.href) window.location.href = action.href;
                }}
              >
                {action.label}
              </Button>
            ))}
            <Button variant="ghost" fullWidth onClick={onClose}>
              Dismiss
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
