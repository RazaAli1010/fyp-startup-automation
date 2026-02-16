interface SectionWrapperProps {
  children: React.ReactNode;
  className?: string;
  id?: string;
}

export function SectionWrapper({ children, className = "", id }: SectionWrapperProps) {
  return (
    <section id={id} className={`relative px-6 py-20 sm:py-28 ${className}`}>
      <div className="mx-auto max-w-6xl">{children}</div>
    </section>
  );
}

interface SectionHeaderProps {
  badge?: string;
  title: string;
  description?: string;
  gradient?: boolean;
}

export function SectionHeader({ badge, title, description, gradient = false }: SectionHeaderProps) {
  return (
    <div className="mb-14 text-center">
      {badge && (
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-4 py-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
            {badge}
          </span>
        </div>
      )}
      <h2
        className={`text-3xl font-bold tracking-tight sm:text-4xl ${
          gradient ? "gradient-text" : "text-slate-100"
        }`}
      >
        {title}
      </h2>
      {description && (
        <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-slate-400">
          {description}
        </p>
      )}
    </div>
  );
}
