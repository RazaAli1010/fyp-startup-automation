"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { setToken, getMe } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

function GoogleCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setError("No token received from Google authentication.");
      return;
    }

    async function handleToken() {
      try {
        setToken(token!);
        const user = await getMe();
        login(token!, user);
        router.replace("/dashboard");
      } catch {
        setError("Failed to authenticate with Google. Please try again.");
      }
    }

    handleToken();
  }, [searchParams, router, login]);

  if (error) {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-6">
        <div className="w-full max-w-sm space-y-6 text-center">
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
            Authentication Failed
          </h1>
          <p className="text-sm text-slate-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
      <div className="space-y-4 text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        <p className="text-sm text-slate-400">Completing Google sign-in…</p>
      </div>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        </div>
      }
    >
      <GoogleCallbackContent />
    </Suspense>
  );
}
