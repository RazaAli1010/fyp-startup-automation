"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { askChatCoFounder, getChatStatus, getToken } from "@/lib/api";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  timestamp: Date;
}

function IconSend() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
    </svg>
  );
}

function IconBot() {
  return (
    <svg className="h-5 w-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
    </svg>
  );
}

function IconUser() {
  return (
    <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
    </svg>
  );
}

function IconArrowLeft() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
    </svg>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-500/20">
        <IconBot />
      </div>
      <div className="rounded-2xl rounded-tl-sm bg-[#1e293b] px-4 py-3">
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-2 animate-bounce rounded-full bg-indigo-400" style={{ animationDelay: "0ms" }} />
          <div className="h-2 w-2 animate-bounce rounded-full bg-indigo-400" style={{ animationDelay: "150ms" }} />
          <div className="h-2 w-2 animate-bounce rounded-full bg-indigo-400" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  );
}

const SUGGESTED_QUESTIONS = [
  "What are the biggest risks for this idea?",
  "How should I approach go-to-market?",
  "What does the competitive landscape look like?",
  "What MVP type should I build first?",
  "Summarize the market opportunity.",
  "What are my key strengths?",
];

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const ideaId = params.ideaId as string;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [indexedAgents, setIndexedAgents] = useState<string[]>([]);
  const [statusLoading, setStatusLoading] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    if (!getToken()) router.push("/auth/login");
  }, [router]);

  useEffect(() => {
    let cancelled = false;
    async function fetchStatus() {
      try {
        const status = await getChatStatus(ideaId);
        if (cancelled) return;
        setIndexedAgents(status.indexed_agents);
        const agentList = status.indexed_agents.length > 0
          ? status.indexed_agents.map((a: string) => a.replace(/_/g, " ")).join(", ")
          : "none yet";
        const welcomeContent = status.ready
          ? `Welcome! I'm your AI Co-Founder. I have access to data from: **${agentList}**. Ask me anything about your startup idea — strategy, risks, market opportunity, or next steps.`
          : "Welcome! I don't have any agent data for this idea yet. Please run the **Idea Validation** agent first, then come back to chat.";
        setMessages([{
          id: "welcome",
          role: "assistant",
          content: welcomeContent,
          sources: [],
          timestamp: new Date(),
        }]);
      } catch {
        if (!cancelled) {
          setMessages([{
            id: "welcome",
            role: "assistant",
            content: "Welcome! Ask me anything about your startup idea.",
            sources: [],
            timestamp: new Date(),
          }]);
        }
      } finally {
        if (!cancelled) setStatusLoading(false);
      }
    }
    fetchStatus();
    return () => { cancelled = true; };
  }, [ideaId]);

  async function handleSend(questionOverride?: string) {
    const question = (questionOverride || input).trim();
    if (!question || isLoading) return;
    setInput("");

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await askChatCoFounder(ideaId, question);
      setIndexedAgents(res.indexed_agents);
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: res.answer,
        sources: res.sources,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const detail = err instanceof Error ? err.message : "Something went wrong";
      setMessages((prev) => [...prev, {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `Sorry, I encountered an error: ${detail}`,
        sources: [],
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function formatMessage(content: string) {
    return content.split("\n").map((line, i) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/g);
      return (
        <p key={i} className={line === "" ? "h-3" : ""}>
          {parts.map((part, j) => {
            if (part.startsWith("**") && part.endsWith("**")) {
              return <strong key={j} className="font-semibold text-slate-100">{part.slice(2, -2)}</strong>;
            }
            return <span key={j}>{part}</span>;
          })}
        </p>
      );
    });
  }

  const showSuggestions = messages.length <= 1 && !isLoading;

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col bg-[#0a0f1a]">
      {/* Header */}
      <div className="shrink-0 border-b border-white/[0.06] bg-[#0f172a]/80 px-4 py-3 backdrop-blur-sm">
        <div className="mx-auto flex max-w-4xl items-center gap-4">
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 text-sm text-slate-400 transition-colors hover:text-slate-200"
          >
            <IconArrowLeft />
            Dashboard
          </Link>
          <div className="h-5 w-px bg-white/10" />
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600">
              <IconBot />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-slate-100">AI Co-Founder</h1>
              <p className="text-xs text-slate-500">
                {indexedAgents.length > 0
                  ? `${indexedAgents.length} agent${indexedAgents.length > 1 ? "s" : ""} indexed`
                  : "No data yet"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {statusLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <div key={msg.id} className={`flex items-start gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                  {/* Avatar */}
                  <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                    msg.role === "assistant"
                      ? "bg-indigo-500/20"
                      : "bg-slate-700"
                  }`}>
                    {msg.role === "assistant" ? <IconBot /> : <IconUser />}
                  </div>

                  {/* Bubble */}
                  <div className={`max-w-[80%] space-y-2 ${msg.role === "user" ? "items-end" : ""}`}>
                    <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      msg.role === "assistant"
                        ? "rounded-tl-sm bg-[#1e293b] text-slate-300"
                        : "rounded-tr-sm bg-indigo-600 text-white"
                    }`}>
                      <div className="space-y-1.5">{formatMessage(msg.content)}</div>
                    </div>

                    {/* Sources */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 px-1">
                        {msg.sources.map((src, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-[10px] font-medium text-indigo-300"
                          >
                            {src}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isLoading && <TypingIndicator />}

              {/* Suggested questions */}
              {showSuggestions && (
                <div className="pt-4">
                  <p className="mb-3 text-xs font-medium uppercase tracking-wider text-slate-500">
                    Suggested questions
                  </p>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {SUGGESTED_QUESTIONS.map((q) => (
                      <button
                        key={q}
                        onClick={() => handleSend(q)}
                        className="rounded-xl border border-white/[0.06] bg-[#1e293b]/50 px-4 py-3 text-left text-sm text-slate-300 transition-all hover:border-indigo-500/30 hover:bg-[#1e293b] hover:text-slate-100"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      </div>

      {/* Input area */}
      <div className="shrink-0 border-t border-white/[0.06] bg-[#0f172a]/80 px-4 py-4 backdrop-blur-sm">
        <div className="mx-auto flex max-w-3xl items-end gap-3">
          <div className="relative flex-1">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask your AI Co-Founder..."
              rows={1}
              className="w-full resize-none rounded-xl border border-white/[0.08] bg-[#1e293b] px-4 py-3 pr-12 text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30"
              style={{ maxHeight: "120px" }}
              disabled={isLoading}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              className="absolute bottom-2 right-2 flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white transition-all hover:bg-indigo-500 disabled:opacity-30 disabled:hover:bg-indigo-600"
            >
              <IconSend />
            </button>
          </div>
        </div>
        <p className="mx-auto mt-2 max-w-3xl text-center text-[10px] text-slate-600">
          Responses are grounded in your agent outputs. Not financial or legal advice.
        </p>
      </div>
    </div>
  );
}
