"""Locked Pydantic output schema for the Legal Document Generator.

This schema defines the strict contract for all generated legal documents.
Do NOT modify field names or types without updating all consumers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field


class LegalDocumentOutput(BaseModel):
    """The complete output of the Legal Document Generator agent."""

    document_type: str = Field(
        ...,
        description="One of: NDA, Founder Agreement, Privacy Policy, Terms of Service",
    )
    jurisdiction: str = Field(
        ...,
        description="Country / region the document is drafted for",
    )
    governing_law: str = Field(
        ...,
        description="Governing law clause, e.g. 'Laws of the State of Delaware, USA'",
    )
    disclaimer: str = Field(
        default="This document is generated for informational purposes only and does not constitute legal advice.",
        description="Mandatory disclaimer attached to every document",
    )

    sections: List[Dict[str, str]] = Field(
        ...,
        description="Ordered list of document sections, each with 'title' and 'content' keys",
    )

    customization_notes: List[str] = Field(
        default_factory=list,
        description="Notes about how the document was customized for the jurisdiction / startup",
    )
    legal_risk_notes: List[str] = Field(
        default_factory=list,
        description="Potential legal risks the founder should be aware of",
    )

    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of generation",
    )
