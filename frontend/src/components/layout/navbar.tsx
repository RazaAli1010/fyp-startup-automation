"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/auth/login");
  }

  return (
    <header className="fixed top-0 z-50 w-full border-b border-white/[0.06] bg-[#020617]/80 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
        <Link
          href={user ? "/dashboard" : "/"}
          className="flex items-center gap-2.5 group"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/20 transition-shadow group-hover:shadow-indigo-500/40">
            <span className="text-xs font-bold text-white">S</span>
          </div>
          <span className="text-sm font-semibold tracking-tight text-slate-100">
            StartBot
          </span>
        </Link>

        <nav className="flex items-center gap-2">
          {user ? (
            <>
              <Link
                href="/dashboard"
                className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-300 transition-colors hover:text-slate-100"
              >
                Dashboard
              </Link>
              <Link
                href="/ideas/new"
                className="rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 px-4 py-1.5 text-sm font-medium text-white shadow-lg shadow-indigo-500/25 transition-all hover:shadow-indigo-500/40 hover:brightness-110"
              >
                Validate Idea
              </Link>
              <button
                onClick={handleLogout}
                className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-400 transition-colors hover:text-slate-200"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                href="/auth/login"
                className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-300 transition-colors hover:text-slate-100"
              >
                Log In
              </Link>
              <Link
                href="/auth/signup"
                className="rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 px-4 py-1.5 text-sm font-medium text-white shadow-lg shadow-indigo-500/25 transition-all hover:shadow-indigo-500/40 hover:brightness-110"
              >
                Sign Up
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
