"""AI Chat Co-Founder Service — RAG-powered conversational agent.

Flow:
  1. Embed user question via OpenAI text-embedding-3-large
  2. Query ChromaDB filtered by idea_id (top_k=5)
  3. Build context from retrieved chunks
  4. Call GPT-4.1 with context-only guardrails (no JSON mode)
  5. Return answer + source labels

LLM Config:
  - model: gpt-4.1
  - temperature: 0.6
  - max_tokens: 900
  - NO json mode, NO tools, NO browsing
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import httpx

from .vector_store import embed_single, embed_single_async, query_by_idea, get_indexed_agents

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
_CHAT_MODEL = "gpt-4.1"
_CHAT_TEMPERATURE = 0.6
_CHAT_MAX_TOKENS = 900
_CHAT_TIMEOUT = 40.0
_TOP_K = 5

_SYSTEM_PROMPT = (
    "You are the AI Co-Founder for a startup idea validation platform called StartBot. "
    "You have access to validated agent outputs including idea evaluation scores, "
    "market research data, MVP blueprints, pitch deck summaries, and legal documents. "
    "Answer the user's question strictly using the provided context below. "
    "Be specific, cite numbers and scores when available, and give actionable advice. "
    "If the context does not contain enough information to answer, clearly state what "
    "data is missing and suggest which agent the user should run to get that information. "
    "Do not make up data. Do not hallucinate numbers or facts."
)

# ---------------------------------------------------------------------------
# Agent label mapping for human-readable sources
# ---------------------------------------------------------------------------
_AGENT_LABELS = {
    "idea_validation": "Idea Validation",
    "market_research": "Market Research",
    "mvp": "MVP Blueprint",
    "pitch_deck": "Pitch Deck",
}


def _source_label(meta: Dict[str, Any]) -> str:
    """Build a human-readable source label from chunk metadata."""
    agent = meta.get("agent", "unknown")
    section = meta.get("section", "")
    # Normalize legal_* agents
    if agent.startswith("legal_"):
        doc_type = agent.replace("legal_", "").replace("_", " ").title()
        label = f"Legal: {doc_type}"
    else:
        label = _AGENT_LABELS.get(agent, agent.replace("_", " ").title())
    if section:
        label += f": {section.replace('_', ' ').title()}"
    return label


def _get_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise EnvironmentError("OPENAI_API_KEY not set")
    return key


# ---------------------------------------------------------------------------
# Main chat function
# ---------------------------------------------------------------------------

async def ask_co_founder(
    idea_id: str,
    question: str,
) -> Dict[str, Any]:
    """Process a user question using RAG and return answer + sources (async).

    Returns:
        {
            "answer": str,
            "sources": list[str],
            "indexed_agents": list[str],
        }
    """
    # 1. Check what data is available
    indexed = get_indexed_agents(idea_id)
    if not indexed:
        return {
            "answer": (
                "I don't have any data for this idea yet. "
                "Please run the Idea Validation agent first to generate evaluation data, "
                "then I can answer questions about your startup idea."
            ),
            "sources": [],
            "indexed_agents": [],
        }

    # 2. Embed the question (async)
    try:
        query_embedding = await embed_single_async(question)
    except Exception as exc:
        logger.error("[CHAT] Failed to embed question: %s", exc)
        return {
            "answer": "Sorry, I encountered an error processing your question. Please try again.",
            "sources": [],
            "indexed_agents": indexed,
        }

    # 3. Retrieve relevant chunks
    results = query_by_idea(idea_id, query_embedding, top_k=_TOP_K)

    if not results:
        return {
            "answer": (
                "I found no relevant data for your question. "
                f"Currently indexed agents: {', '.join(indexed)}. "
                "Try running more agents to unlock deeper insights."
            ),
            "sources": [],
            "indexed_agents": indexed,
        }

    # 4. Build context string
    context_parts = []
    sources = []
    seen_sources = set()
    for item in results:
        context_parts.append(item["text"])
        label = _source_label(item["metadata"])
        if label not in seen_sources:
            sources.append(label)
            seen_sources.add(label)

    context_text = "\n\n---\n\n".join(context_parts)

    # 5. Build messages for LLM
    user_message = (
        f"## Context (from StartBot agent outputs)\n\n"
        f"{context_text}\n\n"
        f"---\n\n"
        f"## User Question\n\n"
        f"{question}"
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # 6. Call LLM (async, no JSON mode, plain text response)
    api_key = _get_openai_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _CHAT_MODEL,
        "messages": messages,
        "max_tokens": _CHAT_MAX_TOKENS,
        "temperature": _CHAT_TEMPERATURE,
    }

    try:
        print(f"💬 [CHAT] Calling {_CHAT_MODEL} for idea {idea_id[:8]}...")
        async with httpx.AsyncClient(timeout=_CHAT_TIMEOUT) as client:
            response = await client.post(
                _OPENAI_CHAT_URL,
                headers=headers,
                json=payload,
            )

        if response.status_code != 200:
            logger.error("[CHAT] LLM error %d: %s", response.status_code, response.text[:300])
            return {
                "answer": "Sorry, I encountered an error generating a response. Please try again.",
                "sources": sources,
                "indexed_agents": indexed,
            }

        data = response.json()
        answer = (data["choices"][0]["message"]["content"] or "").strip()

        usage = data.get("usage", {})
        print(f"💬 [CHAT] Response: {len(answer)} chars, tokens={usage.get('total_tokens', '?')}")

        return {
            "answer": answer,
            "sources": sources,
            "indexed_agents": indexed,
        }

    except httpx.TimeoutException:
        logger.error("[CHAT] LLM request timed out")
        return {
            "answer": "The request timed out. Please try a shorter question.",
            "sources": sources,
            "indexed_agents": indexed,
        }
    except Exception as exc:
        logger.error("[CHAT] Unexpected error: %s", exc)
        return {
            "answer": "An unexpected error occurred. Please try again.",
            "sources": [],
            "indexed_agents": indexed,
        }
