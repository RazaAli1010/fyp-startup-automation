"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { FormProgress } from "@/components/forms/form-progress";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { createIdea } from "@/lib/api";
import type { StartupIdeaInput } from "@/lib/types";
import type { TooltipContent } from "@/components/ui/info-tooltip";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { RouteGuard } from "@/components/auth/route-guard";
import { INDUSTRIES, COUNTRIES, CUSTOMER_TYPES } from "@/lib/constants";

const FIELD_TOOLTIPS: Record<string, TooltipContent> = {
  startup_name: {
    description: "A short, clear name for your startup or idea.",
    impact: "Used for identification only. Does not affect scoring.",
  },
  one_line_description: {
    description:
      "A detailed explanation of your startup: the problem it solves, how it works, who it serves, and what makes it different. 2-5 paragraphs recommended.",
    impact:
      "This is the primary input our AI uses to infer your revenue model, technical complexity, regulatory risk, and generate search queries.",
  },
  industry: {
    description: "Select one or more industries your startup operates in.",
    impact: "Used to identify relevant markets, trends, and competitors.",
  },
  target_customer_type: {
    description:
      "Who your primary customers are: businesses (B2B), consumers (B2C), or both (B2B2C).",
    impact:
      "Affects competition analysis, market sizing, and problem relevance.",
  },
  geography: {
    description: "Select the countries or regions you are targeting.",
    impact: "Used to contextualize market demand and competition.",
  },
};

const CUSTOMER_TYPE_OPTIONS = CUSTOMER_TYPES.map((t) => ({
  value: t,
  label: t,
}));

type FormErrors = Partial<Record<keyof StartupIdeaInput, string>>;

function validate(form: StartupIdeaInput): FormErrors {
  const errors: FormErrors = {};
  if (!form.startup_name.trim()) errors.startup_name = "Required";
  if (!form.one_line_description.trim())
    errors.one_line_description = "Required";
  if (form.one_line_description.trim().split(/\s+/).length < 5)
    errors.one_line_description =
      "Please provide a more detailed description (at least 5 words)";
  if (!form.industry.trim()) errors.industry = "Select at least one industry";
  if (!form.target_customer_type) errors.target_customer_type = "Required";
  if (!form.geography.trim()) errors.geography = "Select at least one country";
  return errors;
}

const INITIAL_FORM: StartupIdeaInput = {
  startup_name: "",
  one_line_description: "",
  industry: "",
  target_customer_type: "" as StartupIdeaInput["target_customer_type"],
  geography: "",
};

const STEP_LABELS = ["Core Idea", "Target Market"];

function computeCurrentStep(form: StartupIdeaInput): number {
  const s1 =
    form.startup_name.trim() !== "" &&
    form.one_line_description.trim().split(/\s+/).length >= 5 &&
    form.industry.trim() !== "";
  const s2 =
    (form.target_customer_type as string) !== "" &&
    form.geography.trim() !== "";

  if (s1 && s2) return 1;
  if (s1) return 0;
  return 0;
}

/* ── Multi-Select Chip Component ─────────────────────────────── */
function MultiSelectChips({
  label,
  tooltip,
  options,
  selected,
  onChange,
  error,
  searchable = false,
  placeholder = "Search...",
}: {
  label: string;
  tooltip?: TooltipContent;
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  error?: string;
  searchable?: boolean;
  placeholder?: string;
}) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filtered = search
    ? options.filter((o) => o.toLowerCase().includes(search.toLowerCase()))
    : options;

  function toggle(item: string) {
    if (selected.includes(item)) {
      onChange(selected.filter((s) => s !== item));
    } else {
      onChange([...selected, item]);
    }
  }

  function remove(item: string) {
    onChange(selected.filter((s) => s !== item));
  }

  return (
    <div className="space-y-1.5" ref={ref}>
      <label className="flex items-center gap-1.5 text-sm font-medium text-slate-300">
        {label}
        {tooltip && <InfoTooltip content={tooltip} />}
      </label>

      {/* Selected chips */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((item) => (
            <span
              key={item}
              className="inline-flex items-center gap-1 rounded-md bg-indigo-500/15 px-2.5 py-1 text-xs font-medium text-indigo-300 border border-indigo-500/20"
            >
              {item}
              <button
                type="button"
                onClick={() => remove(item)}
                className="ml-0.5 text-indigo-400/60 hover:text-indigo-300 transition-colors"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Dropdown trigger */}
      <div className="relative">
        <input
          type="text"
          placeholder={selected.length > 0 ? "Add more..." : placeholder}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          className={`
            w-full rounded-lg border bg-[#0f172a]/80 px-3.5 py-2.5
            text-sm text-slate-100 placeholder-slate-500
            transition-colors duration-150
            focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:ring-offset-1 focus:ring-offset-[#020617]
            ${error ? "border-red-500/50" : "border-slate-700/60 hover:border-indigo-500/30"}
          `}
        />

        {open && filtered.length > 0 && (
          <div className="absolute z-50 mt-1 max-h-48 w-full overflow-y-auto rounded-lg border border-slate-700/60 bg-[#0f172a] shadow-xl">
            {filtered.map((item) => {
              const isSelected = selected.includes(item);
              return (
                <button
                  key={item}
                  type="button"
                  onClick={() => {
                    toggle(item);
                    setSearch("");
                  }}
                  className={`
                    flex w-full items-center gap-2 px-3.5 py-2 text-left text-sm transition-colors
                    ${isSelected ? "bg-indigo-500/10 text-indigo-300" : "text-slate-300 hover:bg-white/5"}
                  `}
                >
                  <span
                    className={`flex h-4 w-4 items-center justify-center rounded border text-[10px] ${
                      isSelected
                        ? "border-indigo-500 bg-indigo-500 text-white"
                        : "border-slate-600"
                    }`}
                  >
                    {isSelected ? "✓" : ""}
                  </span>
                  {item}
                </button>
              );
            })}
          </div>
        )}
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

/* ── Main Form ───────────────────────────────────────────────── */
function NewIdeaForm() {
  const router = useRouter();
  const [form, setForm] = useState<StartupIdeaInput>(INITIAL_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const currentStep = useMemo(() => computeCurrentStep(form), [form]);

  // Industry and geography as arrays (stored as comma-separated in form)
  const selectedIndustries = form.industry
    ? form.industry.split(", ").filter(Boolean)
    : [];
  const selectedGeographies = form.geography
    ? form.geography.split(", ").filter(Boolean)
    : [];

  function update<K extends keyof StartupIdeaInput>(
    key: K,
    value: StartupIdeaInput[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setApiError(null);

    const validationErrors = validate(form);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    console.log("[UI] Submit Idea clicked");
    setSubmitting(true);
    try {
      const res = await createIdea(form);
      router.push(`/ideas/${res.idea_id}`);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Something went wrong";
      setApiError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      {/* Header */}
      <div className="mb-8">
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-indigo-400">
          New Idea
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-50">
          Startup Idea
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Describe your startup in detail. Our AI agents will infer your
          business model, technical complexity, and regulatory risk — then
          evaluate using real market data.
        </p>
      </div>

      <FormProgress
        currentStep={currentStep}
        totalSteps={STEP_LABELS.length}
        stepLabels={STEP_LABELS}
      />

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* ── Section 1: Core Idea ─────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Core Idea</CardTitle>
            <CardDescription>
              The fundamentals of your startup concept.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              label="Startup Name"
              tooltip={FIELD_TOOLTIPS.startup_name}
              placeholder="e.g. FinBot"
              value={form.startup_name}
              onChange={(e) => update("startup_name", e.target.value)}
              error={errors.startup_name}
            />

            {/* Detailed Business Description — textarea */}
            <div className="space-y-1.5">
              <label
                htmlFor="description"
                className="flex items-center gap-1.5 text-sm font-medium text-slate-300"
              >
                Detailed Business Description
                <InfoTooltip content={FIELD_TOOLTIPS.one_line_description} />
              </label>
              <textarea
                id="description"
                rows={6}
                placeholder="Describe the problem your startup solves, how the solution works, who the target users are, and what makes your approach unique. Be as detailed as possible (2-5 paragraphs)."
                value={form.one_line_description}
                onChange={(e) => update("one_line_description", e.target.value)}
                className={`
                  w-full rounded-lg border bg-[#0f172a]/80 px-3.5 py-2.5
                  text-sm text-slate-100 placeholder-slate-500 resize-y min-h-[120px]
                  transition-colors duration-150
                  focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:ring-offset-1 focus:ring-offset-[#020617]
                  ${errors.one_line_description ? "border-red-500/50" : "border-slate-700/60 hover:border-indigo-500/30"}
                `}
              />
              {errors.one_line_description && (
                <p className="text-xs text-red-400">
                  {errors.one_line_description}
                </p>
              )}
              <p className="text-xs text-slate-500">
                {
                  form.one_line_description.trim().split(/\s+/).filter(Boolean)
                    .length
                }{" "}
                words
              </p>
            </div>

            {/* Industry Multi-Select */}
            <MultiSelectChips
              label="Industry"
              tooltip={FIELD_TOOLTIPS.industry}
              options={INDUSTRIES}
              selected={selectedIndustries}
              onChange={(items) => update("industry", items.join(", "))}
              error={errors.industry}
              searchable
              placeholder="Search industries..."
            />
          </CardContent>
        </Card>

        {/* ── Section 2: Target Market ─────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Target Market</CardTitle>
            <CardDescription>Who are you building for?</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Select
              label="Customer Type"
              tooltip={FIELD_TOOLTIPS.target_customer_type}
              options={CUSTOMER_TYPE_OPTIONS}
              value={form.target_customer_type}
              onChange={(e) =>
                update(
                  "target_customer_type",
                  e.target.value as StartupIdeaInput["target_customer_type"],
                )
              }
              error={errors.target_customer_type}
            />

            {/* Geography Multi-Select */}
            <MultiSelectChips
              label="Target Geography"
              tooltip={FIELD_TOOLTIPS.geography}
              options={COUNTRIES}
              selected={selectedGeographies}
              onChange={(items) => update("geography", items.join(", "))}
              error={errors.geography}
              searchable
              placeholder="Search countries..."
            />
          </CardContent>
        </Card>

        {/* ── Submit ───────────────────────────────────────────── */}
        {apiError && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {apiError}
          </div>
        )}

        <Button type="submit" size="lg" loading={submitting} className="w-full">
          {submitting ? "Submitting..." : "Submit & Evaluate"}
        </Button>
      </form>
    </div>
  );
}

export default function NewIdeaPage() {
  return (
    <RouteGuard>
      <NewIdeaForm />
    </RouteGuard>
  );
}
