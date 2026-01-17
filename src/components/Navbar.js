"use client";
import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="flex justify-between items-center px-10 py-4 bg-slate-900 shadow-lg">
      <Link href="/" className="text-2xl font-bold text-cyan-400">
        StartupAgent 🚀
      </Link>

      <div className="space-x-6">
        <Link href="/" className="hover:text-cyan-400">Home</Link>
        <Link
          href="/validate"
          className="bg-cyan-500 px-4 py-2 rounded-lg text-black font-semibold hover:bg-cyan-400"
        >
          Validate Your Idea
        </Link>
      </div>
    </nav>
  );
}
