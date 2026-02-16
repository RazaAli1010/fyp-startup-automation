"""Problem Intensity Agent.

Measures how painful the problem is that a startup aims to solve, using
Tavily (article search) and SerpAPI (Google search intent) ONLY.

Hard constraints
----------------
- NO Reddit
- NO Exa
- NO OpenAI / LLMs
- Queries MUST use user input fields
- Scoring MUST be deterministic and explainable

Rules
-----
- NO LLM calls
- NO text summarisation
- NO scoring / judging by AI
- Pure signal extraction + deterministic formula
"""

from __future__ import annotations

import asyncio
import os
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

import httpx

from ..models.idea import Idea
from ..schemas.problem_intensity_schema import ProblemIntensitySignals

# ---------------------------------------------------------------------------
# Tavily API configuration
# ---------------------------------------------------------------------------
_TAVILY_API_URL = "https://api.tavily.com/search"
_TAVILY_TIMEOUT = 15.0
_TAVILY_MAX_RESULTS = 5

# ---------------------------------------------------------------------------
# SerpAPI configuration
# ---------------------------------------------------------------------------
_SERPAPI_BASE_URL = "https://serpapi.com/search"
_SERPAPI_TIMEOUT = 10.0

# ---------------------------------------------------------------------------
# Pain / complaint keyword lexicons
# ---------------------------------------------------------------------------
_PAIN_KEYWORDS: frozenset[str] = frozenset({
    "manual", "slow", "inefficient", "error-prone", "expensive",
    "tedious", "cumbersome", "frustrating", "outdated", "broken",
    "complicated", "time-consuming", "unreliable", "costly",
    "difficult", "painful", "annoying", "clunky", "legacy",
})

_MANUAL_KEYWORDS: frozenset[str] = frozenset({
    "manual", "spreadsheet", "email-based", "human review",
    "paper-based", "handwritten", "excel", "copy-paste",
    "phone call", "fax", "pen and paper", "word document",
    "manual entry", "manual process", "data entry",
})

_COMPLAINT_PHRASES: list[str] = [
    "too slow", "too expensive", "takes too long", "waste of time",
    "hard to use", "not intuitive", "always breaks", "poor support",
    "no alternative", "stuck with", "forced to use", "hate using",
    "error prone", "constant errors", "unreliable",
]


# ===================================================================== #
#  API key helpers                                                        #
# ===================================================================== #

def _get_tavily_key() -> str:
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if not key:
        raise EnvironmentError("TAVILY_API_KEY not set")
    return key


def _get_serpapi_key() -> str:
    key = os.getenv("SERPAPI_KEY", "").strip()
    if not key:
        raise EnvironmentError("SERPAPI_KEY not set")
    return key


# ===================================================================== #
#  Query builders — MUST use user input fields                            #
# ===================================================================== #

def _build_tavily_queries(idea: Idea) -> List[str]:
    """Build pain-focused Tavily queries from user input fields.

    Required templates per spec:
      - Pain / Fix queries
      - Manual workflow queries
      - Inefficiency queries
      - Cost / friction queries
      - Alternatives queries
    """
    desc = (idea.one_line_description or "").strip()
    industry = (idea.industry or "").strip()
    customer = (idea.target_customer_type or "").strip()
    geo = (idea.geography or "").strip()
    name = (idea.startup_name or "").strip()

    # Infer the core problem / task from the description
    problem_phrase = desc if desc else f"{industry} workflow"
    # Use startup_name as a proxy for current_solution if available
    solution_ref = name if name else f"{industry} tools"

    queries: list[str] = []

    # 1. Pain / Fix queries
    queries.append(f"how to fix {problem_phrase} for {customer}")
    queries.append(f"{customer} problems with {industry}")

    # 2. Manual workflow queries
    queries.append(f"manual process for {problem_phrase} in {industry}")

    # 3. Inefficiency queries
    queries.append(f"problems with {solution_ref} in {industry}")
    if geo and geo.lower() not in ("global", "worldwide"):
        queries.append(f"{industry} inefficiencies in {geo}")

    # 4. Cost / friction queries
    queries.append(f"why {industry} is expensive or slow for {customer}")

    # 5. Alternatives queries
    queries.append(f"alternatives to {solution_ref}")

    print(f"🔥 [PROBLEM] Queries built from input fields:")
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q}")

    return queries


def _build_serpapi_queries(idea: Idea) -> Dict[str, List[str]]:
    """Build SerpAPI queries for problem intent measurement.

    Returns two lists:
      - "problem": problem-oriented queries
      - "general": baseline queries for computing ratios
    """
    desc = (idea.one_line_description or "").strip()
    industry = (idea.industry or "").strip()
    customer = (idea.target_customer_type or "").strip()
    name = (idea.startup_name or "").strip()

    problem_phrase = desc if desc else f"{industry} workflow"
    solution_ref = name if name else f"{industry} tools"

    problem_queries = [
        f"how to fix {problem_phrase}",
        f"alternatives to {solution_ref}",
        f"manual way to {problem_phrase}",
        f"{industry} pain points",
    ]

    general_queries = [
        f"{industry} software",
        f"{industry} market",
    ]

    return {"problem": problem_queries, "general": general_queries}


# ===================================================================== #
#  Tavily fetcher                                                         #
# ===================================================================== #

async def _search_tavily(api_key: str, query: str) -> List[Dict[str, Any]]:
    """Execute a single Tavily search (async). Returns result dicts or []."""
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": _TAVILY_MAX_RESULTS,
        "include_answer": False,
    }
    try:
        async with httpx.AsyncClient(timeout=_TAVILY_TIMEOUT) as client:
            response = await client.post(_TAVILY_API_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"🔍 [PROBLEM] Tavily: {len(results)} results for {query!r}")
            return results
        else:
            print(f"⚠️  [PROBLEM] Tavily HTTP {response.status_code} for {query!r}")
            return []
    except Exception as exc:
        print(f"❌ [PROBLEM] Tavily error for {query!r}: {exc}")
        return []


async def _fetch_tavily_evidence(api_key: str, queries: List[str]) -> List[Dict[str, Any]]:
    """Fetch all Tavily results across queries in parallel, deduplicated by URL."""
    tasks = [_search_tavily(api_key, q) for q in queries]
    query_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_results: list[dict] = []
    seen_urls: set[str] = set()

    for result in query_results:
        if isinstance(result, Exception):
            continue
        for r in result:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(r)

    print(f"📄 [PROBLEM] Total unique Tavily results: {len(all_results)}")
    return all_results


# ===================================================================== #
#  SerpAPI fetcher — Google search for intent ratios                      #
# ===================================================================== #

async def _serpapi_result_count(api_key: str, query: str) -> int:
    """Get total_results from a Google search via SerpAPI (async).

    Returns 0 on any failure.
    """
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": 1,  # We only need the result count, not actual results
    }
    try:
        async with httpx.AsyncClient(timeout=_SERPAPI_TIMEOUT) as client:
            response = await client.get(_SERPAPI_BASE_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            info = data.get("search_information", {})
            count = info.get("total_results", 0)
            print(f"🔎 [PROBLEM] SerpAPI: {count:,} results for {query!r}")
            return int(count)
        else:
            print(f"⚠️  [PROBLEM] SerpAPI HTTP {response.status_code} for {query!r}")
            return 0
    except Exception as exc:
        print(f"❌ [PROBLEM] SerpAPI error for {query!r}: {exc}")
        return 0


async def _compute_query_ratios(
    api_key: str,
    query_groups: Dict[str, List[str]],
) -> tuple[float, float, int]:
    """Compute problem_query_ratio, alternatives_query_ratio, and total queries.

    problem_query_ratio = avg(problem_counts) / (avg(problem_counts) + avg(general_counts))
    alternatives_query_ratio = alternatives_count / total_problem_count
    """
    problem_queries = query_groups.get("problem", [])
    general_queries = query_groups.get("general", [])

    # Run all SerpAPI queries in parallel
    all_queries = problem_queries + general_queries
    tasks = [_serpapi_result_count(api_key, q) for q in all_queries]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Split results back
    problem_counts: list[int] = []
    alternatives_count = 0
    total_problem_queries = 0

    for i, q in enumerate(problem_queries):
        result = all_results[i]
        count = result if isinstance(result, int) else 0
        problem_counts.append(count)
        total_problem_queries += 1
        if "alternative" in q.lower():
            alternatives_count = count

    general_counts: list[int] = []
    for i, q in enumerate(general_queries):
        result = all_results[len(problem_queries) + i]
        count = result if isinstance(result, int) else 0
        general_counts.append(count)

    avg_problem = statistics.mean(problem_counts) if problem_counts else 0
    avg_general = statistics.mean(general_counts) if general_counts else 0

    total = avg_problem + avg_general
    problem_ratio = avg_problem / total if total > 0 else 0.0
    # Clamp to [0, 1]
    problem_ratio = max(0.0, min(1.0, problem_ratio))

    # Alternatives ratio: alternatives result count relative to total problem results
    total_problem_results = sum(problem_counts)
    alt_ratio = alternatives_count / total_problem_results if total_problem_results > 0 else 0.0
    alt_ratio = max(0.0, min(1.0, alt_ratio))

    print(f"🔎 [PROBLEM] Problem query ratio: {problem_ratio:.2f}")
    print(f"🔎 [PROBLEM] Alternatives query ratio: {alt_ratio:.2f}")

    return problem_ratio, alt_ratio, total_problem_queries


# ===================================================================== #
#  Signal extraction from Tavily content                                  #
# ===================================================================== #

def _extract_pain_signals(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract structured pain signals from Tavily search results.

    Returns dict with: pain_articles_count, avg_recency_months,
    pain_keywords, complaint_density, top_complaints,
    manual_process_detected, manual_steps_count, time_waste_hours.
    """
    pain_article_count = 0
    complaint_passages = 0
    total_passages = 0
    all_text_tokens: Counter = Counter()
    complaint_phrase_counter: Counter = Counter()
    publication_months: list[float] = []
    manual_detected = False
    manual_keyword_hits = 0

    now = datetime.now(timezone.utc)

    for result in results:
        content = (result.get("content") or "").lower()
        title = (result.get("title") or "").lower()
        combined = f"{title} {content}"

        if not combined.strip():
            continue

        total_passages += 1

        # Check for pain keywords
        has_pain = any(kw in combined for kw in _PAIN_KEYWORDS)
        if has_pain:
            pain_article_count += 1

        # Check for complaint phrases
        has_complaint = False
        for phrase in _COMPLAINT_PHRASES:
            if phrase in combined:
                has_complaint = True
                complaint_phrase_counter[phrase] += 1

        if has_complaint:
            complaint_passages += 1

        # Check for manual process signals
        for mkw in _MANUAL_KEYWORDS:
            if mkw in combined:
                manual_detected = True
                manual_keyword_hits += 1

        # Extract tokens for keyword analysis
        tokens = re.findall(r"[a-z]{3,}", combined)
        all_text_tokens.update(tokens)

        # Try to extract publication date for recency
        pub_date = result.get("published_date") or result.get("publishedDate") or ""
        if pub_date:
            try:
                # Handle ISO format or common date strings
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                months_ago = (now - dt).days / 30.0
                publication_months.append(max(0.0, months_ago))
            except (ValueError, TypeError):
                pass

    # Compute averages
    avg_recency = statistics.mean(publication_months) if publication_months else 24.0  # default: 2 years old
    complaint_density = complaint_passages / total_passages if total_passages > 0 else 0.0

    # Top pain keywords (exclude very common words)
    common_exclude = {"the", "and", "for", "with", "that", "this", "from", "are", "was", "has",
                      "have", "not", "but", "can", "will", "been", "their", "about", "more",
                      "would", "which", "there", "what", "when", "your", "they", "each",
                      "how", "other", "into", "also", "its", "than", "most", "some", "our"}
    pain_kws = [
        word for word, count in all_text_tokens.most_common(50)
        if word in _PAIN_KEYWORDS and word not in common_exclude
    ][:10]

    # Top complaints
    top_complaints = [phrase for phrase, _ in complaint_phrase_counter.most_common(5)]

    # Manual steps estimation (conservative)
    manual_steps = 0
    time_waste = 0.0
    if manual_detected:
        # Conservative estimate based on keyword density
        manual_steps = min(manual_keyword_hits * 2, 15)  # Cap at 15 steps
        time_waste = min(manual_keyword_hits * 1.5, 20.0)  # Cap at 20 hrs/week

    return {
        "pain_articles_count": pain_article_count,
        "avg_recency_months": round(avg_recency, 1),
        "pain_keywords": pain_kws,
        "complaint_density": round(complaint_density, 4),
        "top_complaints": top_complaints,
        "manual_process_detected": manual_detected,
        "manual_steps_count": manual_steps,
        "estimated_time_waste_hours": round(time_waste, 1),
    }


# ===================================================================== #
#  Deterministic scoring — LOCKED formulas from spec                      #
# ===================================================================== #

def _compute_search_intent_score(problem_query_ratio: float) -> float:
    """Search Intent Score from problem_query_ratio.

    problem_query_ratio > 0.6 → 75
    0.4–0.6 → 60
    0.2–0.4 → 45
    < 0.2 → 30
    """
    if problem_query_ratio > 0.6:
        return 75.0
    elif problem_query_ratio >= 0.4:
        return 60.0
    elif problem_query_ratio >= 0.2:
        return 45.0
    else:
        return 30.0


def _compute_evidence_strength_score(
    pain_articles_count: int,
    avg_recency_months: float,
) -> float:
    """Evidence Strength Score from Tavily article quality.

    recent + multiple articles → 70
    few or old articles → 45
    none → 30
    """
    if pain_articles_count == 0:
        return 30.0
    elif pain_articles_count >= 3 and avg_recency_months <= 12:
        return 70.0
    elif pain_articles_count >= 2 or avg_recency_months <= 18:
        return 55.0
    else:
        return 45.0


def _compute_complaint_score(
    complaint_density: float,
    top_complaints_count: int,
) -> float:
    """Complaint Score from article/review complaint density.

    high repetition → 70
    some complaints → 55
    weak → 40
    none → 35
    """
    if complaint_density >= 0.5 and top_complaints_count >= 3:
        return 70.0
    elif complaint_density >= 0.25 or top_complaints_count >= 2:
        return 55.0
    elif complaint_density > 0 or top_complaints_count >= 1:
        return 40.0
    else:
        return 35.0


def _compute_manual_cost_score(
    manual_detected: bool,
    time_waste_hours: float,
) -> float:
    """Manual Cost Score.

    manual_process_detected = True:
        hours > 10 → 80
        5–10 → 65
        <5 → 50
    False → 30
    """
    if not manual_detected:
        return 30.0
    if time_waste_hours > 10:
        return 80.0
    elif time_waste_hours >= 5:
        return 65.0
    else:
        return 50.0


def _apply_guardrails(
    raw_score: float,
    *,
    search_intent_present: bool,
    evidence_present: bool,
    complaint_present: bool,
    manual_present: bool,
    manual_detected: bool,
    complaint_score: float,
) -> float:
    """Apply absolute guardrails per spec.

    - If < 2 signal categories present → cap at 55
    - If manual_process_detected=False AND complaint_score < 45 → cap at 60
    - If all signals missing → score = 35
    - Score NEVER 0, NEVER 100
    """
    categories_present = sum([
        search_intent_present,
        evidence_present,
        complaint_present,
        manual_present,
    ])

    # All missing → 35
    if categories_present == 0:
        print("📊 [PROBLEM] All signal categories missing → score = 35")
        return 35.0

    score = raw_score

    # < 2 categories → cap at 55
    if categories_present < 2:
        score = min(score, 55.0)
        print(f"📊 [PROBLEM] Only {categories_present} category present → capped at 55")

    # No manual + weak complaints → cap at 60
    if not manual_detected and complaint_score < 45:
        score = min(score, 60.0)
        print(f"📊 [PROBLEM] No manual process + weak complaints → capped at 60")

    # Never 0 or 100
    score = max(1.0, min(99.0, score))

    return round(score, 2)


def _determine_confidence(
    search_intent_present: bool,
    evidence_present: bool,
    complaint_present: bool,
    manual_present: bool,
) -> Literal["low", "medium", "high"]:
    """Confidence assignment per spec.

    HIGH: ≥ 3 signal categories present
    MEDIUM: 2 categories present
    LOW: 0–1 category present
    """
    count = sum([search_intent_present, evidence_present, complaint_present, manual_present])
    if count >= 3:
        return "high"
    elif count == 2:
        return "medium"
    else:
        return "low"


# ===================================================================== #
#  Public API                                                             #
# ===================================================================== #

async def fetch_problem_intensity_signals(idea: Idea) -> ProblemIntensitySignals:
    """Run the full Problem Intensity pipeline for a given Idea.

    Pipeline:
    1. Build Tavily queries from user input
    2. Fetch Tavily evidence
    3. Build SerpAPI queries from user input
    4. Compute search intent ratios via SerpAPI
    5. Extract pain signals from Tavily content
    6. Compute deterministic component scores
    7. Apply guardrails + confidence
    8. Return ProblemIntensitySignals

    Uses Tavily + SerpAPI ONLY. No Reddit, no Exa, no LLMs.
    """
    print("=" * 60)
    print(f"🔥 [PROBLEM] Problem Intensity Agent STARTED for: {idea.startup_name}")
    print(f"🔥 [PROBLEM] Industry: {idea.industry}, Customer: {idea.target_customer_type}")
    print("=" * 60)

    # ── 1. Tavily queries ─────────────────────────────────────────────
    tavily_queries = _build_tavily_queries(idea)

    # ── 1 & 2. Tavily + SerpAPI in parallel ─────────────────────
    serpapi_queries = _build_serpapi_queries(idea)

    # Prepare both tasks
    async def _tavily_task() -> list[dict]:
        try:
            tavily_key = _get_tavily_key()
            return await _fetch_tavily_evidence(tavily_key, tavily_queries)
        except EnvironmentError:
            print(" [PROBLEM] Tavily API key missing — skipping Tavily evidence")
            return []

    async def _serpapi_task() -> tuple[float, float, int]:
        try:
            serpapi_key = _get_serpapi_key()
            return await _compute_query_ratios(serpapi_key, serpapi_queries)
        except EnvironmentError:
            print(" [PROBLEM] SerpAPI key missing — skipping search intent")
            return (0.0, 0.0, 0)

    tavily_result, serpapi_result = await asyncio.gather(
        _tavily_task(),
        _serpapi_task(),
        return_exceptions=True,
    )

    tavily_results: list[dict] = tavily_result if isinstance(tavily_result, list) else []
    if isinstance(serpapi_result, tuple):
        problem_ratio, alt_ratio, total_problem_queries = serpapi_result
    else:
        problem_ratio = 0.0
        alt_ratio = 0.0
        total_problem_queries = 0

    # ── 3. Extract pain signals from Tavily content ───────────────────
    pain_signals = _extract_pain_signals(tavily_results)

    # ── 4. Compute component scores ───────────────────────────────────
    search_intent_score = _compute_search_intent_score(problem_ratio)
    evidence_strength_score = _compute_evidence_strength_score(
        pain_signals["pain_articles_count"],
        pain_signals["avg_recency_months"],
    )
    complaint_score = _compute_complaint_score(
        pain_signals["complaint_density"],
        len(pain_signals["top_complaints"]),
    )
    manual_cost_score = _compute_manual_cost_score(
        pain_signals["manual_process_detected"],
        pain_signals["estimated_time_waste_hours"],
    )

    print(f"📊 [PROBLEM] Search intent score: {search_intent_score}")
    print(f"📊 [PROBLEM] Evidence strength score: {evidence_strength_score}")
    print(f"📊 [PROBLEM] Complaint score: {complaint_score}")
    print(f"📊 [PROBLEM] Manual cost score: {manual_cost_score}")
    print(f"🛠️  [PROBLEM] Manual workflow detected: {pain_signals['manual_process_detected']}")

    # ── 5. Final composite score (LOCKED formula) ─────────────────────
    raw_score = (
        0.30 * search_intent_score
        + 0.25 * complaint_score
        + 0.25 * manual_cost_score
        + 0.20 * evidence_strength_score
    )

    # ── 6. Determine which signal categories are present ──────────────
    search_intent_present = total_problem_queries > 0 and problem_ratio > 0
    evidence_present = pain_signals["pain_articles_count"] > 0
    complaint_present = pain_signals["complaint_density"] > 0
    manual_present = pain_signals["manual_process_detected"]

    # ── 7. Apply guardrails ───────────────────────────────────────────
    final_score = _apply_guardrails(
        raw_score,
        search_intent_present=search_intent_present,
        evidence_present=evidence_present,
        complaint_present=complaint_present,
        manual_present=manual_present,
        manual_detected=pain_signals["manual_process_detected"],
        complaint_score=complaint_score,
    )

    # ── 8. Confidence ─────────────────────────────────────────────────
    confidence = _determine_confidence(
        search_intent_present, evidence_present, complaint_present, manual_present,
    )

    # ── 9. Build explanation ──────────────────────────────────────────
    parts = [
        f"Search intent: {search_intent_score:.0f} (ratio={problem_ratio:.2f})",
        f"Evidence: {evidence_strength_score:.0f} ({pain_signals['pain_articles_count']} articles, {pain_signals['avg_recency_months']:.0f}mo avg)",
        f"Complaints: {complaint_score:.0f} (density={pain_signals['complaint_density']:.2f})",
        f"Manual cost: {manual_cost_score:.0f} (detected={pain_signals['manual_process_detected']}, {pain_signals['estimated_time_waste_hours']:.1f}h/wk)",
    ]
    explanation = (
        f"Problem intensity = {final_score:.1f} (confidence={confidence}). "
        + " | ".join(parts)
    )

    print(f"📊 [PROBLEM] Final score: {final_score} (confidence={confidence})")
    print("=" * 60)

    return ProblemIntensitySignals(
        # Search intent
        total_problem_queries=total_problem_queries,
        problem_query_ratio=round(problem_ratio, 4),
        alternatives_query_ratio=round(alt_ratio, 4),
        # Evidence
        pain_articles_count=pain_signals["pain_articles_count"],
        avg_article_recency_months=pain_signals["avg_recency_months"],
        pain_keywords=pain_signals["pain_keywords"],
        # Complaints
        complaint_density=round(pain_signals["complaint_density"], 4),
        top_complaints=pain_signals["top_complaints"],
        # Manual
        manual_process_detected=pain_signals["manual_process_detected"],
        manual_steps_count=pain_signals["manual_steps_count"],
        estimated_time_waste_hours_per_week=pain_signals["estimated_time_waste_hours"],
        # Component scores
        search_intent_score=round(search_intent_score, 2),
        evidence_strength_score=round(evidence_strength_score, 2),
        complaint_score=round(complaint_score, 2),
        manual_cost_score=round(manual_cost_score, 2),
        # Final
        problem_intensity_score=final_score,
        confidence_level=confidence,
        explanation=explanation,
    )


def empty_problem_intensity_signals() -> ProblemIntensitySignals:
    """Return safe fallback signals when the agent fails entirely."""
    return ProblemIntensitySignals(
        total_problem_queries=0,
        problem_query_ratio=0.0,
        alternatives_query_ratio=0.0,
        pain_articles_count=0,
        avg_article_recency_months=24.0,
        pain_keywords=[],
        complaint_density=0.0,
        top_complaints=[],
        manual_process_detected=False,
        manual_steps_count=0,
        estimated_time_waste_hours_per_week=0.0,
        search_intent_score=30.0,
        evidence_strength_score=30.0,
        complaint_score=35.0,
        manual_cost_score=30.0,
        problem_intensity_score=35.0,
        confidence_level="low",
        explanation="No data available — all signals missing. Default score 35.",
    )
