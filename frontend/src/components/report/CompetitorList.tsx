"use client";

interface CompetitorListProps {
  competitors: string[];
}

function normalizeCompetitorName(name: string): string | null {
  const trimmed = name.trim();
  if (!trimmed) return null;
  const words = trimmed.split(/\s+/).slice(0, 2);
  const result = words.join(" ");
  return result.length >= 2 ? result : null;
}

export function CompetitorList({ competitors }: CompetitorListProps) {
  if (!competitors || competitors.length === 0) {
    return (
      <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 px-5 py-4 text-center">
        <p className="text-sm text-slate-500">
          No strong competitors detected based on current data.
        </p>
      </div>
    );
  }

  const seen = new Set<string>();
  const shown: string[] = [];
  for (const raw of competitors) {
    const name = normalizeCompetitorName(raw);
    if (name && !seen.has(name.toLowerCase())) {
      seen.add(name.toLowerCase());
      shown.push(name);
      if (shown.length >= 5) break;
    }
  }

  if (shown.length === 0) {
    return (
      <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 px-5 py-4 text-center">
        <p className="text-sm text-slate-500">
          No strong competitors detected based on current data.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {shown.map((name) => (
        <span
          key={name}
          className="inline-flex items-center rounded-full border border-indigo-500/20 bg-indigo-500/10 px-3 py-1 text-sm font-medium text-indigo-300 transition-colors hover:border-indigo-500/40 hover:bg-indigo-500/20"
        >
          {name}
        </span>
      ))}
    </div>
  );
}
