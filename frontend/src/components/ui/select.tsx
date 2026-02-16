import { SelectHTMLAttributes, forwardRef } from "react";
import { InfoTooltip, type TooltipContent } from "./info-tooltip";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
  tooltip?: TooltipContent;
  options: { value: string; label: string }[];
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, tooltip, options, className = "", id, ...props }, ref) => {
    const selectId = id ?? label.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="space-y-1.5">
        <label
          htmlFor={selectId}
          className="flex items-center gap-1.5 text-sm font-medium text-slate-300"
        >
          {label}
          {tooltip && <InfoTooltip content={tooltip} />}
        </label>
        <select
          ref={ref}
          id={selectId}
          className={`
            w-full rounded-lg border bg-[#0f172a]/80 px-3.5 py-2.5
            text-sm text-slate-100
            transition-colors duration-150
            focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:ring-offset-1 focus:ring-offset-[#020617]
            ${error ? "border-red-500/50" : "border-slate-700/60 hover:border-indigo-500/30"}
            ${className}
          `}
          {...props}
        >
          <option value="" className="bg-[#0f172a] text-slate-500">
            Select...
          </option>
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#0f172a]">
              {opt.label}
            </option>
          ))}
        </select>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    );
  },
);

Select.displayName = "Select";

export { Select };
export type { SelectProps };
