import { InputHTMLAttributes, forwardRef } from "react";
import { InfoTooltip, type TooltipContent } from "./info-tooltip";

interface SliderProps extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "type"
> {
  label: string;
  error?: string;
  tooltip?: TooltipContent;
  displayValue?: string;
}

const Slider = forwardRef<HTMLInputElement, SliderProps>(
  (
    { label, error, tooltip, displayValue, className = "", id, ...props },
    ref,
  ) => {
    const sliderId = id ?? label.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label
            htmlFor={sliderId}
            className="flex items-center gap-1.5 text-sm font-medium text-slate-300"
          >
            {label}
            {tooltip && <InfoTooltip content={tooltip} />}
          </label>
          {displayValue !== undefined && (
            <span className="text-sm font-mono text-indigo-300">
              {displayValue}
            </span>
          )}
        </div>
        <input
          ref={ref}
          id={sliderId}
          type="range"
          className={`
            w-full h-1.5 rounded-full appearance-none cursor-pointer
            bg-slate-700 accent-indigo-500
            ${className}
          `}
          {...props}
        />
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    );
  },
);

Slider.displayName = "Slider";

export { Slider };
export type { SliderProps };
