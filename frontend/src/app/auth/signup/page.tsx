"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { signup, getGoogleLoginUrl, getGoogleAuthStatus } from "@/lib/api";

// ── Password strength helpers ────────────────────────────────
const PW_RULES = [
  { re: /.{8,}/, label: "At least 8 characters" },
  { re: /[A-Z]/, label: "One uppercase letter" },
  { re: /[a-z]/, label: "One lowercase letter" },
  { re: /[0-9]/, label: "One number" },
  {
    re: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/,
    label: "One special character",
  },
];

const COMMON_PASSWORDS = new Set([
  "password",
  "password1",
  "123456",
  "12345678",
  "123456789",
  "qwerty",
  "abc123",
  "letmein",
  "welcome",
  "admin",
]);

function getPasswordStrength(pw: string) {
  if (!pw) return { score: 0, level: "none" as const };
  const passed = PW_RULES.filter((r) => r.re.test(pw)).length;
  const isCommon = COMMON_PASSWORDS.has(pw.toLowerCase());
  if (isCommon) return { score: 0, level: "weak" as const };
  if (passed <= 2) return { score: 1, level: "weak" as const };
  if (passed <= 4) return { score: 2, level: "medium" as const };
  return { score: 3, level: "strong" as const };
}

const STRENGTH_COLORS = {
  none: "bg-white/10",
  weak: "bg-red-500",
  medium: "bg-amber-500",
  strong: "bg-emerald-500",
};

const STRENGTH_LABELS = {
  none: "",
  weak: "Weak",
  medium: "Medium",
  strong: "Strong",
};

// ── Username validation ──────────────────────────────────────
const USERNAME_RE = /^[a-zA-Z0-9_]{3,20}$/;

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [googleEnabled, setGoogleEnabled] = useState<boolean | null>(null);

  useEffect(() => {
    getGoogleAuthStatus()
      .then((s) => setGoogleEnabled(s.google_auth_enabled))
      .catch(() => setGoogleEnabled(false));
  }, []);

  const strength = useMemo(() => getPasswordStrength(password), [password]);
  const allRulesPassed =
    PW_RULES.every((r) => r.re.test(password)) &&
    !COMMON_PASSWORDS.has(password.toLowerCase());
  const usernameValid = USERNAME_RE.test(username);
  const formValid =
    allRulesPassed &&
    usernameValid &&
    password === confirmPassword &&
    email.length > 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!usernameValid) {
      setError(
        "Username must be 3-20 characters (letters, numbers, underscores only)",
      );
      return;
    }

    if (!allRulesPassed) {
      setError("Password does not meet all requirements");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      await signup(email, username, password);
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-6">
        <div className="w-full max-w-sm space-y-6 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-indigo-500/10">
            <svg
              className="h-7 w-7 text-indigo-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-slate-50">Check your email</h1>
          <p className="text-sm text-slate-400">
            We sent a verification link to{" "}
            <span className="font-medium text-slate-200">{email}</span>. Please
            verify your email to continue.
          </p>
          <Link
            href="/auth/login"
            className="inline-block text-sm font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Go to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-6">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight text-slate-50">
            Create your account
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Start validating startup ideas with AI
          </p>
        </div>

        {googleEnabled === false ? (
          <div
            className="flex w-full items-center justify-center gap-3 rounded-lg border border-white/5 bg-white/[0.02] px-4 py-2.5 text-sm font-medium text-slate-500 cursor-not-allowed"
            title="Google login is currently unavailable"
          >
            <svg className="h-5 w-5 opacity-40" viewBox="0 0 24 24">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                fill="#666"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#666"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#666"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#666"
              />
            </svg>
            Google login unavailable
          </div>
        ) : (
          <a
            href={getGoogleLoginUrl()}
            className="flex w-full items-center justify-center gap-3 rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 transition-colors hover:bg-white/10"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            Continue with Google
          </a>
        )}

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/10" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="bg-[#020617] px-3 text-slate-500">
              or sign up with email
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-2.5 text-sm text-red-400">
              {error}
            </div>
          )}

          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-xs font-medium text-slate-400"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/25"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label
              htmlFor="username"
              className="mb-1.5 block text-xs font-medium text-slate-400"
            >
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/25"
              placeholder="your_username"
            />
            {username && !usernameValid && (
              <p className="mt-1 text-xs text-amber-400">
                3-20 characters, letters, numbers, underscores only
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1.5 block text-xs font-medium text-slate-400"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/25"
              placeholder="Strong password"
            />

            {password && (
              <div className="mt-2 space-y-2">
                {/* Strength bar */}
                <div className="flex items-center gap-2">
                  <div className="flex flex-1 gap-1">
                    {[1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className={`h-1 flex-1 rounded-full transition-colors ${
                          i <= strength.score
                            ? STRENGTH_COLORS[strength.level]
                            : "bg-white/10"
                        }`}
                      />
                    ))}
                  </div>
                  <span
                    className={`text-xs font-medium ${
                      strength.level === "weak"
                        ? "text-red-400"
                        : strength.level === "medium"
                          ? "text-amber-400"
                          : strength.level === "strong"
                            ? "text-emerald-400"
                            : "text-slate-500"
                    }`}
                  >
                    {STRENGTH_LABELS[strength.level]}
                  </span>
                </div>

                {/* Rule checklist */}
                <ul className="space-y-0.5">
                  {PW_RULES.map((rule) => {
                    const passed = rule.re.test(password);
                    return (
                      <li
                        key={rule.label}
                        className={`flex items-center gap-1.5 text-xs ${passed ? "text-emerald-400" : "text-slate-500"}`}
                      >
                        {passed ? (
                          <svg
                            className="h-3 w-3"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={3}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        ) : (
                          <svg
                            className="h-3 w-3"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={3}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M19 12H5"
                            />
                          </svg>
                        )}
                        {rule.label}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </div>

          <div>
            <label
              htmlFor="confirmPassword"
              className="mb-1.5 block text-xs font-medium text-slate-400"
            >
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/25"
              placeholder="Repeat password"
            />
            {confirmPassword && password !== confirmPassword && (
              <p className="mt-1 text-xs text-red-400">
                Passwords do not match
              </p>
            )}
          </div>

          <Button
            type="submit"
            loading={loading}
            disabled={!formValid}
            fullWidth
          >
            {loading ? "Creating account…" : "Create Account"}
          </Button>
        </form>

        <p className="text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link
            href="/auth/login"
            className="font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
