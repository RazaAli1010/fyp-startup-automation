from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.idea_schema import IdeaResponse, StartupIdeaInput
from ..services.auth_dependency import get_current_user
from ..services.idea_service import create_idea

router = APIRouter(
    prefix="/ideas",
    tags=["Ideas"],
)


@router.post(
    "/",
    response_model=IdeaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a Startup Idea",
    response_description="The submitted idea ID and confirmation message",
)
def submit_idea(
    payload: StartupIdeaInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IdeaResponse:
    """Accept a structured startup idea, validate it, persist it, and return its ID."""
    try:
        idea = create_idea(db, payload, user_id=current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store idea: {exc}",
        ) from exc

    return IdeaResponse(
        idea_id=idea.id,
        message="Idea submitted successfully",
    )
