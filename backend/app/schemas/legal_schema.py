"""Pydantic schemas for Legal Document API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class LegalDocumentResponse(BaseModel):
    """The document content returned inside a record."""

    document_type: str
    jurisdiction: str
    governing_law: str
    disclaimer: str
    sections: List[Dict[str, str]]
    customization_notes: List[str] = []
    legal_risk_notes: List[str] = []
    generated_at: Optional[datetime] = None


class LegalDocumentRecord(BaseModel):
    """A single legal document record (DB row → API response)."""

    id: str
    idea_id: str
    document_type: str
    jurisdiction: Optional[str] = None
    status: str
    document: Optional[LegalDocumentResponse] = None
    created_at: datetime


class LegalDocumentListResponse(BaseModel):
    """List wrapper for legal documents."""

    records: List[LegalDocumentRecord] = Field(default_factory=list)
