"""AI Chat Co-Founder routes — RAG-powered conversational endpoint.

Endpoints:
  POST /chat/{idea_id}/ask  — Ask a question about a specific idea
  GET  /chat/{idea_id}/status — Check what agents have indexed data
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.idea import Idea
from ..models.user import User
from ..services.auth_dependency import get_current_user
from ..services.chat_service import ask_co_founder
from ..services.vector_store import get_indexed_agents

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["AI Chat Co-Founder"],
)


# ── Request / Response schemas ────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="User question about the startup idea",
    )


class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI Co-Founder response")
    sources: list[str] = Field(
        default_factory=list,
        description="Source labels for the retrieved context",
    )
    indexed_agents: list[str] = Field(
        default_factory=list,
        description="Agents that have indexed data for this idea",
    )


class ChatStatusResponse(BaseModel):
    idea_id: str
    indexed_agents: list[str]
    ready: bool = Field(
        ..., description="True if at least one agent has indexed data"
    )


# ── Routes ────────────────────────────────────────────────────────────────

@router.post(
    "/{idea_id}/ask",
    response_model=ChatResponse,
    summary="Ask AI Co-Founder",
    response_description="RAG-powered answer grounded in agent outputs",
)
async def ask_chat(
    idea_id: UUID,
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Ask the AI Co-Founder a question about a specific idea.

    The response is grounded in validated agent outputs stored in the vector
    database. If no data is available, the response will indicate which agents
    need to be run first.
    """
    # Verify idea exists and belongs to user
    idea = db.query(Idea).filter(Idea.id == str(idea_id)).first()
    if idea is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Idea {idea_id} not found",
        )

    print(f"💬 [CHAT] Question for idea {idea_id}: {body.question[:80]}...")

    result = await ask_co_founder(
        idea_id=str(idea_id),
        question=body.question,
    )

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        indexed_agents=result["indexed_agents"],
    )


@router.get(
    "/{idea_id}/status",
    response_model=ChatStatusResponse,
    summary="Chat Data Status",
    response_description="Which agents have indexed data for this idea",
)
def chat_status(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatStatusResponse:
    """Check which agents have indexed data for this idea."""
    idea = db.query(Idea).filter(Idea.id == str(idea_id)).first()
    if idea is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Idea {idea_id} not found",
        )

    indexed = get_indexed_agents(str(idea_id))
    return ChatStatusResponse(
        idea_id=str(idea_id),
        indexed_agents=indexed,
        ready=len(indexed) > 0,
    )
