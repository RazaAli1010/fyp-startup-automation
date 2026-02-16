import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
}

const variantStyles: Record<Variant, string> = {
  primary:
    "bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 text-white border border-white/10 shadow-lg shadow-indigo-500/25 hover:shadow-xl hover:shadow-indigo-500/40 hover:brightness-110 hover:scale-[1.02] hover:-translate-y-0.5 active:scale-[0.98] active:translate-y-0",
  secondary:
    "bg-white/5 text-slate-100 hover:bg-white/10 border border-white/10 hover:border-white/20 hover:-translate-y-0.5 hover:shadow-md hover:shadow-white/5 active:translate-y-0",
  ghost:
    "bg-transparent text-slate-400 hover:text-slate-100 hover:bg-white/5 hover:-translate-y-px",
  danger:
    "bg-gradient-to-r from-red-500 to-rose-600 text-white border border-red-500/20 shadow-lg shadow-red-500/20 hover:shadow-red-500/40 hover:brightness-110",
};

const sizeStyles: Record<Size, string> = {
  sm: "px-3.5 py-1.5 text-sm",
  md: "px-5 py-2.5 text-sm",
  lg: "px-7 py-3 text-base",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading,
      fullWidth,
      className = "",
      children,
      disabled,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`
          inline-flex items-center justify-center gap-2
          rounded-xl font-semibold
          transition-all duration-200 ease-out
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#020617]
          disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${fullWidth ? "w-full" : ""}
          ${className}
        `}
        {...props}
      >
        {loading && (
          <svg
            className="h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";

export { Button };
export type { ButtonProps };
