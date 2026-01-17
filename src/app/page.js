import Link from "next/link";

export default function Home() {
  return (
    <section className="flex flex-col items-center justify-center text-center mt-24">
      <h1 className="text-5xl font-extrabold mb-6">
        Startup Automation Agent 🤖
      </h1>

      <p className="text-gray-300 max-w-2xl mb-10">
        Validate your startup idea instantly using AI-powered market,
        feasibility, and business model analysis.
      </p>

      <Link
        href="/validate"
        className="bg-cyan-500 text-black px-8 py-4 rounded-xl font-bold text-lg hover:bg-cyan-400"
      >
        Validate Your Idea
      </Link>
    </section>
  );
}
