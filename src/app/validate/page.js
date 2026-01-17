"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function ValidatePage() {
  const [idea, setIdea] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleAnalyze = async () => {
    if (!idea.trim()) return alert("Please enter your idea");

    setLoading(true);
    localStorage.setItem("startupIdea", idea);
    router.push("/result");
  };

  return (
    <div className="max-w-4xl mx-auto mt-20">
      <h2 className="text-4xl font-bold mb-6 text-center">
        Describe Your Startup Idea 💡
      </h2>

      <textarea
        rows="8"
        value={idea}
        onChange={(e) => setIdea(e.target.value)}
        placeholder="Example: A peer-to-peer item renting platform with lender and borrower subscriptions..."
        className="w-full p-6 rounded-xl text-black text-lg outline-none"
      />

      <button
        onClick={handleAnalyze}
        disabled={loading}
        className="w-full mt-6 bg-cyan-500 py-4 rounded-xl text-black font-bold text-xl hover:bg-cyan-400"
      >
        {loading ? "Analyzing..." : "Analyze Idea"}
      </button>
    </div>
  );
}
