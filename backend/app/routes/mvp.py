"""MVP routes — generate and retrieve MVP blueprint reports.

Endpoints:
  POST /mvp/generate          — Generate MVP blueprint for an idea
  GET  /mvp/idea/{idea_id}    — Get MVP for a specific idea
  GET  /mvp/                  — List all MVPs for current user
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..agents.mvp_agent.generator import generate_mvp_blueprint
from ..database import get_db
from ..models.idea import Idea
from ..models.market_research import MarketResearch
from ..models.mvp_report import MVPReport
from ..models.user import User
from ..schemas.mvp_schema import MVPBlueprintResponse, MVPReportRecord, MVPReportListResponse
from ..services.auth_dependency import get_current_user
from ..services.vector_store import chunk_mvp, index_chunks_async

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mvp",
    tags=["MVP"],
)


# ── Helpers ──────────────────────────────────────────────────────────────

def _record_to_response(record: MVPReport) -> MVPReportRecord:
    """Convert an MVPReport ORM instance to an MVPReportRecord response."""
    blueprint = None
    if record.blueprint_json:
        try:
            blueprint = MVPBlueprintResponse(**json.loads(record.blueprint_json))
        except Exception:
            blueprint = None

    return MVPReportRecord(
        id=str(record.id),
        idea_id=str(record.idea_id),
        status=record.status or "pending",
        blueprint=blueprint,
        created_at=record.created_at or datetime.utcnow(),
    )


def _extract_market_confidence(mr: MarketResearch) -> str:
    """Extract overall market confidence level from MarketResearch record."""
    if mr.confidence_json:
        try:
            conf = json.loads(mr.confidence_json)
            overall = conf.get("overall", 0)
            if overall >= 70:
                return "high"
            if overall >= 40:
                return "medium"
        except Exception:
            pass
    return "low"


# ── Routes ───────────────────────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=MVPReportRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Generate MVP Blueprint",
    response_description="MVP report with blueprint",
)
async def generate_mvp(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MVPReportRecord:
    """Generate an MVP blueprint for a validated idea.

    Rules:
    - If MVP already exists → return stored version (no regeneration)
    - Requires completed evaluation + market research
    """
    # ── Check for existing MVP ────────────────────────────────
    existing = (
        db.query(MVPReport)
        .filter(MVPReport.idea_id == str(idea_id), MVPReport.user_id == str(current_user.id))
        .first()
    )
    if existing and existing.status == "generated":
        print(f"📄 [MVP] Returning stored MVP (no regeneration) — idea_id={idea_id}")
        return _record_to_response(existing)

    # ── Fetch idea ────────────────────────────────────────────
    idea = db.query(Idea).filter(Idea.id == str(idea_id)).first()
    if idea is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Idea {idea_id} not found",
        )

    # ── Validate dependencies ─────────────────────────────────
    if not idea.evaluation_report_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idea must be evaluated before generating MVP. Run evaluation first.",
        )

    mr = db.query(MarketResearch).filter(MarketResearch.idea_id == str(idea_id)).first()
    if mr is None or mr.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Market research must be completed before generating MVP. Run market research first.",
        )

    # ── Parse evaluation scores ───────────────────────────────
    try:
        eval_report = json.loads(idea.evaluation_report_json)
        module_scores = eval_report.get("module_scores", {})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse stored evaluation report.",
        )

    # ── Parse competitors from market research ────────────────
    competitors = []
    competitor_count = int(mr.competitor_count) if mr.competitor_count else 0
    if mr.competitors_json:
        try:
            competitors = json.loads(mr.competitors_json)
        except Exception:
            competitors = []

    market_confidence = _extract_market_confidence(mr)

    # ── Upsert DB record as pending ───────────────────────────
    if existing:
        existing.status = "pending"
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        db_record = existing
    else:
        db_record = MVPReport(
            user_id=str(current_user.id),
            idea_id=str(idea_id),
            status="pending",
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

    print(f"🛠️ [MVP] Generating MVP for idea_id={idea_id}")

    # ── Run MVP generator ─────────────────────────────────────
    try:
        blueprint = generate_mvp_blueprint(
            startup_name=idea.startup_name,
            one_line_description=idea.one_line_description,
            industry=idea.industry,
            target_customer_type=idea.target_customer_type,
            geography=idea.geography,
            customer_size=idea.customer_size,
            revenue_model=idea.revenue_model,
            pricing_estimate=idea.pricing_estimate,
            team_size=idea.team_size,
            tech_complexity=idea.tech_complexity,
            regulatory_risk=idea.regulatory_risk,
            problem_intensity=module_scores.get("problem_intensity", 50),
            market_timing=module_scores.get("market_timing", 50),
            competition_pressure=module_scores.get("competition_pressure", 50),
            market_potential=module_scores.get("market_potential", 50),
            execution_feasibility=module_scores.get("execution_feasibility", 50),
            final_viability_score=module_scores.get("final_viability_score", 50),
            market_confidence=market_confidence,
            competitors=competitors,
            competitor_count=competitor_count,
        )
    except Exception as exc:
        print(f"❌ [MVP] Generation FAILED: {exc}")
        db_record.status = "failed"
        db_record.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_record)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MVP generation failed: {exc}",
        ) from exc

    # ── Persist blueprint ─────────────────────────────────────
    db_record.status = "generated"
    db_record.blueprint_json = json.dumps(blueprint.model_dump())
    db_record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_record)

    print(f"✅ [MVP] MVP blueprint generated and stored — idea_id={idea_id}")

    # Index for RAG chat
    try:
        chunks = chunk_mvp(str(idea_id), blueprint.model_dump())
        await index_chunks_async(chunks)
    except Exception as exc:
        logger.warning("Vector indexing failed (non-blocking): %s", exc)

    return _record_to_response(db_record)


@router.get(
    "/",
    response_model=MVPReportListResponse,
    summary="List all MVPs for current user",
    response_description="All MVP reports owned by the authenticated user",
)
def list_mvps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MVPReportListResponse:
    """Return all MVP reports for the logged-in user, sorted by created_at DESC."""
    records = (
        db.query(MVPReport)
        .filter(MVPReport.user_id == str(current_user.id))
        .order_by(MVPReport.created_at.desc())
        .all()
    )
    return MVPReportListResponse(
        records=[_record_to_response(r) for r in records]
    )


@router.get(
    "/idea/{idea_id}",
    response_model=MVPReportRecord,
    summary="Get MVP by Idea ID",
    response_description="MVP report linked to the specified idea",
)
def get_mvp_by_idea(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MVPReportRecord:
    """Retrieve MVP report by its linked idea ID. Never triggers generation."""
    record = (
        db.query(MVPReport)
        .filter(
            MVPReport.idea_id == str(idea_id),
            MVPReport.user_id == str(current_user.id),
        )
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No MVP report found for idea {idea_id}",
        )
    print(f"📄 [MVP] Returning stored MVP (no regeneration) — idea_id={idea_id}")
    return _record_to_response(record)
