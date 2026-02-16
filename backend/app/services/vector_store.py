"""Vector Store Service — ChromaDB persistent storage for RAG.

Handles:
  - ChromaDB client initialization (persistent mode)
  - Chunking agent outputs into 300-500 token semantic chunks
  - Indexing chunks with metadata (idea_id, agent, section)
  - Querying by idea_id with top-k retrieval

Storage: /app/vector_store (configurable via CHROMADB_PERSIST_DIR)
Embeddings: OpenAI text-embedding-3-large
"""

from __future__ import annotations

import os
import hashlib
import logging
from typing import Any, Dict, List, Optional

import chromadb
import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_PERSIST_DIR = os.getenv("CHROMADB_PERSIST_DIR", "./vector_store")
_COLLECTION_NAME = "startbot_agent_outputs"
_EMBEDDING_MODEL = "text-embedding-3-large"
_OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
_EMBEDDING_TIMEOUT = 15.0

# ---------------------------------------------------------------------------
# Singleton ChromaDB client
# ---------------------------------------------------------------------------
_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None


def _get_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise EnvironmentError("OPENAI_API_KEY not set")
    return key


def get_client() -> chromadb.ClientAPI:
    """Return the singleton ChromaDB persistent client."""
    global _client
    if _client is None:
        os.makedirs(_PERSIST_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=_PERSIST_DIR)
        print(f"🗄️  [VECTOR] ChromaDB initialized at {_PERSIST_DIR}")
    return _client


def get_collection() -> chromadb.Collection:
    """Return the singleton ChromaDB collection (creates if missing)."""
    global _collection
    if _collection is None:
        client = get_client()
        _collection = client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"🗄️  [VECTOR] Collection '{_COLLECTION_NAME}' ready (count={_collection.count()})")
    return _collection


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------

def _embed_texts(texts: List[str]) -> List[List[float]]:
    """Call OpenAI embeddings API and return vectors."""
    api_key = _get_openai_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _EMBEDDING_MODEL,
        "input": texts,
    }
    response = httpx.post(
        _OPENAI_EMBEDDINGS_URL,
        headers=headers,
        json=payload,
        timeout=_EMBEDDING_TIMEOUT,
    )
    if response.status_code != 200:
        logger.error("[VECTOR] Embedding API error: %s", response.text[:300])
        raise RuntimeError(f"Embedding API returned {response.status_code}")

    data = response.json()
    embeddings = [item["embedding"] for item in data["data"]]
    return embeddings


def embed_single(text: str) -> List[float]:
    """Embed a single text string."""
    return _embed_texts([text])[0]


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------

def _chunk_id(idea_id: str, agent: str, section: str) -> str:
    """Generate a deterministic chunk ID."""
    raw = f"{idea_id}:{agent}:{section}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _make_chunk(
    idea_id: str,
    agent: str,
    section: str,
    text: str,
) -> Dict[str, Any]:
    """Create a chunk dict with metadata."""
    return {
        "id": _chunk_id(idea_id, agent, section),
        "text": text.strip(),
        "metadata": {
            "idea_id": idea_id,
            "agent": agent,
            "section": section,
        },
    }


# ---------------------------------------------------------------------------
# Agent-specific chunkers
# ---------------------------------------------------------------------------

def chunk_evaluation(idea_id: str, report: dict) -> List[Dict[str, Any]]:
    """Chunk an evaluation report into semantic sections."""
    chunks = []
    scores = report.get("module_scores", {})
    summary = report.get("summary", {})
    normalized = report.get("normalized_signals", {})

    # Chunk 1: Overall verdict and scores
    verdict_text = (
        f"Idea Validation Result: "
        f"Final viability score is {scores.get('final_viability_score', 'N/A')}/100. "
        f"Verdict: {summary.get('verdict', 'N/A')}. "
        f"Risk level: {summary.get('risk_level', 'N/A')}. "
        f"Key strength: {summary.get('key_strength', 'N/A')}. "
        f"Key risk: {summary.get('key_risk', 'N/A')}."
    )
    chunks.append(_make_chunk(idea_id, "idea_validation", "verdict", verdict_text))

    # Chunk 2: Module scores breakdown
    scores_text = (
        f"Module Scores: "
        f"Problem Intensity: {scores.get('problem_intensity', 'N/A')}/100. "
        f"Market Timing: {scores.get('market_timing', 'N/A')}/100. "
        f"Competition Pressure: {scores.get('competition_pressure', 'N/A')}/100. "
        f"Market Potential: {scores.get('market_potential', 'N/A')}/100. "
        f"Execution Feasibility: {scores.get('execution_feasibility', 'N/A')}/100."
    )
    chunks.append(_make_chunk(idea_id, "idea_validation", "module_scores", scores_text))

    # Chunk 3: Competitors found
    competitors = report.get("competitor_names", [])
    if competitors:
        comp_text = (
            f"Competitors discovered during validation: {', '.join(competitors[:8])}. "
            f"Total competitors found: {len(competitors)}."
        )
        chunks.append(_make_chunk(idea_id, "idea_validation", "competitors", comp_text))

    return chunks


def chunk_market_research(idea_id: str, record: dict) -> List[Dict[str, Any]]:
    """Chunk a market research record into semantic sections."""
    chunks = []

    # Chunk 1: Market size (TAM/SAM/SOM)
    tam_min = record.get("tam_min", 0) or 0
    tam_max = record.get("tam_max", 0) or 0
    sam_min = record.get("sam_min", 0) or 0
    sam_max = record.get("sam_max", 0) or 0
    som_min = record.get("som_min", 0) or 0
    som_max = record.get("som_max", 0) or 0
    size_text = (
        f"Market Size Estimates: "
        f"TAM (Total Addressable Market): ${tam_min/1e9:.2f}B - ${tam_max/1e9:.2f}B. "
        f"SAM (Serviceable Addressable Market): ${sam_min/1e6:.1f}M - ${sam_max/1e6:.1f}M. "
        f"SOM (Serviceable Obtainable Market): ${som_min/1e6:.1f}M - ${som_max/1e6:.1f}M. "
        f"ARPU (Annual Revenue Per User): ${record.get('arpu_annual', 'N/A')}."
    )
    chunks.append(_make_chunk(idea_id, "market_research", "market_size", size_text))

    # Chunk 2: Growth and demand
    growth_text = (
        f"Market Growth and Demand: "
        f"Estimated growth rate: {record.get('growth_rate_estimate', 'N/A')}%. "
        f"Demand strength score: {record.get('demand_strength', 'N/A')}/100."
    )
    chunks.append(_make_chunk(idea_id, "market_research", "growth_demand", growth_text))

    # Chunk 3: Competition
    competitors = record.get("competitors", [])
    if competitors:
        comp_text = (
            f"Market Research Competitors: {', '.join(competitors[:8])}. "
            f"Total competitor count: {record.get('competitor_count', len(competitors))}."
        )
        chunks.append(_make_chunk(idea_id, "market_research", "competition", comp_text))

    # Chunk 4: Assumptions and confidence
    assumptions = record.get("assumptions")
    confidence = record.get("confidence")
    if assumptions or confidence:
        meta_text = "Market Research Metadata: "
        if assumptions:
            if isinstance(assumptions, list):
                meta_text += f"Assumptions: {'; '.join(str(a) for a in assumptions[:5])}. "
            elif isinstance(assumptions, dict):
                meta_text += f"Assumptions: {'; '.join(f'{k}: {v}' for k, v in list(assumptions.items())[:5])}. "
        if confidence:
            if isinstance(confidence, dict):
                meta_text += f"Confidence: {'; '.join(f'{k}: {v}' for k, v in confidence.items())}."
            else:
                meta_text += f"Confidence: {confidence}."
        chunks.append(_make_chunk(idea_id, "market_research", "assumptions", meta_text))

    return chunks


def chunk_mvp(idea_id: str, blueprint: dict) -> List[Dict[str, Any]]:
    """Chunk an MVP blueprint into semantic sections."""
    chunks = []

    # Chunk 1: MVP type and core hypothesis
    type_text = (
        f"MVP Blueprint: Type is '{blueprint.get('mvp_type', 'N/A')}'. "
        f"Core hypothesis: {blueprint.get('core_hypothesis', 'N/A')}. "
        f"Primary user: {blueprint.get('primary_user', 'N/A')}."
    )
    chunks.append(_make_chunk(idea_id, "mvp", "type_hypothesis", type_text))

    # Chunk 2: Core features
    features = blueprint.get("core_features", [])
    if features:
        feat_text = f"MVP Core Features: {'; '.join(str(f) for f in features[:6])}."
        chunks.append(_make_chunk(idea_id, "mvp", "features", feat_text))

    # Chunk 3: Tech stack
    tech = blueprint.get("recommended_tech_stack", {})
    if tech:
        if isinstance(tech, dict):
            tech_text = "Recommended Tech Stack: " + "; ".join(f"{k}: {v}" for k, v in tech.items())
        else:
            tech_text = f"Recommended Tech Stack: {tech}"
        chunks.append(_make_chunk(idea_id, "mvp", "tech_stack", tech_text))

    # Chunk 4: Build plan and validation
    build = blueprint.get("build_plan", [])
    validation = blueprint.get("validation_plan", [])
    if build or validation:
        plan_text = "MVP Roadmap: "
        if build:
            plan_text += f"Build plan: {'; '.join(str(p) for p in build[:5])}. "
        if validation:
            plan_text += f"Validation plan: {'; '.join(str(v) for v in validation[:5])}."
        chunks.append(_make_chunk(idea_id, "mvp", "roadmap", plan_text))

    # Chunk 5: Risk notes
    risks = blueprint.get("risk_notes", [])
    if risks:
        risk_text = f"MVP Risk Notes: {'; '.join(str(r) for r in risks[:5])}."
        chunks.append(_make_chunk(idea_id, "mvp", "risks", risk_text))

    return chunks


def chunk_pitch_deck(idea_id: str, deck: dict) -> List[Dict[str, Any]]:
    """Chunk a pitch deck record (executive summary only)."""
    chunks = []
    title = deck.get("title") or deck.get("deck_title", "Pitch Deck")
    view_url = deck.get("view_url", "")
    summary_text = (
        f"Pitch Deck: '{title}' generated via Alai Slides API. "
        f"Provider: {deck.get('provider', 'alai')}. "
        f"Status: {deck.get('status', 'unknown')}."
    )
    if view_url:
        summary_text += f" View URL: {view_url}."
    chunks.append(_make_chunk(idea_id, "pitch_deck", "summary", summary_text))
    return chunks


def chunk_legal(idea_id: str, doc: dict) -> List[Dict[str, Any]]:
    """Chunk a legal document (type + jurisdiction summary)."""
    chunks = []
    doc_type = doc.get("document_type", "unknown")
    jurisdiction = doc.get("jurisdiction", "N/A")
    governing_law = doc.get("governing_law", "N/A")

    summary_text = (
        f"Legal Document: {doc_type}. "
        f"Jurisdiction: {jurisdiction}. "
        f"Governing law: {governing_law}. "
        f"Disclaimer: {doc.get('disclaimer', 'N/A')}."
    )

    sections = doc.get("sections", [])
    if sections:
        section_titles = [s.get("title", "") for s in sections if isinstance(s, dict)]
        if section_titles:
            summary_text += f" Sections: {', '.join(section_titles)}."

    risk_notes = doc.get("legal_risk_notes", [])
    if risk_notes:
        summary_text += f" Risk notes: {'; '.join(str(r) for r in risk_notes[:3])}."

    chunks.append(_make_chunk(idea_id, f"legal_{doc_type}", "summary", summary_text))
    return chunks


# ---------------------------------------------------------------------------
# Index and delete operations
# ---------------------------------------------------------------------------

def index_chunks(chunks: List[Dict[str, Any]]) -> int:
    """Embed and upsert chunks into ChromaDB. Returns count indexed."""
    if not chunks:
        return 0

    collection = get_collection()
    texts = [c["text"] for c in chunks]
    ids = [c["id"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    try:
        embeddings = _embed_texts(texts)
    except Exception as exc:
        logger.error("[VECTOR] Embedding failed, skipping indexing: %s", exc)
        return 0

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"🗄️  [VECTOR] Indexed {len(chunks)} chunks")
    return len(chunks)


def query_by_idea(
    idea_id: str,
    query_embedding: List[float],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Query ChromaDB for chunks matching an idea_id, ranked by similarity."""
    collection = get_collection()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"idea_id": idea_id},
        include=["documents", "metadatas", "distances"],
    )

    items = []
    if results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
        dists = results["distances"][0] if results["distances"] else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, dists):
            items.append({
                "text": doc,
                "metadata": meta,
                "distance": dist,
            })

    return items


async def _embed_texts_async(texts: List[str]) -> List[List[float]]:
    """Async version of _embed_texts — non-blocking OpenAI embeddings call."""
    api_key = _get_openai_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _EMBEDDING_MODEL,
        "input": texts,
    }
    async with httpx.AsyncClient(timeout=_EMBEDDING_TIMEOUT) as client:
        response = await client.post(
            _OPENAI_EMBEDDINGS_URL,
            headers=headers,
            json=payload,
        )
    if response.status_code != 200:
        logger.error("[VECTOR] Embedding API error: %s", response.text[:300])
        raise RuntimeError(f"Embedding API returned {response.status_code}")

    data = response.json()
    embeddings = [item["embedding"] for item in data["data"]]
    return embeddings


async def embed_single_async(text: str) -> List[float]:
    """Async version of embed_single."""
    result = await _embed_texts_async([text])
    return result[0]


async def index_chunks_async(chunks: List[Dict[str, Any]]) -> int:
    """Async version of index_chunks — embed via async, upsert into ChromaDB."""
    if not chunks:
        return 0

    collection = get_collection()
    texts = [c["text"] for c in chunks]
    ids = [c["id"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    try:
        embeddings = await _embed_texts_async(texts)
    except Exception as exc:
        logger.error("[VECTOR] Embedding failed, skipping indexing: %s", exc)
        return 0

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"🗄️  [VECTOR] Indexed {len(chunks)} chunks (async)")
    return len(chunks)


def get_indexed_agents(idea_id: str) -> List[str]:
    """Return list of agent names that have indexed data for this idea."""
    collection = get_collection()
    try:
        results = collection.get(
            where={"idea_id": idea_id},
            include=["metadatas"],
        )
        if results and results["metadatas"]:
            agents = set()
            for meta in results["metadatas"]:
                agent = meta.get("agent", "")
                # Normalize legal_* to "legal"
                if agent.startswith("legal_"):
                    agent = "legal"
                agents.add(agent)
            return sorted(agents)
    except Exception:
        pass
    return []
