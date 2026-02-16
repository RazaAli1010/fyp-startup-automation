import { HTMLAttributes, forwardRef } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ hover = false, className = "", children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`
          rounded-xl border border-slate-800/60 bg-[#0f172a]/80 p-6
          ${hover ? "transition-all duration-200 hover:border-indigo-500/20 hover:bg-[#131c31]" : ""}
          ${className}
        `}
        {...props}
      >
        {children}
      </div>
    );
  },
);

Card.displayName = "Card";

function CardHeader({
  className = "",
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`mb-4 ${className}`} {...props}>
      {children}
    </div>
  );
}

function CardTitle({
  className = "",
  children,
  ...props
}: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={`text-lg font-semibold text-slate-100 ${className}`}
      {...props}
    >
      {children}
    </h3>
  );
}

function CardDescription({
  className = "",
  children,
  ...props
}: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={`text-sm text-slate-400 ${className}`} {...props}>
      {children}
    </p>
  );
}

function CardContent({
  className = "",
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={className} {...props}>
      {children}
    </div>
  );
}

export { Card, CardHeader, CardTitle, CardDescription, CardContent };
