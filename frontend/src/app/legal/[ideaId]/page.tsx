"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { generateLegalDocument, getLegalByIdea, ApiError } from "@/lib/api";
import type { GenerateLegalRequest } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { GatingModal } from "@/components/ui/gating-modal";
import { RouteGuard } from "@/components/auth/route-guard";
import { BackButton } from "@/components/ui/back-button";
import type { LegalDocumentRecord, LegalDocumentResponse } from "@/lib/types";

type Status = "idle" | "loading" | "generating" | "success" | "error";

const DOCUMENT_TYPES = [
  { key: "nda", label: "Non-Disclosure Agreement", short: "NDA" },
  { key: "founder_agreement", label: "Founder Agreement", short: "Founder" },
  { key: "privacy_policy", label: "Privacy Policy", short: "Privacy" },
  { key: "terms_of_service", label: "Terms of Service", short: "ToS" },
];

function statusBadge(s: string) {
  switch (s) {
    case "generated":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
    case "failed":
      return "border-red-500/30 bg-red-500/10 text-red-400";
    default:
      return "border-amber-500/30 bg-amber-500/10 text-amber-400";
  }
}

function LegalContent() {
  const params = useParams();
  const router = useRouter();
  const ideaId = params.ideaId as string;

  const [status, setStatus] = useState<Status>("loading");
  const [documents, setDocuments] = useState<LegalDocumentRecord[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<LegalDocumentRecord | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState<string | null>(null);

  // Fetch existing legal documents for this idea
  const fetchDocs = useCallback(async () => {
    if (!ideaId) return;
    try {
      const res = await getLegalByIdea(ideaId);
      setDocuments(res.records || []);
      setStatus("success");
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 404) {
        setDocuments([]);
        setStatus("success");
      } else {
        setError(
          err instanceof Error ? err.message : "Failed to load documents",
        );
        setStatus("error");
      }
    }
  }, [ideaId]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  // Generate a specific document type
  const handleGenerate = async (docTypeKey: string) => {
    setGenerating(docTypeKey);
    setError(null);
    try {
      const body: GenerateLegalRequest = { document_type: docTypeKey };
      const result = await generateLegalDocument(ideaId, body);
      // Update documents list
      setDocuments((prev) => {
        const filtered = prev.filter(
          (d) => d.document_type !== result.document_type,
        );
        return [result, ...filtered];
      });
      setSelectedDoc(result);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Generation failed. Please try again.",
      );
    } finally {
      setGenerating(null);
    }
  };

  // Find existing doc by type
  const getDocByType = (key: string) =>
    documents.find((d) => d.document_type === key && d.status === "generated");

  // ── Loading ────────────────────────────────────────────────
  if (status === "loading") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
        <Spinner size="lg" label="Loading legal documents..." />
      </div>
    );
  }

  // ── Error (full page) ─────────────────────────────────────
  if (status === "error" && documents.length === 0) {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center gap-4 px-6">
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-6 py-4 text-center">
          <p className="text-sm font-medium text-red-400">{error}</p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => fetchDocs()}>
          Retry
        </Button>
      </div>
    );
  }

  // ── Render document viewer ────────────────────────────────
  const doc = selectedDoc?.document;

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <BackButton fallback="/dashboard" />

      {/* Header */}
      <div className="mb-8 mt-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-emerald-400">
          Legal Documents
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-50">
          Legal Document Generator
        </h1>
        <p className="mt-1 text-sm text-slate-500 font-mono">{ideaId}</p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Document type cards */}
      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {DOCUMENT_TYPES.map((dt) => {
          const existing = getDocByType(dt.key);
          const isGenerating = generating === dt.key;
          const isSelected = selectedDoc?.document_type === dt.key;

          return (
            <button
              key={dt.key}
              disabled={isGenerating}
              onClick={() => {
                if (existing) {
                  setSelectedDoc(existing);
                } else {
                  handleGenerate(dt.key);
                }
              }}
              className={`group relative flex flex-col items-center gap-2 rounded-xl border p-4 transition-all duration-200 hover:-translate-y-0.5 ${
                isSelected
                  ? "border-emerald-500/40 bg-emerald-500/10"
                  : "border-white/10 bg-white/[0.02] hover:bg-white/[0.05] hover:border-emerald-500/20"
              } ${isGenerating ? "opacity-60 cursor-wait" : ""}`}
            >
              {/* Status indicator */}
              {existing && (
                <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-emerald-400" />
              )}

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

              <span className="text-xs font-semibold text-slate-100 text-center leading-tight">
                {dt.short}
              </span>

              {isGenerating ? (
                <Spinner size="sm" />
              ) : existing ? (
                <span className="text-[10px] text-emerald-400 font-medium">
                  View
                </span>
              ) : (
                <span className="text-[10px] text-slate-500 font-medium">
                  Generate
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Document display */}
      {doc && selectedDoc ? (
        <div className="space-y-6">
          {/* Document header + Download */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-50">
                  {doc.document_type
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, (c: string) => c.toUpperCase())}
                </h2>
                <div className="mt-3 flex flex-wrap gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
                    <svg
                      className="h-3 w-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"
                      />
                    </svg>
                    {doc.jurisdiction}
                  </span>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-300">
                    <svg
                      className="h-3 w-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z"
                      />
                    </svg>
                    {doc.governing_law}
                  </span>
                  <span
                    className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${statusBadge(selectedDoc.status)}`}
                  >
                    {selectedDoc.status}
                  </span>
                </div>
              </div>
              <button
                onClick={() => {
                  const printArea = document.getElementById("legal-doc-print");
                  if (!printArea) return;
                  const w = window.open("", "_blank");
                  if (!w) return;
                  w.document.write(
                    `<html><head><title>${doc.document_type}</title><style>body{font-family:Georgia,serif;max-width:800px;margin:40px auto;padding:0 20px;color:#1e293b;line-height:1.8}h1{font-size:24px;margin-bottom:8px}h2{font-size:18px;margin-top:28px;margin-bottom:8px;border-bottom:1px solid #e2e8f0;padding-bottom:4px}.meta{color:#64748b;font-size:13px;margin-bottom:24px}.disclaimer{background:#fffbeb;border:1px solid #fbbf24;border-radius:8px;padding:12px 16px;font-size:13px;color:#92400e;margin-bottom:24px}.section{margin-bottom:20px}.notes{background:#f8fafc;border-radius:8px;padding:16px;margin-top:24px}.notes h3{font-size:14px;font-weight:600;margin-bottom:8px}.notes li{font-size:13px;margin-bottom:4px;color:#475569}@media print{body{margin:20px}}</style></head><body>`,
                  );
                  w.document.write(
                    `<h1>${doc.document_type.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())}</h1>`,
                  );
                  w.document.write(
                    `<div class="meta">${doc.jurisdiction} &middot; ${doc.governing_law}</div>`,
                  );
                  w.document.write(
                    `<div class="disclaimer">${doc.disclaimer}</div>`,
                  );
                  doc.sections.forEach((s, idx) => {
                    w.document.write(
                      `<div class="section"><h2>${idx + 1}. ${s.title}</h2><p>${s.content.replace(/\n/g, "<br/>")}</p></div>`,
                    );
                  });
                  if (doc.customization_notes.length > 0) {
                    w.document.write(
                      `<div class="notes"><h3>Customization Notes</h3><ul>${doc.customization_notes.map((n) => `<li>${n}</li>`).join("")}</ul></div>`,
                    );
                  }
                  if (doc.legal_risk_notes.length > 0) {
                    w.document.write(
                      `<div class="notes"><h3>Legal Risk Notes</h3><ul>${doc.legal_risk_notes.map((n) => `<li>${n}</li>`).join("")}</ul></div>`,
                    );
                  }
                  w.document.write(`</body></html>`);
                  w.document.close();
                  setTimeout(() => {
                    w.print();
                  }, 300);
                }}
                className="shrink-0 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 transition-all hover:shadow-emerald-500/40 hover:brightness-110 hover:scale-[1.02]"
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                  />
                </svg>
                Download PDF
              </button>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-5 py-4">
            <div className="flex items-start gap-3">
              <svg
                className="mt-0.5 h-4 w-4 shrink-0 text-amber-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
              <p className="text-sm leading-relaxed text-amber-300/90">
                {doc.disclaimer}
              </p>
            </div>
          </div>

          {/* Document body — printable area */}
          <div
            id="legal-doc-print"
            className="rounded-2xl border border-white/10 bg-[#0c1222] p-6 sm:p-8"
          >
            {doc.sections.map((section, i) => (
              <div
                key={i}
                className={`${i > 0 ? "mt-8 border-t border-white/5 pt-8" : ""}`}
              >
                <h3
                  className="mb-4 flex items-center gap-3 text-lg font-bold text-slate-100"
                  style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-xs font-bold text-emerald-400">
                    {i + 1}
                  </span>
                  {section.title}
                </h3>
                <div
                  className="whitespace-pre-wrap text-base leading-[1.85] text-slate-300/90"
                  style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
                >
                  {section.content}
                </div>
              </div>
            ))}
          </div>

          {/* Customization notes */}
          {doc.customization_notes.length > 0 && (
            <div className="rounded-xl border border-indigo-500/10 bg-indigo-500/5 p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-100">
                <svg
                  className="h-4 w-4 text-indigo-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M11.42 15.17l-5.59-5.59a2.002 2.002 0 010-2.83l.81-.81a2.002 2.002 0 012.83 0L12 8.47l2.53-2.53a2.002 2.002 0 012.83 0l.81.81a2.002 2.002 0 010 2.83l-5.59 5.59a.996.996 0 01-1.41 0z"
                  />
                </svg>
                Customization Notes
              </h3>
              <ul className="space-y-2">
                {doc.customization_notes.map((note, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2.5 text-sm leading-relaxed text-slate-400"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Legal risk notes */}
          {doc.legal_risk_notes.length > 0 && (
            <div className="rounded-xl border border-amber-500/10 bg-amber-500/5 p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-300">
                <svg
                  className="h-4 w-4 text-amber-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                  />
                </svg>
                Legal Risk Notes
              </h3>
              <ul className="space-y-2">
                {doc.legal_risk_notes.map((note, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2.5 text-sm leading-relaxed text-amber-400/80"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <Card>
          <CardContent className="flex h-48 flex-col items-center justify-center gap-3">
            <svg
              className="h-10 w-10 text-slate-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
              />
            </svg>
            <p className="text-sm text-slate-500">
              Select a document type above to generate or view
            </p>
          </CardContent>
        </Card>
      )}

      {/* Agent Actions */}
      <div className="mt-8 mb-8 rounded-2xl border border-white/10 bg-white/[0.02] p-6">
        <h2 className="mb-1 text-lg font-semibold text-slate-100">
          Related Tools
        </h2>
        <p className="mb-5 text-sm text-slate-500">
          Explore other reports for this idea.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <button
            onClick={() => router.push(`/ideas/${ideaId}`)}
            className="group flex flex-col items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.02] p-5 transition-all duration-200 hover:bg-white/[0.05] hover:border-indigo-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-indigo-500/10"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10 transition-transform duration-200 group-hover:scale-110">
              <svg
                className="h-5 w-5 text-indigo-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold text-slate-100">
              View Evaluation
            </span>
            <span className="text-xs text-slate-500">Viability scores</span>
          </button>

          <button
            onClick={() => router.push(`/ideas/${ideaId}/pitch-deck`)}
            className="group flex flex-col items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.02] p-5 transition-all duration-200 hover:bg-white/[0.05] hover:border-purple-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-purple-500/10"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10 transition-transform duration-200 group-hover:scale-110">
              <svg
                className="h-5 w-5 text-purple-400"
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
            <span className="text-sm font-semibold text-slate-100">
              Pitch Deck
            </span>
            <span className="text-xs text-slate-500">Investor-ready deck</span>
          </button>

          <button
            onClick={() => router.push(`/mvp/${ideaId}`)}
            className="group flex flex-col items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.02] p-5 transition-all duration-200 hover:bg-white/[0.05] hover:border-orange-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-orange-500/10"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/10 transition-transform duration-200 group-hover:scale-110">
              <svg
                className="h-5 w-5 text-orange-400"
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
            <span className="text-sm font-semibold text-slate-100">
              MVP Blueprint
            </span>
            <span className="text-xs text-slate-500">Feature plan</span>
          </button>

          {/* AI Chat Co-Founder */}
          <button
            onClick={() => router.push(`/chat/${ideaId}`)}
            className="group flex flex-col items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.02] p-5 transition-all duration-200 hover:bg-white/[0.05] hover:border-indigo-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-indigo-500/10"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10 transition-transform duration-200 group-hover:scale-110">
              <svg
                className="h-5 w-5 text-indigo-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold text-slate-100">
              AI Co-Founder
            </span>
            <span className="text-xs text-slate-500">
              Ask strategic questions
            </span>
          </button>
        </div>
      </div>

      {/* Quick links */}
      <div className="flex justify-center gap-4">
        <Link href="/dashboard">
          <Button variant="ghost">Dashboard</Button>
        </Link>
      </div>
    </div>
  );
}

export default function LegalPage() {
  return (
    <RouteGuard>
      <LegalContent />
    </RouteGuard>
  );
}
