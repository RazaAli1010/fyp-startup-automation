import Link from "next/link";
import { ButtonHTMLAttributes } from "react";

interface GradientButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  href?: string;
  size?: "md" | "lg";
}

export function GradientButton({
  href,
  size = "md",
  children,
  className = "",
  ...props
}: GradientButtonProps) {
  const sizeClasses =
    size === "lg" ? "px-8 py-3.5 text-base" : "px-6 py-2.5 text-sm";

  const classes = `
    inline-flex items-center justify-center gap-2
    rounded-xl font-semibold text-white
    bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400
    shadow-lg shadow-indigo-500/25
    transition-all duration-300
    hover:shadow-xl hover:shadow-indigo-500/40 hover:brightness-110 hover:scale-[1.02]
    active:scale-[0.98]
    animate-glow-pulse
    ${sizeClasses}
    ${className}
  `;

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }

  return (
    <button className={classes} {...props}>
      {children}
    </button>
  );
}
