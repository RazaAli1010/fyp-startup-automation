"""Idea Evaluation Pipeline Route.

Orchestrates all services in the correct order and returns a structured
evaluation report.  The route is thin — all business logic lives in
service functions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.idea import Idea
from ..models.user import User
from ..services.auth_dependency import get_current_user
from ..schemas.evaluation_schema import IdeaEvaluationReport
from ..schemas.normalized_schema import NormalizedSignals
from ..schemas.score_schema import ModuleScores
from ..schemas.problem_intensity_schema import ProblemIntensitySignals
from ..schemas.trend_schema import TrendDemandSignals
from ..schemas.competitor_schema import CompetitorSignals
from ..services.query_builder import build_query_bundle
from ..services.problem_intensity_agent import fetch_problem_intensity_signals, empty_problem_intensity_signals
from ..services.trend_agent import fetch_trend_demand_signals
from ..services.competitor_agent import fetch_competitor_signals
from ..services.normalization_engine import normalize_signals
from ..services.scoring_engine import compute_scores
from ..services.vector_store import chunk_evaluation, index_chunks_async
from ..services.idea_inference import (
    infer_idea_attributes,
    map_complexity_to_numeric,
    map_regulatory_to_numeric,
    map_revenue_model_to_pricing,
    normalize_revenue_model,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ideas",
    tags=["Evaluation"],
)


# ===================================================================== #
#  Rule-based summary generation                                          #
# ===================================================================== #

def _generate_summary(scores: ModuleScores) -> dict[str, str]:
    """Produce a rule-based summary dict from module scores.  No LLM."""

    # --- verdict ---
    final = scores.final_viability_score
    if final >= 75:
        verdict = "Strong"
    elif final >= 55:
        verdict = "Moderate"
    else:
        verdict = "Weak"

    # --- risk_level ---
    if scores.competition_pressure < 40 or scores.execution_feasibility < 30:
        risk_level = "High"
    elif scores.competition_pressure < 60 or scores.execution_feasibility < 50:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    # --- key_strength (highest scoring module) ---
    module_map: dict[str, float] = {
        "Problem Intensity": scores.problem_intensity,
        "Market Timing": scores.market_timing,
        "Competition Pressure": scores.competition_pressure,
        "Market Potential": scores.market_potential,
        "Execution Feasibility": scores.execution_feasibility,
    }
    key_strength = max(module_map, key=module_map.get)  # type: ignore[arg-type]

    # --- key_risk (lowest scoring module) ---
    key_risk = min(module_map, key=module_map.get)  # type: ignore[arg-type]

    return {
        "verdict": verdict,
        "risk_level": risk_level,
        "key_strength": key_strength,
        "key_risk": key_risk,
    }


# ===================================================================== #
#  Graceful-degradation defaults                                          #
# ===================================================================== #

def _empty_problem() -> ProblemIntensitySignals:
    return empty_problem_intensity_signals()


def _empty_trend() -> TrendDemandSignals:
    return TrendDemandSignals(
        avg_search_volume=0.0,
        growth_rate_5y=0.0,
        momentum_score=0.0,
        volatility_index=0.0,
        demand_strength_score=0.0,
        trend_data_available=False,
        trend_data_source_tier=None,
    )


def _empty_competitor() -> CompetitorSignals:
    return CompetitorSignals(
        total_competitors=0,
        competitor_names=[],
        avg_company_age=0.0,
        competitor_density_score=0.0,
        feature_overlap_score=0.0,
    )


# ===================================================================== #
#  Pipeline route                                                         #
# ===================================================================== #

@router.post(
    "/{idea_id}/evaluate",
    response_model=IdeaEvaluationReport,
    summary="Evaluate a Startup Idea",
    response_description="Full deterministic evaluation report",
)
async def evaluate_idea(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IdeaEvaluationReport:
    """Run the end-to-end evaluation pipeline for a stored idea.

    Pipeline order:
    1. Fetch Idea from DB
    2. Build QueryBundle
    3. Fetch ProblemIntensitySignals (Tavily + SerpAPI, no Reddit)
    4. Fetch TrendDemandSignals
    5. Fetch CompetitorSignals
    6. Normalize → NormalizedSignals
    7. Score → ModuleScores
    8. Generate summary → return report
    """

    print(f"➡️  [EVALUATION] Pipeline START for idea {idea_id}")

    # ── 1. Fetch Idea ────────────────────────────────────────────────
    logger.info("Pipeline step 1: Fetching idea %s", idea_id)
    idea = db.query(Idea).filter(Idea.id == str(idea_id)).first()
    if idea is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Idea {idea_id} not found",
        )

    try:
        # ── 2. OpenAI Inference — infer attributes from description ────
        logger.info("Pipeline step 2: Inferring idea attributes via OpenAI")
        print("🧠 [EVALUATION] Step 2: OpenAI structured inference")
        inferred = await infer_idea_attributes(
            description=idea.one_line_description,
            industry=idea.industry,
            target_customer_type=idea.target_customer_type,
        )

        # Map inferred levels to numeric values
        raw_rev_model = inferred.get("revenue_model", "Subscription")
        norm_rev_model = normalize_revenue_model(raw_rev_model)
        tech_level = inferred.get("technical_complexity_level", "medium")
        reg_level = inferred.get("regulatory_risk_level", "medium")
        tech_numeric = map_complexity_to_numeric(tech_level)
        reg_numeric = map_regulatory_to_numeric(reg_level)
        pricing = map_revenue_model_to_pricing(norm_rev_model)

        # Persist inferred values to Idea model
        idea.revenue_model = norm_rev_model
        idea.pricing_estimate = pricing
        idea.tech_complexity = tech_numeric
        idea.regulatory_risk = reg_numeric
        idea.inferred_revenue_model = raw_rev_model
        idea.inferred_tech_level = tech_level
        idea.inferred_reg_level = reg_level
        idea.inferred_problem_keywords = ",".join(inferred.get("core_problem_keywords", []))
        idea.inferred_market_keywords = ",".join(inferred.get("market_keywords", []))
        db.commit()
        db.refresh(idea)
        print(f"✅ [EVALUATION] Inferred: rev={norm_rev_model}, tech={tech_level}→{tech_numeric}, reg={reg_level}→{reg_numeric}")

        # ── 3. Build QueryBundle ─────────────────────────────────────────
        logger.info("Pipeline step 3: Building query bundle")
        query_bundle = build_query_bundle(idea)

        # ── 4-6. Fetch all signals IN PARALLEL ────────────────────────
        logger.info("Pipeline steps 4-6: Fetching all signals in parallel")
        t_start = time.perf_counter()

        problem_task = fetch_problem_intensity_signals(idea)
        trend_task = fetch_trend_demand_signals(query_bundle)
        competitor_task = fetch_competitor_signals(query_bundle)

        results = await asyncio.gather(
            problem_task, trend_task, competitor_task,
            return_exceptions=True,
        )

        elapsed_parallel = time.perf_counter() - t_start
        logger.info("[EVALUATION] Parallel fetch completed in %.2fs", elapsed_parallel)

        problem_signals = results[0] if not isinstance(results[0], Exception) else _empty_problem()
        trend_signals = results[1] if not isinstance(results[1], Exception) else _empty_trend()
        competitor_signals = results[2] if not isinstance(results[2], Exception) else _empty_competitor()

        if isinstance(results[0], Exception):
            logger.warning("Problem intensity agent failed: %s — using empty signals", results[0])
        if isinstance(results[1], Exception):
            logger.warning("Trend agent failed: %s — using empty signals", results[1])
        if isinstance(results[2], Exception):
            logger.warning("Competitor agent failed: %s — using empty signals", results[2])

        # ── 6. Normalize ─────────────────────────────────────────────────────
        logger.info("Pipeline step 6: Normalizing signals")
        normalized = normalize_signals(
            problem=problem_signals,
            trend=trend_signals,
            competitor=competitor_signals,
            idea=idea,
        )

        # ── 7. Score ─────────────────────────────────────────────────────
        logger.info("Pipeline step 7: Computing scores")
        scores = compute_scores(normalized)

        # ── 8. Summary ───────────────────────────────────────────────────
        logger.info("Pipeline step 8: Generating summary")
        summary = _generate_summary(scores)

        # ── 9. Build report object ────────────────────────────────────
        report = IdeaEvaluationReport(
            idea_id=str(idea_id),
            normalized_signals=normalized,
            module_scores=scores,
            competitor_names=competitor_signals.competitor_names,
            trend_data_available=trend_signals.trend_data_available,
            trend_data_source_tier=trend_signals.trend_data_source_tier,
            summary=summary,
        )

        # ── 10. Persist final score + full report to Idea row ────────
        idea.final_viability_score = scores.final_viability_score
        idea.evaluation_report_json = json.dumps(report.model_dump(), default=str)
        db.commit()
        logger.info("Pipeline step 10: Persisted score=%.2f + report JSON to idea %s", scores.final_viability_score, idea_id)

    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ [EVALUATION] Pipeline CRASHED for idea {idea_id}: {exc}")
        logger.exception("Evaluation pipeline failed for idea %s", idea_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {exc}",
        ) from exc

    # ── 11. Index evaluation data for RAG chat ─────────────────
    try:
        chunks = chunk_evaluation(str(idea_id), report.model_dump())
        await index_chunks_async(chunks)
    except Exception as exc:
        logger.warning("Vector indexing failed (non-blocking): %s", exc)

    print(f"✅ [EVALUATION] Completed — returning final report to frontend (score={scores.final_viability_score:.1f}, verdict={summary['verdict']})")
    return report


# ===================================================================== #
#  GET stored evaluation (NEVER re-runs pipeline)                         #
# ===================================================================== #

@router.get(
    "/{idea_id}/evaluation",
    response_model=IdeaEvaluationReport,
    summary="Get stored evaluation report",
    response_description="Previously computed evaluation report from DB",
)
def get_evaluation(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IdeaEvaluationReport:
    """Return the stored evaluation report for an idea. NEVER re-runs the pipeline."""
    idea = db.query(Idea).filter(Idea.id == str(idea_id)).first()
    if idea is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Idea {idea_id} not found",
        )

    if not idea.evaluation_report_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Idea {idea_id} has not been evaluated yet",
        )

    try:
        report_data = json.loads(idea.evaluation_report_json)
        report = IdeaEvaluationReport(**report_data)
    except Exception as exc:
        logger.error("Failed to parse stored evaluation for idea %s: %s", idea_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored evaluation report is corrupted",
        ) from exc

    print(f"📊 [IDEA] Loaded stored evaluation for idea {idea_id} (score={report.module_scores.final_viability_score:.1f})")
    return report
