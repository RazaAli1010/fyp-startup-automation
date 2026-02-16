import Link from "next/link";
import { Button } from "@/components/ui/button";
import { FeatureCard } from "@/components/ui/feature-card";
import { SectionWrapper, SectionHeader } from "@/components/ui/section-wrapper";

/* ================================================================
 *  SVG Icons (inline, no external deps)
 * ================================================================ */

function IconPain() {
  return (
    <svg
      className="h-6 w-6 text-indigo-400"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
      />
    </svg>
  );
}

function IconTrend() {
  return (
    <svg
      className="h-6 w-6 text-cyan-400"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941"
      />
    </svg>
  );
}

function IconShield() {
  return (
    <svg
      className="h-6 w-6 text-purple-400"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
      />
    </svg>
  );
}

function IconGear() {
  return (
    <svg
      className="h-6 w-6 text-indigo-400"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M11.42 15.17l-5.1-3.04a1.5 1.5 0 01-.55-2.05l.88-1.52a1.5 1.5 0 012.05-.55l5.1 3.04m-2.38 4.12l5.1 3.04a1.5 1.5 0 002.05-.55l.88-1.52a1.5 1.5 0 00-.55-2.05l-5.1-3.04m-7.14 7.14a3 3 0 104.24-4.24 3 3 0 00-4.24 4.24z"
      />
    </svg>
  );
}

function IconChart() {
  return (
    <svg
      className="h-6 w-6 text-cyan-400"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
      />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M13 7l5 5m0 0l-5 5m5-5H6"
      />
    </svg>
  );
}

/* ================================================================
 *  Data
 * ================================================================ */

const FEATURES = [
  {
    icon: <IconPain />,
    title: "Problem Intensity",
    description:
      "Detects real user pain from Tavily and SerpAPI signals. Measures search intent, complaint frequency, and unmet needs.",
  },
  {
    icon: <IconTrend />,
    title: "Market Timing",
    description:
      "Analyzes long-term demand growth and momentum using Google Trends data. Identifies whether the market is rising, peaking, or declining.",
  },
  {
    icon: <IconShield />,
    title: "Competition Pressure",
    description:
      "Measures market saturation and differentiation difficulty. Discovers competitors automatically and scores feature overlap.",
  },
  {
    icon: <IconGear />,
    title: "Execution Feasibility",
    description:
      "Evaluates technical complexity and regulatory barriers. Scores how difficult it is to build and launch your product.",
  },
  {
    icon: <IconChart />,
    title: "Market Potential",
    description:
      "Estimates realistic opportunity size by combining demand strength with growth trajectory. No inflated TAM guesses.",
  },
];

const PIPELINE_STEPS = [
  {
    step: "01",
    title: "Enter Details",
    desc: "Describe your startup idea with structured inputs",
  },
  {
    step: "02",
    title: "Agents Collect",
    desc: "AI agents gather Tavily, SerpAPI, Trends, and competitor data",
  },
  {
    step: "03",
    title: "Normalize",
    desc: "Raw signals are normalized to a 0–100 scale",
  },
  {
    step: "04",
    title: "Score",
    desc: "Deterministic scoring engine computes module scores",
  },
  {
    step: "05",
    title: "Verdict",
    desc: "Clear viability verdict with explainable insights",
  },
];

/* ================================================================
 *  Page
 * ================================================================ */

export default function Home() {
  return (
    <div className="relative overflow-hidden">
      {/* ── Background orbs ─────────────────────────────────── */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="animate-float absolute -top-32 left-1/4 h-[500px] w-[500px] rounded-full bg-indigo-600/[0.07] blur-[120px]" />
        <div className="animate-float-delayed absolute top-1/3 right-1/4 h-[400px] w-[400px] rounded-full bg-purple-600/[0.06] blur-[100px]" />
        <div className="animate-float absolute bottom-0 left-1/2 h-[350px] w-[350px] -translate-x-1/2 rounded-full bg-cyan-500/[0.05] blur-[100px]" />
      </div>

      {/* ══════════════════════════════════════════════════════
       *  HERO SECTION
       * ══════════════════════════════════════════════════════ */}
      <section className="relative flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-6 text-center">
        <div className="mx-auto max-w-3xl">
          {/* Badge */}
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-4 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
              Multi-Agent AI Validation Engine
            </span>
          </div>

          {/* Headline */}
          <h1 className="mb-6 text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
            <span className="text-slate-100">Validate Startup Ideas with</span>
            <br />
            <span className="gradient-text">Data, Not Guesswork</span>
          </h1>

          {/* Subheading */}
          <p className="mx-auto mb-10 max-w-xl text-lg leading-relaxed text-slate-400">
            StartBot deploys deterministic AI agents to collect real market
            signals, normalize them, and produce an investor-grade viability
            score — fully explainable, fully auditable.
          </p>

          {/* CTA */}
          <Link href="/ideas/new">
            <Button size="lg">
              Validate My Idea
              <ArrowIcon />
            </Button>
          </Link>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 flex flex-col items-center gap-2">
          <span className="text-xs text-slate-500">Scroll to explore</span>
          <div className="h-6 w-3.5 rounded-full border border-slate-700 p-0.5">
            <div className="h-1.5 w-full rounded-full bg-indigo-400 animate-bounce" />
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════
       *  VALIDATION ENGINE SECTION
       * ══════════════════════════════════════════════════════ */}
      <SectionWrapper id="engine">
        <SectionHeader
          badge="Validation Engine"
          title="Five Dimensions of Startup Viability"
          description="Each idea is evaluated across five critical dimensions using real data from Tavily, SerpAPI, Google Trends, and automated competitor discovery."
          gradient
        />

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feat) => (
            <FeatureCard
              key={feat.title}
              icon={feat.icon}
              title={feat.title}
              description={feat.description}
            />
          ))}
        </div>
      </SectionWrapper>

      {/* ══════════════════════════════════════════════════════
       *  AGENT TOOLS
       * ══════════════════════════════════════════════════════ */}
      <SectionWrapper id="tools">
        <SectionHeader
          badge="Agent Tools"
          title="Beyond Validation — Build With Confidence"
          description="Once your idea is validated, unlock powerful AI-driven tools to research markets, craft investor-ready decks, and plan your MVP."
          gradient
        />

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {/* Market Research */}
          <div className="gradient-border group relative rounded-2xl bg-[#0f172a] p-7 transition-all duration-300 hover:bg-[#131c31] hover:scale-[1.02] hover:-translate-y-1">
            <div className="mb-5 flex h-13 w-13 items-center justify-center rounded-xl bg-gradient-to-br from-teal-500/20 to-cyan-500/20 transition-transform duration-300 group-hover:scale-110">
              <svg
                className="h-6 w-6 text-teal-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
                />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold text-slate-100">
              Market Research
            </h3>
            <p className="mb-5 text-sm leading-relaxed text-slate-400">
              Estimate TAM, SAM, SOM, discover competitors, and measure demand
              strength with real market data.
            </p>
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-teal-400">
              <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />
              Requires: Validated Idea
            </span>
          </div>

          {/* Pitch Deck */}
          <div className="gradient-border group relative rounded-2xl bg-[#0f172a] p-7 transition-all duration-300 hover:bg-[#131c31] hover:scale-[1.02] hover:-translate-y-1">
            <div className="mb-5 flex h-13 w-13 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 transition-transform duration-300 group-hover:scale-110">
              <svg
                className="h-6 w-6 text-purple-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5"
                />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold text-slate-100">
              Pitch Deck Generator
            </h3>
            <p className="mb-5 text-sm leading-relaxed text-slate-400">
              Generate an investor-ready pitch deck powered by your evaluation
              data and market signals.
            </p>
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-purple-400">
              <span className="h-1.5 w-1.5 rounded-full bg-purple-400" />
              Requires: Validated Idea
            </span>
          </div>

          {/* MVP Generator */}
          <div className="gradient-border group relative rounded-2xl bg-[#0f172a] p-7 transition-all duration-300 hover:bg-[#131c31] hover:scale-[1.02] hover:-translate-y-1">
            <div className="mb-5 flex h-13 w-13 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500/20 to-amber-500/20 transition-transform duration-300 group-hover:scale-110">
              <svg
                className="h-6 w-6 text-orange-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M11.42 15.17l-5.59-5.59a2.002 2.002 0 010-2.83l.81-.81a2.002 2.002 0 012.83 0L12 8.47l2.53-2.53a2.002 2.002 0 012.83 0l.81.81a2.002 2.002 0 010 2.83l-5.59 5.59a.996.996 0 01-1.41 0z"
                />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold text-slate-100">
              MVP Blueprint
            </h3>
            <p className="mb-5 text-sm leading-relaxed text-slate-400">
              Get a structured MVP plan with features, tech stack, build phases,
              and validation metrics.
            </p>
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-orange-400">
              <span className="h-1.5 w-1.5 rounded-full bg-orange-400" />
              Requires: Validated Idea + Market Research
            </span>
          </div>

          {/* Legal Documents */}
          <div className="gradient-border group relative rounded-2xl bg-[#0f172a] p-7 transition-all duration-300 hover:bg-[#131c31] hover:scale-[1.02] hover:-translate-y-1">
            <div className="mb-5 flex h-13 w-13 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-green-500/20 transition-transform duration-300 group-hover:scale-110">
              <svg
                className="h-6 w-6 text-emerald-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold text-slate-100">
              Legal Documents
            </h3>
            <p className="mb-5 text-sm leading-relaxed text-slate-400">
              Generate jurisdiction-aware NDAs, Founder Agreements, Privacy
              Policies, and Terms of Service.
            </p>
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Requires: Validated Idea
            </span>
          </div>
        </div>

        {/* CTA to dashboard */}
        <div className="mt-10 text-center">
          <Link href="/dashboard">
            <Button variant="secondary" size="lg">
              Go to Dashboard
              <ArrowIcon />
            </Button>
          </Link>
        </div>
      </SectionWrapper>

      {/* ══════════════════════════════════════════════════════
       *  WHY STARTBOT IS DIFFERENT
       * ══════════════════════════════════════════════════════ */}
      <SectionWrapper id="why">
        <SectionHeader
          badge="Why StartBot"
          title="Not Another AI Chatbot"
          description="Most validation tools give you LLM-generated opinions. StartBot gives you deterministic, data-backed scores."
        />

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* The Old Way */}
          <div className="rounded-2xl border border-red-500/10 bg-red-500/[0.03] p-8">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full bg-red-500/10 px-3 py-1">
              <span className="text-xs font-semibold text-red-400">
                The Old Way
              </span>
            </div>
            <ul className="space-y-3">
              {[
                "LLM guesswork with hallucinated data",
                "One-line TAM calculations",
                "Generic advice anyone could give",
                "No real market signals",
                "Opaque scoring with no explanation",
              ].map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-3 text-sm text-slate-400"
                >
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-500/10 text-xs text-red-400">
                    ✕
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* The StartBot Way */}
          <div className="gradient-border rounded-2xl bg-[#0f172a] p-8">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full bg-indigo-500/10 px-3 py-1">
              <span className="text-xs font-semibold text-indigo-300">
                The StartBot Way
              </span>
            </div>
            <ul className="space-y-3">
              {[
                "Deterministic scoring — same input, same output",
                "Multi-agent data collection from real sources",
                "Explainable results with transparent formulas",
                "Investor-style evaluation framework",
                "Clamped 0–100 scores across every dimension",
              ].map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-3 text-sm text-slate-300"
                >
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-xs text-indigo-300">
                    ✓
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </SectionWrapper>

      {/* ══════════════════════════════════════════════════════
       *  HOW IT WORKS — PIPELINE
       * ══════════════════════════════════════════════════════ */}
      <SectionWrapper id="pipeline">
        <SectionHeader
          badge="How It Works"
          title="From Idea to Verdict in 5 Steps"
          gradient
        />

        <div className="relative">
          {/* Connecting line */}
          <div className="absolute left-6 top-0 hidden h-full w-px bg-gradient-to-b from-indigo-500/50 via-purple-500/30 to-cyan-500/50 sm:block" />

          <div className="space-y-6 sm:space-y-8">
            {PIPELINE_STEPS.map((s, i) => (
              <div
                key={s.step}
                className="group relative flex items-start gap-6"
              >
                {/* Step number */}
                <div className="relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-indigo-500/20 bg-[#0f172a] font-mono text-sm font-bold text-indigo-400 transition-all duration-300 group-hover:border-indigo-500/50 group-hover:shadow-lg group-hover:shadow-indigo-500/10">
                  {s.step}
                </div>

                {/* Content */}
                <div className="gradient-border flex-1 rounded-xl bg-[#0f172a] px-6 py-5 transition-all duration-300 group-hover:bg-[#131c31]">
                  <h3 className="text-base font-semibold text-slate-100">
                    {s.title}
                  </h3>
                  <p className="mt-1 text-sm text-slate-400">{s.desc}</p>
                </div>

                {/* Arrow connector (except last) */}
                {i < PIPELINE_STEPS.length - 1 && (
                  <div className="absolute left-6 top-12 hidden h-6 w-px sm:block" />
                )}
              </div>
            ))}
          </div>
        </div>
      </SectionWrapper>

      {/* ══════════════════════════════════════════════════════
       *  FINAL CTA
       * ══════════════════════════════════════════════════════ */}
      <SectionWrapper className="text-center">
        <div className="mx-auto max-w-2xl">
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl">
            Build ideas worth building.
          </h2>
          <p className="mb-10 text-base text-slate-400">
            Stop guessing. Let data-driven AI agents validate your next startup
            before you invest months of effort.
          </p>
          <Link href="/ideas/new">
            <Button size="lg">
              Start Validation
              <ArrowIcon />
            </Button>
          </Link>
        </div>
      </SectionWrapper>

      {/* ── Footer ──────────────────────────────────────────── */}
      <footer className="border-t border-white/[0.04] px-6 py-8 text-center">
        <p className="text-xs text-slate-600">
          StartBot — Multi-Agent AI Startup Validation Engine
        </p>
      </footer>
    </div>
  );
}
