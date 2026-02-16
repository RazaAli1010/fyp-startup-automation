import { InputHTMLAttributes, forwardRef } from "react";
import { InfoTooltip, type TooltipContent } from "./info-tooltip";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  tooltip?: TooltipContent;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, tooltip, className = "", id, ...props }, ref) => {
    const inputId = id ?? label.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="space-y-1.5">
        <label
          htmlFor={inputId}
          className="flex items-center gap-1.5 text-sm font-medium text-slate-300"
        >
          {label}
          {tooltip && <InfoTooltip content={tooltip} />}
        </label>
        <input
          ref={ref}
          id={inputId}
          className={`
            w-full rounded-lg border bg-[#0f172a]/80 px-3.5 py-2.5
            text-sm text-slate-100 placeholder-slate-500
            transition-colors duration-150
            focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:ring-offset-1 focus:ring-offset-[#020617]
            ${error ? "border-red-500/50" : "border-slate-700/60 hover:border-indigo-500/30"}
            ${className}
          `}
          {...props}
        />
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    );
  },
);

Input.displayName = "Input";

export { Input };
export type { InputProps };
