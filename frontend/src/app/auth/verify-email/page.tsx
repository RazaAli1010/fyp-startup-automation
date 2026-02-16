"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Missing verification token.");
      return;
    }

    async function verify() {
      try {
        const res = await fetch(
          `${API_BASE_URL}/auth/verify-email?token=${encodeURIComponent(token!)}`,
        );
        const data = await res.json();
        if (res.ok) {
          setStatus("success");
          setMessage(data.message ?? "Email verified successfully.");
        } else {
          setStatus("error");
          setMessage(data.detail ?? "Verification failed.");
        }
      } catch {
        setStatus("error");
        setMessage("Network error — could not reach the server.");
      }
    }

    verify();
  }, [token]);

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-6">
      <div className="w-full max-w-sm space-y-6 text-center">
        {status === "loading" && (
          <>
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
            <p className="text-sm text-slate-400">Verifying your email…</p>
          </>
        )}

        {status === "success" && (
          <>
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10">
              <svg
                className="h-7 w-7 text-emerald-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-slate-50">Email Verified</h1>
            <p className="text-sm text-slate-400">{message}</p>
            <Link
              href="/auth/login"
              className="inline-block rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 px-6 py-2.5 text-sm font-medium text-white shadow-lg shadow-indigo-500/25 transition-all hover:shadow-indigo-500/40 hover:brightness-110"
            >
              Go to Login
            </Link>
          </>
        )}

        {status === "error" && (
          <>
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-500/10">
              <svg
                className="h-7 w-7 text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-slate-50">
              Verification Failed
            </h1>
            <p className="text-sm text-slate-400">{message}</p>
            <Link
              href="/auth/signup"
              className="inline-block text-sm font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              Try signing up again
            </Link>
          </>
        )}
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
