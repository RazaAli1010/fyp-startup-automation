"""Pitch Deck routes — generate and retrieve investor-ready pitch decks.

The generator is downstream of the Idea Validation Agent.  It does NOT
judge ideas; it translates validated signals into an investor narrative.

Endpoints:
  POST /pitch-deck/generate      — Generate a new pitch deck
  GET  /pitch-deck                — List all pitch decks for current user
  GET  /pitch-deck/idea/{idea_id} — Get pitch deck for a specific idea
  GET  /pitch-deck/{pitch_deck_id} — Get a single pitch deck by its ID
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..agents.pitch_deck_agent.generator import generate_pitch_deck
from ..services.alai_client import AlaiError
from ..database import get_db
from ..models.idea import Idea
from ..models.pitch_deck import PitchDeck
from ..models.user import User
from ..schemas.pitch_deck_schema import PitchDeckRecord, PitchDeckListResponse
from ..schemas.score_schema import ModuleScores
from ..schemas.problem_intensity_schema import ProblemIntensitySignals
from ..schemas.trend_schema import TrendDemandSignals
from ..schemas.competitor_schema import CompetitorSignals
from ..services.auth_dependency import get_current_user
from ..services.query_builder import build_query_bundle
from ..services.problem_intensity_agent import fetch_problem_intensity_signals, empty_problem_intensity_signals
from ..services.trend_agent import fetch_trend_demand_signals
from ..services.competitor_agent import fetch_competitor_signals
from ..services.normalization_engine import normalize_signals
from ..services.scoring_engine import compute_scores
from ..services.vector_store import chunk_pitch_deck, index_chunks_async

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pitch-deck",
    tags=["Pitch Deck"],
)


# ── Helpers ──────────────────────────────────────────────────────────────

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


async def _run_evaluation(idea: Idea) -> tuple[ModuleScores, dict[str, str]]:
    """Run the full evaluation pipeline with parallel signal fetching."""
    query_bundle = build_query_bundle(idea)

    t_start = time.perf_counter()
    results = await asyncio.gather(
        fetch_problem_intensity_signals(idea),
        fetch_trend_demand_signals(query_bundle),
        fetch_competitor_signals(query_bundle),
        return_exceptions=True,
    )
    elapsed = time.perf_counter() - t_start
    logger.info("[PITCH-DECK] Parallel eval fetch completed in %.2fs", elapsed)

    problem_signals = results[0] if not isinstance(results[0], Exception) else _empty_problem()
    trend_signals = results[1] if not isinstance(results[1], Exception) else _empty_trend()
    competitor_signals = results[2] if not isinstance(results[2], Exception) else _empty_competitor()

    if isinstance(results[0], Exception):
        logger.warning("Problem intensity agent failed: %s — using empty signals", results[0])
    if isinstance(results[1], Exception):
        logger.warning("Trend agent failed: %s — using empty signals", results[1])
    if isinstance(results[2], Exception):
        logger.warning("Competitor agent failed: %s — using empty signals", results[2])

    normalized = normalize_signals(
        problem=problem_signals,
        trend=trend_signals,
        competitor=competitor_signals,
        idea=idea,
    )
    scores = compute_scores(normalized)

    final = scores.final_viability_score
    if final >= 75:
        verdict = "Strong"
    elif final >= 55:
        verdict = "Moderate"
    else:
        verdict = "Weak"

    if scores.competition_pressure < 40 or scores.execution_feasibility < 30:
        risk_level = "High"
    elif scores.competition_pressure < 60 or scores.execution_feasibility < 50:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    module_map = {
        "Problem Intensity": scores.problem_intensity,
        "Market Timing": scores.market_timing,
        "Competition Pressure": scores.competition_pressure,
        "Market Potential": scores.market_potential,
        "Execution Feasibility": scores.execution_feasibility,
    }
    key_strength = max(module_map, key=module_map.get)  # type: ignore[arg-type]
    key_risk = min(module_map, key=module_map.get)  # type: ignore[arg-type]

    summary = {
        "verdict": verdict,
        "risk_level": risk_level,
        "key_strength": key_strength,
        "key_risk": key_risk,
    }

    return scores, summary


def _record_to_response(record: PitchDeck) -> PitchDeckRecord:
    """Convert a PitchDeck ORM instance to a PitchDeckRecord response."""
    return PitchDeckRecord(
        id=str(record.id),
        idea_id=str(record.idea_id),
        title=record.title or "Pitch Deck",
        status=record.status or "pending",
        provider=record.provider or "alai",
        generation_id=record.generation_id,
        view_url=record.view_url,
        pdf_url=record.pdf_url,
        created_at=record.created_at or datetime.utcnow(),
    )


# ── Routes ───────────────────────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=PitchDeckRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a Pitch Deck",
    response_description="Pitch deck record with status and URLs",
)
async def generate_deck(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PitchDeckRecord:
    """Generate a pitch deck for a validated idea.

    1. Creates a DB record with status=pending
    2. Runs evaluation pipeline
    3. Calls Alai Slides API (polls until complete)
    4. Updates DB record to completed with URLs
    5. Returns the full PitchDeckRecord
    """
    print(f"➡️  [PITCH-DECK] Generation START for idea {idea_id}")

    # 1. Fetch idea
    idea = db.query(Idea).filter(Idea.id == str(idea_id)).first()
    if idea is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Idea {idea_id} not found",
        )

    # 2. Upsert DB record as "pending"
    existing = db.query(PitchDeck).filter(PitchDeck.idea_id == str(idea_id)).first()
    if existing:
        existing.title = idea.startup_name
        existing.status = "pending"
        existing.generation_id = None
        existing.view_url = None
        existing.pdf_url = None
        existing.deck_json = None
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        db_record = existing
        print(f"📝 [PITCH-DECK] Reset existing record to pending (id={db_record.id})")
    else:
        db_record = PitchDeck(
            user_id=str(current_user.id),
            idea_id=str(idea_id),
            title=idea.startup_name,
            status="pending",
            provider="alai",
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        print(f"📝 [PITCH-DECK] Created pending record (id={db_record.id})")

    # 3. Run evaluation pipeline
    print(f"🔄 [PITCH-DECK] Running evaluation pipeline for idea {idea_id}")
    try:
        scores, summary = await _run_evaluation(idea)
        print(f"✅ [PITCH-DECK] Evaluation complete — score={scores.final_viability_score:.1f}")
    except Exception as exc:
        print(f"❌ [PITCH-DECK] Evaluation pipeline FAILED: {exc}")
        db_record.status = "failed"
        db_record.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_record)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation pipeline failed: {exc}",
        ) from exc

    # 4. Generate pitch deck via Alai API
    print(f"🚀 [PITCH-DECK] Calling Alai Slides API")
    try:
        deck = await generate_pitch_deck(
            idea_name=idea.startup_name,
            idea_description=idea.one_line_description,
            idea_industry=idea.industry,
            idea_target_customer=idea.target_customer_type,
            idea_geography=idea.geography,
            idea_revenue_model=idea.revenue_model,
            idea_pricing_estimate=idea.pricing_estimate,
            idea_team_size=idea.team_size,
            final_score=scores.final_viability_score,
            verdict=summary["verdict"],
            risk_level=summary["risk_level"],
            key_strength=summary["key_strength"],
            key_risk=summary["key_risk"],
            problem_intensity=scores.problem_intensity,
            market_timing=scores.market_timing,
            competition_pressure=scores.competition_pressure,
            market_potential=scores.market_potential,
            execution_feasibility=scores.execution_feasibility,
        )
        print(f"✅ [PITCH-DECK] Alai generation complete — generation_id={deck.generation_id}")
    except AlaiError as exc:
        print(f"❌ [PITCH-DECK] Alai FAILED: {exc}")
        db_record.status = "failed"
        db_record.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_record)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Pitch deck generation failed — Alai service unavailable: {exc}",
        ) from exc
    except Exception as exc:
        print(f"❌ [PITCH-DECK] Unexpected error: {exc}")
        db_record.status = "failed"
        db_record.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_record)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pitch deck generation failed unexpectedly: {exc}",
        ) from exc

    # 5. Update DB record to completed
    db_record.status = "completed"
    db_record.provider = deck.provider
    db_record.generation_id = deck.generation_id
    db_record.view_url = deck.view_url
    db_record.pdf_url = deck.pdf_url
    db_record.deck_json = deck.model_dump_json()
    db_record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_record)

    print(f"✅ [PITCH-DECK] DB updated to completed (id={db_record.id})")
    print(f"✅ [PITCH-DECK] view_url={db_record.view_url}")
    print(f"✅ [PITCH-DECK] pdf_url={db_record.pdf_url}")

    response = _record_to_response(db_record)

    # Index for RAG chat
    try:
        deck_data = {
            "title": idea.startup_name,
            "provider": deck.provider,
            "status": "completed",
            "view_url": deck.view_url,
        }
        chunks = chunk_pitch_deck(str(idea_id), deck_data)
        await index_chunks_async(chunks)
    except Exception as exc:
        logger.warning("Vector indexing failed (non-blocking): %s", exc)

    print(f"✅ [PITCH-DECK] Returning final response to frontend")
    return response


@router.get(
    "/",
    response_model=PitchDeckListResponse,
    summary="List all Pitch Decks for current user",
    response_description="All pitch decks owned by the authenticated user",
)
def list_decks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PitchDeckListResponse:
    """Return all pitch decks for the logged-in user, sorted by created_at DESC."""
    records = (
        db.query(PitchDeck)
        .filter(PitchDeck.user_id == str(current_user.id))
        .order_by(PitchDeck.created_at.desc())
        .all()
    )
    return PitchDeckListResponse(
        pitch_decks=[_record_to_response(r) for r in records]
    )


@router.get(
    "/idea/{idea_id}",
    response_model=PitchDeckRecord,
    summary="Get Pitch Deck by Idea ID",
    response_description="Pitch deck linked to the specified idea",
)
def get_deck_by_idea(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PitchDeckRecord:
    """Retrieve a pitch deck by its linked idea ID."""
    record = (
        db.query(PitchDeck)
        .filter(
            PitchDeck.idea_id == str(idea_id),
            PitchDeck.user_id == str(current_user.id),
        )
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pitch deck found for idea {idea_id}",
        )
    return _record_to_response(record)


@router.get(
    "/{pitch_deck_id}",
    response_model=PitchDeckRecord,
    summary="Get Pitch Deck by ID",
    response_description="Single pitch deck record",
)
def get_deck(
    pitch_deck_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PitchDeckRecord:
    """Retrieve a single pitch deck by its own ID."""
    record = (
        db.query(PitchDeck)
        .filter(
            PitchDeck.id == str(pitch_deck_id),
            PitchDeck.user_id == str(current_user.id),
        )
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pitch deck {pitch_deck_id} not found",
        )
    return _record_to_response(record)
