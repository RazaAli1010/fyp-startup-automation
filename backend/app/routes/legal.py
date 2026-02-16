"""Legal Document routes — generate and retrieve legal documents.

Endpoints:
  POST /legal/generate           — Generate a legal document for an idea
  GET  /legal/idea/{idea_id}     — List all legal docs for a specific idea
  GET  /legal/{document_id}      — Get a single legal document by ID
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..agents.legal_agent.generator import generate_legal_document
from ..database import get_db
from ..models.idea import Idea
from ..models.legal_document import LegalDocument
from ..models.user import User
from ..schemas.legal_schema import (
    LegalDocumentListResponse,
    LegalDocumentRecord,
    LegalDocumentResponse,
)
from ..services.auth_dependency import get_current_user
from ..services.vector_store import chunk_legal, index_chunks_async

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/legal",
    tags=["Legal"],
)


# ── Request body ─────────────────────────────────────────────────────────

class GenerateLegalRequest(BaseModel):
    """Structured input for legal document generation."""
    document_type: str = Field(
        ...,
        description="One of: nda, founder_agreement, privacy_policy, terms_of_service",
    )
    jurisdiction: Optional[str] = Field(
        None,
        description="Country / jurisdiction override. Uses idea geography if omitted.",
    )
    company_name: Optional[str] = Field(
        None,
        description="Legal company name override. Uses idea startup_name if omitted.",
    )
    founder_count: int = Field(
        2,
        description="Number of founders (used for Founder Agreement).",
    )


# ── Helpers ──────────────────────────────────────────────────────────────

def _record_to_response(record: LegalDocument) -> LegalDocumentRecord:
    """Convert a LegalDocument ORM instance to a LegalDocumentRecord response."""
    document = None
    if record.document_json:
        try:
            document = LegalDocumentResponse(**json.loads(record.document_json))
        except Exception:
            document = None

    return LegalDocumentRecord(
        id=str(record.id),
        idea_id=str(record.idea_id),
        document_type=record.document_type or "",
        jurisdiction=record.jurisdiction,
        status=record.status or "pending",
        document=document,
        created_at=record.created_at or datetime.utcnow(),
    )


# ── Routes ───────────────────────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=LegalDocumentRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Legal Document",
    response_description="Legal document record with content",
)
async def generate_legal(
    idea_id: UUID = Query(..., description="The idea to generate a legal document for"),
    body: GenerateLegalRequest = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegalDocumentRecord:
    """Generate a legal document for a validated idea.

    Rules:
    - One document per (idea + document_type). If exists → return stored version.
    - Requires completed evaluation (idea validation).
    """
    doc_type_key = body.document_type.strip().lower().replace(" ", "_").replace("-", "_")

    # ── Check for existing document ──────────────────────────────
    existing = (
        db.query(LegalDocument)
        .filter(
            LegalDocument.idea_id == str(idea_id),
            LegalDocument.user_id == str(current_user.id),
            LegalDocument.document_type == doc_type_key,
        )
        .first()
    )
    if existing and existing.status == "generated":
        print(f"📄 [LEGAL] Returning stored {doc_type_key} (no regeneration) — idea_id={idea_id}")
        return _record_to_response(existing)

    # ── Fetch idea ───────────────────────────────────────────────
    idea = db.query(Idea).filter(Idea.id == str(idea_id)).first()
    if idea is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Idea {idea_id} not found",
        )

    # ── Validate dependency: evaluation must exist ───────────────
    if not idea.evaluation_report_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idea must be validated before generating legal documents. Run evaluation first.",
        )

    # ── Resolve inputs ───────────────────────────────────────────
    company_name = body.company_name or idea.startup_name
    geography = body.jurisdiction or idea.geography
    founder_count = body.founder_count

    # ── Upsert DB record as pending ──────────────────────────────
    if existing:
        existing.status = "pending"
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        db_record = existing
    else:
        db_record = LegalDocument(
            user_id=str(current_user.id),
            idea_id=str(idea_id),
            document_type=doc_type_key,
            status="pending",
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

    print(f"⚖️ [LEGAL] Generating {doc_type_key} for idea_id={idea_id}")

    # ── Run legal document generator ─────────────────────────────
    try:
        doc_output = await generate_legal_document(
            document_type=doc_type_key,
            company_name=company_name,
            industry=idea.industry,
            geography=geography,
            founder_count=founder_count,
        )
    except Exception as exc:
        print(f"❌ [LEGAL] Generation FAILED: {exc}")
        db_record.status = "failed"
        db_record.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_record)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Legal document generation failed: {exc}",
        ) from exc

    # ── Persist document ─────────────────────────────────────────
    db_record.status = "generated"
    db_record.jurisdiction = doc_output.jurisdiction
    db_record.document_json = json.dumps(doc_output.model_dump(), default=str)
    db_record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_record)

    print(f"📄 [LEGAL] Document stored in DB — {doc_type_key} for idea_id={idea_id}")

    # Index for RAG chat
    try:
        chunks = chunk_legal(str(idea_id), doc_output.model_dump())
        await index_chunks_async(chunks)
    except Exception as exc:
        logger.warning("Vector indexing failed (non-blocking): %s", exc)

    return _record_to_response(db_record)


@router.get(
    "/idea/{idea_id}",
    response_model=LegalDocumentListResponse,
    summary="List legal documents for an idea",
    response_description="All legal documents linked to the specified idea",
)
def get_legal_by_idea(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegalDocumentListResponse:
    """Retrieve all legal documents for an idea. Never triggers generation."""
    records = (
        db.query(LegalDocument)
        .filter(
            LegalDocument.idea_id == str(idea_id),
            LegalDocument.user_id == str(current_user.id),
        )
        .order_by(LegalDocument.created_at.desc())
        .all()
    )
    return LegalDocumentListResponse(
        records=[_record_to_response(r) for r in records]
    )


@router.get(
    "/{document_id}",
    response_model=LegalDocumentRecord,
    summary="Get legal document by ID",
    response_description="A single legal document record",
)
def get_legal_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegalDocumentRecord:
    """Retrieve a single legal document by its ID. Never triggers generation."""
    record = (
        db.query(LegalDocument)
        .filter(
            LegalDocument.id == str(document_id),
            LegalDocument.user_id == str(current_user.id),
        )
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Legal document {document_id} not found",
        )
    return _record_to_response(record)
