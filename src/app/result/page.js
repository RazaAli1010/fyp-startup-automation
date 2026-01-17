"use client";
import { useEffect, useState } from "react";

function ResultCard({ title, children }) {
  return (
    <div className="relative group">
      <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500/20 via-blue-500/20 to-indigo-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
      <div className="relative bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-lg p-8 rounded-2xl border border-white/20 shadow-2xl hover:border-emerald-500/30 transition-all duration-300">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-8 w-1 bg-gradient-to-b from-emerald-400 to-blue-400 rounded-full"></div>
          <h3 className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
            {title}
          </h3>
        </div>
        <div className="text-gray-200 leading-relaxed space-y-3">
          {children}
        </div>
        <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-emerald-500/10 to-transparent rounded-bl-full"></div>
      </div>
    </div>
  );
}

export default function ResultPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const idea = localStorage.getItem("startupIdea");
    if (!idea) {
      setLoading(false);
      return;
    }

    // Simulate API call
    setTimeout(() => {
      const mockData = {
        idea_input: idea,
        competitor_analysis: {
          competitors_found: 3,
          direct_competitors: [
            { name: "CompetitorA", description: "Similar platform", url: "https://example.com" }
          ],
          indirect_competitors: ["CompetitorB"],
          differentiation_opportunities: ["Unique feature set"],
          market_structure: { type: "Fragmented" }
        },
        trends_data: { trend_direction: "Growing", interest_score: 75 },
        reddit_sentiment: {
          overall_sentiment: "Positive",
          sentiment_score: 8,
          total_posts_analyzed: 150,
          key_concerns: ["Privacy"],
          key_praises: ["Innovation"]
        },
        final_verdict: {
          overall_score: 85,
          summary: "Strong potential with clear market opportunity.",
          confidence: 0.87
        }
      };
      setData(mockData);
      setLoading(false);
    }, 1500);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-24 h-24 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-emerald-500/20 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <p className="text-white text-xl font-semibold">Analyzing your startup idea...</p>
          <p className="text-gray-400 mt-2">This may take a few moments</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center">
        <div className="text-center bg-white/5 backdrop-blur-lg rounded-2xl p-12 border border-white/10">
          <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-red-500 to-red-600 rounded-full flex items-center justify-center">
            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <p className="text-white text-2xl font-bold mb-2">No data found</p>
          <p className="text-gray-400">Please submit an idea first</p>
        </div>
      </div>
    );
  }

  const {
    idea_input = "",
    competitor_analysis = {},
    trends_data = {},
    reddit_sentiment = {},
    final_verdict = {},
  } = data;

  const { overall_score = 0, summary = "No summary available.", confidence = 0 } =
    final_verdict;

  const cleanIdea = idea_input.replace(/^"+|"+$/g, "") || "No idea provided";

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 relative overflow-hidden py-20">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 -right-40 w-80 h-80 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-emerald-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-indigo-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
      </div>

      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-grid-pattern opacity-10 pointer-events-none"></div>

      <div className="max-w-7xl mx-auto px-8 mt-16 space-y-10 relative z-10">
        {/* Header Section */}
        <div className="text-center mb-12 animate-fade-in">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 mb-6">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium text-gray-200">Analysis Complete</span>
          </div>
          
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            <span className="bg-gradient-to-r from-emerald-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent">
              Your Startup
            </span>
            <br />
            <span className="text-white">Analysis Results</span>
          </h1>
        </div>

        {/* Score Overview Card */}
        <div className="relative group mb-12 animate-fade-in-up">
          <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 via-blue-500 to-indigo-500 rounded-2xl blur opacity-50 group-hover:opacity-75 transition duration-500"></div>
          <div className="relative bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-lg p-10 rounded-2xl border border-white/20 shadow-2xl">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="text-6xl font-bold bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent mb-2">
                  {overall_score}
                </div>
                <div className="text-gray-400 text-sm uppercase tracking-wider">Overall Score</div>
              </div>
              <div className="text-center border-l border-r border-white/10">
                <div className="text-6xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent mb-2">
                  {Math.round(confidence * 100)}%
                </div>
                <div className="text-gray-400 text-sm uppercase tracking-wider">Confidence</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-white mb-2">
                  {overall_score >= 75 ? "Strong Potential" : overall_score >= 50 ? "Moderate Potential" : "Needs Work"}
                </div>
                <div className="text-gray-400 text-sm uppercase tracking-wider">Verdict</div>
              </div>
            </div>
          </div>
        </div>

        {/* IDEA */}
        <ResultCard title="Submitted Idea">
          <p className="italic text-gray-300 text-lg">{cleanIdea}</p>
        </ResultCard>

        {/* FINAL VERDICT */}
        <ResultCard title="Final Verdict">
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="flex-shrink-0">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500 to-blue-500 flex items-center justify-center">
                  <span className="text-2xl font-bold text-white">{overall_score}</span>
                </div>
              </div>
              <div className="flex-1">
                <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-emerald-500 to-blue-500 rounded-full transition-all duration-1000"
                    style={{ width: `${overall_score}%` }}
                  ></div>
                </div>
              </div>
            </div>
            <p className="text-lg leading-relaxed">{summary}</p>
            <div className="flex items-center gap-2 text-sm">
              <div className="px-3 py-1 bg-emerald-500/20 border border-emerald-500/30 rounded-full text-emerald-400">
                Confidence: {Math.round(confidence * 100)}%
              </div>
            </div>
          </div>
        </ResultCard>

        {/* COMPETITOR ANALYSIS */}
        <ResultCard title="Competitor Analysis">
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-lg font-semibold">
              <div className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <span className="text-blue-400">{competitor_analysis.competitors_found || 0}</span>
              </div>
              <span>Competitors Found</span>
            </div>

            <div className="mt-6">
              <p className="font-medium text-white mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-emerald-400 rounded-full"></span>
                Direct Competitors
              </p>
              <ul className="space-y-2 ml-4">
                {competitor_analysis.direct_competitors?.length > 0
                  ? competitor_analysis.direct_competitors.map((c, i) => {
                      if (typeof c === "object") {
                        return (
                          <li key={i} className="bg-white/5 p-3 rounded-lg border border-white/10">
                            <strong className="text-emerald-400">{c.name}</strong>
                            <p className="text-sm text-gray-400 mt-1">{c.description}</p>
                            {c.url && (
                              <a href={c.url} target="_blank" className="text-blue-400 hover:text-blue-300 underline text-sm mt-1 inline-block">
                                Visit website →
                              </a>
                            )}
                          </li>
                        );
                      }
                      return <li key={i} className="bg-white/5 p-3 rounded-lg border border-white/10">{c}</li>;
                    })
                  : <li className="text-gray-400 italic">No direct competitors found</li>}
              </ul>
            </div>

            <div className="mt-6">
              <p className="font-medium text-white mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
                Indirect Competitors
              </p>
              <ul className="space-y-2 ml-4">
                {competitor_analysis.indirect_competitors?.length > 0
                  ? competitor_analysis.indirect_competitors.map((c, i) => (
                      <li key={i} className="bg-white/5 p-3 rounded-lg border border-white/10">
                        {typeof c === "object" ? c.name : c}
                      </li>
                    ))
                  : <li className="text-gray-400 italic">No indirect competitors found</li>}
              </ul>
            </div>

            <div className="mt-6">
              <p className="font-medium text-white mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-indigo-400 rounded-full"></span>
                Differentiation Opportunities
              </p>
              <ul className="space-y-2 ml-4">
                {competitor_analysis.differentiation_opportunities?.length > 0
                  ? competitor_analysis.differentiation_opportunities.map((d, i) => (
                      <li key={i} className="bg-gradient-to-r from-emerald-500/10 to-blue-500/10 p-3 rounded-lg border border-emerald-500/20">
                        {typeof d === "object" ? d.name : d}
                      </li>
                    ))
                  : <li className="text-gray-400 italic">No differentiation opportunities found</li>}
              </ul>
            </div>

            {competitor_analysis.market_structure?.type && (
              <div className="mt-6 bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-4">
                <p className="font-medium text-white">
                  Market Structure: <span className="text-indigo-400">{competitor_analysis.market_structure.type}</span>
                </p>
              </div>
            )}
          </div>
        </ResultCard>

        {/* MARKET TRENDS */}
        <ResultCard title="Market Trends">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white/5 p-6 rounded-xl border border-white/10">
              <div className="text-sm text-gray-400 mb-2">Trend Direction</div>
              <div className="text-2xl font-bold text-white">{trends_data.trend_direction || "N/A"}</div>
            </div>
            <div className="bg-white/5 p-6 rounded-xl border border-white/10">
              <div className="text-sm text-gray-400 mb-2">Interest Score</div>
              <div className="flex items-center gap-3">
                <div className="text-2xl font-bold text-white">{trends_data.interest_score || 0}/100</div>
                <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full"
                    style={{ width: `${trends_data.interest_score || 0}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </ResultCard>

        {/* REDDIT SENTIMENT */}
        <ResultCard title="Public Sentiment (Reddit)">
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white/5 p-4 rounded-xl border border-white/10 text-center">
                <div className="text-sm text-gray-400 mb-2">Overall Sentiment</div>
                <div className="text-xl font-semibold text-white">{reddit_sentiment.overall_sentiment || "N/A"}</div>
              </div>
              <div className="bg-white/5 p-4 rounded-xl border border-white/10 text-center">
                <div className="text-sm text-gray-400 mb-2">Sentiment Score</div>
                <div className="text-xl font-semibold text-white">{reddit_sentiment.sentiment_score || 0}/10</div>
              </div>
              <div className="bg-white/5 p-4 rounded-xl border border-white/10 text-center">
                <div className="text-sm text-gray-400 mb-2">Posts Analyzed</div>
                <div className="text-xl font-semibold text-white">{reddit_sentiment.total_posts_analyzed || 0}</div>
              </div>
            </div>

            <div>
              <p className="font-medium text-white mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-red-400 rounded-full"></span>
                Key Concerns
              </p>
              <ul className="space-y-2 ml-4">
                {reddit_sentiment.key_concerns?.length > 0
                  ? reddit_sentiment.key_concerns.map((k, i) => (
                      <li key={i} className="bg-red-500/10 border border-red-500/20 p-3 rounded-lg">
                        {typeof k === "object" ? k.name || JSON.stringify(k) : k}
                      </li>
                    ))
                  : <li className="text-gray-400 italic">No concerns found</li>}
              </ul>
            </div>

            <div>
              <p className="font-medium text-white mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                Key Praises
              </p>
              <ul className="space-y-2 ml-4">
                {reddit_sentiment.key_praises?.length > 0
                  ? reddit_sentiment.key_praises.map((k, i) => (
                      <li key={i} className="bg-green-500/10 border border-green-500/20 p-3 rounded-lg">
                        {typeof k === "object" ? k.name || JSON.stringify(k) : k}
                      </li>
                    ))
                  : <li className="text-gray-400 italic">No praises found</li>}
              </ul>
            </div>
          </div>
        </ResultCard>
      </div>

      <style jsx>{`
        @keyframes fade-in {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        @keyframes fade-in-up {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fade-in {
          animation: fade-in 0.6s ease-out;
        }

        .animate-fade-in-up {
          animation: fade-in-up 0.8s ease-out;
        }

        .bg-grid-pattern {
          background-image: 
            linear-gradient(to right, rgba(255, 255, 255, 0.1) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
          background-size: 50px 50px;
        }
      `}</style>
    </div>
  );
}