"""Shared Exa query builder — exactly 5 high-signal competitor queries.

Used by BOTH:
  - Idea Validation Agent (competitor_agent.py)
  - Market Research Agent (competitors.py)

LOCKED QUERY SET — no additions, no per-agent customization.
TOTAL EXA QUERIES = 5 — no more, no less.
"""

from __future__ import annotations

from typing import List


def build_exa_queries(
    *,
    one_line_description: str,
    industry: str,
    target_customer_type: str = "",
    revenue_model: str = "",
    current_solution: str = "",
) -> List[str]:
    """Build exactly 5 Exa competitor discovery queries (LOCKED).

    Parameters
    ----------
    one_line_description : str
        The startup's one-line description (verbatim from idea).
    industry : str
        The industry vertical (e.g. "Fintech", "Healthtech").
    target_customer_type : str
        Target customer segment (e.g. "Freelancers", "SMBs").
    revenue_model : str
        Revenue model (e.g. "Subscription", "Marketplace Fee").
    current_solution : str
        Known current solution / alternative. Falls back to description
        tokens if empty.

    Returns
    -------
    list[str]
        Exactly 5 query strings.
    """
    desc = (one_line_description or "").strip()
    ind = (industry or "").strip()
    cust = (target_customer_type or "").strip()
    rev = (revenue_model or "").strip()
    sol = (current_solution or "").strip()

    # Derive current_solution fallback from description tokens
    if not sol:
        tokens = [t for t in desc.lower().split() if len(t) > 2]
        sol = " ".join(tokens[:3]) if tokens else ind

    # Query 1: Companies working on similar idea {one_line_description}
    q1 = f"Companies working on similar idea {desc}" if desc else f"Companies in {ind}"

    # Query 2: Big companies in {industry}
    q2 = f"Big companies in {ind}" if ind else f"Big companies in {desc[:50]}"

    # Query 3: {industry} startups for {target_customer_type}
    q3 = f"{ind} startups for {cust}" if (ind and cust) else f"Startups in {ind or desc[:40]}"

    # Query 4: {revenue_model} platforms in {industry}
    q4 = f"{rev} platforms in {ind}" if (rev and ind) else f"Platforms in {ind or desc[:40]}"

    # Query 5: {current_solution} competitors
    q5 = f"{sol} competitors"

    queries = [q1, q2, q3, q4, q5]

    print(f"🔎 [EXA] Running 5 competitor queries")
    for i, q in enumerate(queries, 1):
        print(f"🔎 [EXA] Query {i}/5: {q}")

    return queries
