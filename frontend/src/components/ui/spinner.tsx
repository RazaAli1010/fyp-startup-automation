"use client";

interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  sublabel?: string;
}

const sizeMap = {
  sm: "h-5 w-5",
  md: "h-8 w-8",
  lg: "h-12 w-12",
};

export function Spinner({ size = "md", label, sublabel }: SpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className={`relative ${sizeMap[size]}`}>
        {/* Outer ring */}
        <div
          className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-indigo-500 border-r-purple-500"
          style={{ animationDuration: "1.2s" }}
        />
        {/* Inner ring */}
        <div
          className="absolute inset-1 animate-spin rounded-full border-2 border-transparent border-b-cyan-400 border-l-indigo-400"
          style={{ animationDuration: "1.8s", animationDirection: "reverse" }}
        />
        {/* Center glow */}
        <div className="absolute inset-[30%] rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 shadow-lg shadow-indigo-500/30 animate-pulse" />
      </div>
      {label && (
        <p className="text-sm font-medium text-slate-200">{label}</p>
      )}
      {sublabel && (
        <p className="text-xs text-slate-500">{sublabel}</p>
      )}
    </div>
  );
}
