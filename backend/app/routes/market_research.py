"""Market Research routes — generate and retrieve market research reports.

Endpoints:
  POST /market-research/generate      — Generate market research for an idea
  GET  /market-research/idea/{idea_id} — Get research for a specific idea
  GET  /market-research/               — List all research for current user
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..agents.market_research_agent.agent import run_market_research
from ..database import get_db
from ..models.idea import Idea
from ..models.market_research import MarketResearch
from ..models.user import User
from ..schemas.market_research_schema import MarketResearchRecord, MarketResearchListResponse
from ..services.auth_dependency import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/market-research",
    tags=["Market Research"],
)


# ── Helpers ──────────────────────────────────────────────────────────────

def _record_to_response(record: MarketResearch) -> MarketResearchRecord:
    """Convert a MarketResearch ORM instance to a MarketResearchRecord response."""
    return MarketResearchRecord(
        id=str(record.id),
        idea_id=str(record.idea_id),
        status=record.status or "pending",
        tam_min=record.tam_min,
        tam_max=record.tam_max,
        sam_min=record.sam_min,
        sam_max=record.sam_max,
        som_min=record.som_min,
        som_max=record.som_max,
        arpu_annual=record.arpu_annual,
        growth_rate_estimate=record.growth_rate_estimate,
        demand_strength=record.demand_strength,
        assumptions=json.loads(record.assumptions_json) if record.assumptions_json else None,
        confidence=json.loads(record.confidence_json) if record.confidence_json else None,
        sources=json.loads(record.sources_json) if record.sources_json else None,
        competitors=json.loads(record.competitors_json) if record.competitors_json else None,
        competitor_count=int(record.competitor_count) if record.competitor_count else 0,
        created_at=record.created_at or datetime.utcnow(),
    )


# ── Routes ───────────────────────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=MarketResearchRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Market Research",
    response_description="Market research record with TAM/SAM/SOM and confidence",
)
def generate_research(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarketResearchRecord:
    """Generate market research for an idea.

    1. Creates a DB record with status=pending
    2. Runs market research agent (calculations + confidence)
    3. Updates DB record to completed
    4. Returns the full MarketResearchRecord
    """
    print(f"➡️  [MARKET] Generation START for idea {idea_id}")

    # 1. Fetch idea
    idea = db.query(Idea).filter(Idea.id == str(idea_id)).first()
    if idea is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Idea {idea_id} not found",
        )

    # 2. Upsert DB record as "pending"
    existing = db.query(MarketResearch).filter(MarketResearch.idea_id == str(idea_id)).first()
    if existing:
        existing.status = "pending"
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        db_record = existing
        print(f"📝 [MARKET] Reset existing record to pending (id={db_record.id})")
    else:
        db_record = MarketResearch(
            user_id=str(current_user.id),
            idea_id=str(idea_id),
            status="pending",
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        print(f"📝 [MARKET] Created pending record (id={db_record.id})")

    # 3. Run market research agent
    print(f"🔄 [MARKET] Running market research agent for idea {idea_id}")
    try:
        result = run_market_research(
            startup_name=idea.startup_name,
            one_line_description=idea.one_line_description,
            industry=idea.industry,
            target_customer_type=idea.target_customer_type,
            geography=idea.geography,
            customer_size=idea.customer_size,
            revenue_model=idea.revenue_model,
            pricing_estimate=idea.pricing_estimate,
            team_size=idea.team_size,
        )
        print("✅ [MARKET] Market research agent complete")
    except Exception as exc:
        print(f"❌ [MARKET] Agent FAILED: {exc}")
        db_record.status = "failed"
        db_record.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_record)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Market research generation failed: {exc}",
        ) from exc

    # 4. Update DB record to completed
    db_record.status = "completed"
    db_record.tam_min = result.tam_min
    db_record.tam_max = result.tam_max
    db_record.sam_min = result.sam_min
    db_record.sam_max = result.sam_max
    db_record.som_min = result.som_min
    db_record.som_max = result.som_max
    db_record.arpu_annual = result.arpu_annual
    db_record.growth_rate_estimate = result.growth_rate_estimate
    db_record.demand_strength = result.demand_strength
    db_record.assumptions_json = json.dumps(result.assumptions)
    db_record.confidence_json = json.dumps(result.confidence)
    db_record.sources_json = json.dumps(result.sources)
    db_record.competitors_json = json.dumps(result.competitors)
    db_record.competitor_count = result.competitor_count
    db_record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_record)

    print(f"✅ [MARKET] DB updated to completed (id={db_record.id})")
    print(f"✅ [MARKET] TAM: ${result.tam_min/1e9:.1f}B – ${result.tam_max/1e9:.1f}B")
    print(f"✅ [MARKET] Demand: {result.demand_strength}/100")

    response = _record_to_response(db_record)
    print("✅ [MARKET] Returning final response to frontend")
    return response


@router.get(
    "/",
    response_model=MarketResearchListResponse,
    summary="List all Market Research for current user",
    response_description="All market research records owned by the authenticated user",
)
def list_research(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarketResearchListResponse:
    """Return all market research for the logged-in user, sorted by created_at DESC."""
    records = (
        db.query(MarketResearch)
        .filter(MarketResearch.user_id == str(current_user.id))
        .order_by(MarketResearch.created_at.desc())
        .all()
    )
    return MarketResearchListResponse(
        records=[_record_to_response(r) for r in records]
    )


@router.get(
    "/idea/{idea_id}",
    response_model=MarketResearchRecord,
    summary="Get Market Research by Idea ID",
    response_description="Market research linked to the specified idea",
)
def get_research_by_idea(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarketResearchRecord:
    """Retrieve market research by its linked idea ID."""
    record = (
        db.query(MarketResearch)
        .filter(
            MarketResearch.idea_id == str(idea_id),
            MarketResearch.user_id == str(current_user.id),
        )
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market research found for idea {idea_id}",
        )
    return _record_to_response(record)
