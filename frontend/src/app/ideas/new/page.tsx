"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
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
import { RouteGuard } from "@/components/auth/route-guard";

const FIELD_TOOLTIPS: Record<string, TooltipContent> = {
  startup_name: {
    description: "A short, clear name for your startup or idea.",
    impact: "Used for identification only. Does not affect scoring.",
  },
  one_line_description: {
    description:
      "A concise explanation of what your startup does and who it is for.",
    impact: "Helps generate search and analysis queries.",
  },
  industry: {
    description:
      "The primary industry your startup operates in (e.g. FinTech, HealthTech, SaaS).",
    impact: "Used to identify relevant markets, trends, and competitors.",
  },
  target_customer_type: {
    description:
      "Who your primary customers are (businesses, consumers, or both).",
    impact: "Affects competition analysis and problem relevance.",
  },
  geography: {
    description: "The main region or country you are targeting.",
    impact: "Used to contextualize market demand and competition.",
  },
  customer_size: {
    description:
      "The size of your typical customer (individuals, SMBs, enterprises).",
    impact: "Affects market realism and competition pressure.",
  },
  revenue_model: {
    description:
      "How you plan to make money (subscription, one-time payment, etc.).",
    impact: "Used as contextual information only.",
  },
  pricing_estimate: {
    description: "Approximate price you expect customers to pay.",
    impact: "Used to assess market positioning (not exact revenue).",
  },
  estimated_cac: {
    description: "Estimated cost to acquire one customer.",
    impact: "Used as contextual input for execution realism.",
  },
  estimated_ltv: {
    description: "Estimated total revenue from a customer over their lifetime.",
    impact: "Used as contextual input only.",
  },
  team_size: {
    description:
      "Expected number of people needed to build and run the product initially.",
    impact: "Used to assess execution feasibility.",
  },
  tech_complexity: {
    description:
      "How difficult the technology is to build (0 = simple, 1 = very complex).",
    impact: "Higher complexity reduces execution feasibility score.",
  },
  regulatory_risk: {
    description:
      "How much regulation or legal complexity is involved (0 = none, 1 = very high).",
    impact: "Higher regulatory risk reduces execution feasibility score.",
  },
};

const CUSTOMER_TYPE_OPTIONS = [
  { value: "B2B", label: "B2B" },
  { value: "B2C", label: "B2C" },
  { value: "Marketplace", label: "Marketplace" },
];

const CUSTOMER_SIZE_OPTIONS = [
  { value: "Individual", label: "Individual" },
  { value: "SMB", label: "SMB" },
  { value: "Mid-Market", label: "Mid-Market" },
  { value: "Enterprise", label: "Enterprise" },
];

const REVENUE_MODEL_OPTIONS = [
  { value: "Subscription", label: "Subscription" },
  { value: "One-time", label: "One-time" },
  { value: "Marketplace Fee", label: "Marketplace Fee" },
  { value: "Ads", label: "Ads" },
];

type FormErrors = Partial<Record<keyof StartupIdeaInput, string>>;

function validate(form: StartupIdeaInput): FormErrors {
  const errors: FormErrors = {};
  if (!form.startup_name.trim()) errors.startup_name = "Required";
  if (!form.one_line_description.trim())
    errors.one_line_description = "Required";
  if (!form.industry.trim()) errors.industry = "Required";
  if (!form.target_customer_type) errors.target_customer_type = "Required";
  if (!form.geography.trim()) errors.geography = "Required";
  if (!form.customer_size) errors.customer_size = "Required";
  if (!form.revenue_model) errors.revenue_model = "Required";
  if (form.pricing_estimate <= 0) errors.pricing_estimate = "Must be > 0";
  if (form.estimated_cac < 0) errors.estimated_cac = "Must be >= 0";
  if (form.estimated_ltv < 0) errors.estimated_ltv = "Must be >= 0";
  if (form.team_size < 1) errors.team_size = "Must be >= 1";
  return errors;
}

const INITIAL_FORM: StartupIdeaInput = {
  startup_name: "",
  one_line_description: "",
  industry: "",
  target_customer_type: "" as StartupIdeaInput["target_customer_type"],
  geography: "",
  customer_size: "" as StartupIdeaInput["customer_size"],
  revenue_model: "" as StartupIdeaInput["revenue_model"],
  pricing_estimate: 0,
  estimated_cac: 0,
  estimated_ltv: 0,
  team_size: 1,
  tech_complexity: 0.5,
  regulatory_risk: 0.3,
};

const STEP_LABELS = [
  "Core Idea",
  "Target Market",
  "Business Model",
  "Execution",
];

function computeCurrentStep(form: StartupIdeaInput): number {
  const s1 =
    form.startup_name.trim() !== "" &&
    form.one_line_description.trim() !== "" &&
    form.industry.trim() !== "";
  const s2 =
    (form.target_customer_type as string) !== "" &&
    form.geography.trim() !== "" &&
    (form.customer_size as string) !== "";
  const s3 = (form.revenue_model as string) !== "" && form.pricing_estimate > 0;

  if (s1 && s2 && s3) return 3;
  if (s1 && s2) return 2;
  if (s1) return 1;
  return 0;
}

function NewIdeaForm() {
  const router = useRouter();
  const [form, setForm] = useState<StartupIdeaInput>(INITIAL_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const currentStep = useMemo(() => computeCurrentStep(form), [form]);

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
          Fill in every section. Our AI agents will evaluate your idea using
          real market data.
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
            <Input
              label="One-Line Description"
              tooltip={FIELD_TOOLTIPS.one_line_description}
              placeholder="e.g. AI-powered bookkeeping for freelancers"
              value={form.one_line_description}
              onChange={(e) => update("one_line_description", e.target.value)}
              error={errors.one_line_description}
            />
            <Input
              label="Industry"
              tooltip={FIELD_TOOLTIPS.industry}
              placeholder="e.g. Fintech, Healthcare, EdTech"
              value={form.industry}
              onChange={(e) => update("industry", e.target.value)}
              error={errors.industry}
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
            <Input
              label="Geography"
              tooltip={FIELD_TOOLTIPS.geography}
              placeholder="e.g. United States, Global, Southeast Asia"
              value={form.geography}
              onChange={(e) => update("geography", e.target.value)}
              error={errors.geography}
            />
            <Select
              label="Customer Size"
              tooltip={FIELD_TOOLTIPS.customer_size}
              options={CUSTOMER_SIZE_OPTIONS}
              value={form.customer_size}
              onChange={(e) =>
                update(
                  "customer_size",
                  e.target.value as StartupIdeaInput["customer_size"],
                )
              }
              error={errors.customer_size}
            />
          </CardContent>
        </Card>

        {/* ── Section 3: Business Model ────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Business Model</CardTitle>
            <CardDescription>How will this startup make money?</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Select
              label="Revenue Model"
              tooltip={FIELD_TOOLTIPS.revenue_model}
              options={REVENUE_MODEL_OPTIONS}
              value={form.revenue_model}
              onChange={(e) =>
                update(
                  "revenue_model",
                  e.target.value as StartupIdeaInput["revenue_model"],
                )
              }
              error={errors.revenue_model}
            />
            <Input
              label="Pricing Estimate (USD)"
              tooltip={FIELD_TOOLTIPS.pricing_estimate}
              type="number"
              min={0}
              step={0.01}
              placeholder="e.g. 29.99"
              value={form.pricing_estimate || ""}
              onChange={(e) =>
                update("pricing_estimate", parseFloat(e.target.value) || 0)
              }
              error={errors.pricing_estimate}
            />
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Estimated CAC (USD)"
                tooltip={FIELD_TOOLTIPS.estimated_cac}
                type="number"
                min={0}
                step={0.01}
                placeholder="e.g. 50"
                value={form.estimated_cac || ""}
                onChange={(e) =>
                  update("estimated_cac", parseFloat(e.target.value) || 0)
                }
                error={errors.estimated_cac}
              />
              <Input
                label="Estimated LTV (USD)"
                tooltip={FIELD_TOOLTIPS.estimated_ltv}
                type="number"
                min={0}
                step={0.01}
                placeholder="e.g. 500"
                value={form.estimated_ltv || ""}
                onChange={(e) =>
                  update("estimated_ltv", parseFloat(e.target.value) || 0)
                }
                error={errors.estimated_ltv}
              />
            </div>
          </CardContent>
        </Card>

        {/* ── Section 4: Execution Assumptions ─────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Execution Assumptions</CardTitle>
            <CardDescription>
              Your team and technical landscape.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <Input
              label="Team Size"
              tooltip={FIELD_TOOLTIPS.team_size}
              type="number"
              min={1}
              step={1}
              placeholder="e.g. 3"
              value={form.team_size || ""}
              onChange={(e) =>
                update("team_size", parseInt(e.target.value, 10) || 1)
              }
              error={errors.team_size}
            />
            <Slider
              label="Tech Complexity"
              tooltip={FIELD_TOOLTIPS.tech_complexity}
              min={0}
              max={1}
              step={0.05}
              value={form.tech_complexity}
              displayValue={`${Math.round(form.tech_complexity * 100)}%`}
              onChange={(e) =>
                update("tech_complexity", parseFloat(e.target.value))
              }
            />
            <Slider
              label="Regulatory Risk"
              tooltip={FIELD_TOOLTIPS.regulatory_risk}
              min={0}
              max={1}
              step={0.05}
              value={form.regulatory_risk}
              displayValue={`${Math.round(form.regulatory_risk * 100)}%`}
              onChange={(e) =>
                update("regulatory_risk", parseFloat(e.target.value))
              }
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
