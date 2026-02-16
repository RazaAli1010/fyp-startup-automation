"""Authentication routes — signup, login, email verification, Google OAuth."""

from __future__ import annotations

import logging
import os
import re
from uuid import uuid4

from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.auth_schema import (
    AuthResponse,
    DashboardResponse,
    LoginRequest,
    MessageResponse,
    SignupRequest,
    UserDashboardIdea,
    UserDashboardLegal,
    UserDashboardMarketResearch,
    UserDashboardMVP,
    UserDashboardPitchDeck,
    UserPublic,
)
from ..services.auth_dependency import get_current_user
from ..services.auth_utils import (
    create_access_token,
    create_email_verification_token,
    decode_email_verification_token,
    hash_password,
    send_verification_email,
    verify_password,
)
from ..services.google_oauth_config import (
    GOOGLE_AUTH_ENABLED,
    GOOGLE_AUTH_URL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_TOKEN_URL,
    GOOGLE_USERINFO_URL,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ===================================================================== #
#  Utility: build UserPublic from ORM                                     #
# ===================================================================== #

def _user_public(user: User) -> UserPublic:
    return UserPublic(
        id=str(user.id),
        email=user.email,
        username=user.username,
        auth_provider=user.auth_provider,
        is_email_verified=user.is_email_verified,
    )


# ===================================================================== #
#  Google OAuth status endpoint (for frontend)                            #
# ===================================================================== #

@router.get("/google/status", summary="Check if Google OAuth is available")
def google_auth_status():
    """Return whether Google OAuth login is currently available."""
    return {"google_auth_enabled": GOOGLE_AUTH_ENABLED}


# ===================================================================== #
#  Local auth                                                             #
# ===================================================================== #

@router.post(
    "/signup",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> MessageResponse:
    """Create a new local user and send a verification email."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    existing_username = db.query(User).filter(User.username == payload.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken",
        )

    user = User(
        id=uuid4(),
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        is_email_verified=False,
        auth_provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_email_verification_token(str(user.id), user.email)
    send_verification_email(user.email, token)

    print(f"✅ [Auth] User signed up: {user.email}")
    return MessageResponse(
        message="Account created. Please check your email to verify your account."
    )


@router.get(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email address",
)
def verify_email(
    token: str = Query(..., description="Email verification token"),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Validate the email verification token and activate the account."""
    payload = decode_email_verification_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_email_verified:
        return MessageResponse(message="Email already verified. You can log in.")

    user.is_email_verified = True
    db.commit()

    print(f"✅ [Auth] Email verified: {user.email}")
    return MessageResponse(message="Email verified successfully. You can now log in.")


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in with email and password",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Authenticate a local user and issue a JWT."""
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or user.hashed_password is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox for the verification link.",
        )

    token = create_access_token(str(user.id), user.email, user.username)
    print(f"✅ [Auth] User logged in: {user.email}")
    return AuthResponse(
        access_token=token,
        user=_user_public(user),
    )


# ===================================================================== #
#  Google OAuth 2.0                                                       #
# ===================================================================== #

@router.get("/google/login", summary="Redirect to Google consent screen")
def google_login():
    """Redirect user to Google OAuth consent screen."""
    if not GOOGLE_AUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is temporarily unavailable",
        )

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback", summary="Handle Google OAuth callback")
def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    db: Session = Depends(get_db),
):
    """Exchange Google auth code for tokens, create/find user, issue JWT."""
    if not GOOGLE_AUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is temporarily unavailable",
        )

    # Exchange code for access token
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        token_resp = httpx.post(GOOGLE_TOKEN_URL, data=token_data, timeout=10.0)
        if token_resp.status_code != 200:
            logger.error("Google token exchange failed: %s", token_resp.text)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with Google",
            )
        tokens = token_resp.json()
    except httpx.HTTPError as exc:
        logger.error("Google token exchange error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to communicate with Google",
        )

    # Get user info
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No access token received from Google",
        )

    try:
        userinfo_resp = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google",
            )
        userinfo = userinfo_resp.json()
    except httpx.HTTPError as exc:
        logger.error("Google userinfo error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to get user info from Google",
        )

    google_email = userinfo.get("email")
    if not google_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account has no email",
        )

    # Find or create user
    user = db.query(User).filter(User.email == google_email).first()
    if user is None:
        # Generate a unique username from the Google email prefix
        base_username = re.sub(r"[^a-zA-Z0-9_]", "", google_email.split("@")[0])[:15]
        if len(base_username) < 3:
            base_username = "user"
        username = base_username
        counter = 1
        while db.query(User).filter(User.username == username).first() is not None:
            username = f"{base_username}_{counter}"
            counter += 1

        user = User(
            id=uuid4(),
            email=google_email,
            username=username,
            hashed_password=None,
            is_email_verified=True,
            auth_provider="google",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✅ [Auth] New Google user created: {google_email} (username: {username})")
    else:
        if not user.is_email_verified:
            user.is_email_verified = True
            db.commit()
        print(f"✅ [Auth] Existing user logged in via Google: {google_email}")

    jwt_token = create_access_token(str(user.id), user.email, user.username)

    # Redirect to frontend with token
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(
        url=f"{frontend_url}/auth/google/callback?token={jwt_token}",
    )


# ===================================================================== #
#  Protected: current user info + dashboard                               #
# ===================================================================== #

@router.get("/me", response_model=UserPublic, summary="Get current user")
def get_me(user: User = Depends(get_current_user)) -> UserPublic:
    """Return the authenticated user's public profile."""
    return _user_public(user)


@router.get("/dashboard", response_model=DashboardResponse, summary="User dashboard data")
def get_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """Return the user's profile, submitted ideas, pitch deck history, and market research."""
    from ..models.idea import Idea
    from ..models.pitch_deck import PitchDeck
    from ..models.market_research import MarketResearch
    from ..models.mvp_report import MVPReport

    ideas = db.query(Idea).filter(Idea.user_id == user.id).order_by(Idea.created_at.desc()).all()

    idea_list = []
    for idea in ideas:
        idea_list.append(
            UserDashboardIdea(
                id=str(idea.id),
                startup_name=idea.startup_name,
                industry=idea.industry,
                created_at=idea.created_at.isoformat() if idea.created_at else None,
                final_viability_score=idea.final_viability_score,
            )
        )

    decks = (
        db.query(PitchDeck)
        .filter(PitchDeck.user_id == str(user.id))
        .order_by(PitchDeck.created_at.desc())
        .all()
    )
    deck_list = []
    for deck in decks:
        deck_list.append(
            UserDashboardPitchDeck(
                id=str(deck.id),
                idea_id=str(deck.idea_id),
                title=deck.title or "Pitch Deck",
                status=deck.status or "pending",
                view_url=deck.view_url,
                pdf_url=deck.pdf_url,
                created_at=deck.created_at.isoformat() if deck.created_at else None,
            )
        )

    research_records = (
        db.query(MarketResearch)
        .filter(MarketResearch.user_id == str(user.id))
        .order_by(MarketResearch.created_at.desc())
        .all()
    )
    research_list = []
    for r in research_records:
        research_list.append(
            UserDashboardMarketResearch(
                id=str(r.id),
                idea_id=str(r.idea_id),
                status=r.status or "pending",
                tam_max=r.tam_max,
                sam_max=r.sam_max,
                som_max=r.som_max,
                demand_strength=r.demand_strength,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
        )

    mvp_records = (
        db.query(MVPReport)
        .filter(MVPReport.user_id == str(user.id))
        .order_by(MVPReport.created_at.desc())
        .all()
    )
    mvp_list = []
    for m in mvp_records:
        mvp_type = None
        if m.blueprint_json:
            try:
                import json as _json
                bp = _json.loads(m.blueprint_json)
                mvp_type = bp.get("mvp_type")
            except Exception:
                pass
        mvp_list.append(
            UserDashboardMVP(
                id=str(m.id),
                idea_id=str(m.idea_id),
                status=m.status or "pending",
                mvp_type=mvp_type,
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
        )

    from ..models.legal_document import LegalDocument
    legal_records = (
        db.query(LegalDocument)
        .filter(LegalDocument.user_id == str(user.id))
        .order_by(LegalDocument.created_at.desc())
        .all()
    )
    legal_list = [
        UserDashboardLegal(
            id=str(ld.id),
            idea_id=str(ld.idea_id),
            document_type=ld.document_type or "",
            jurisdiction=ld.jurisdiction,
            status=ld.status or "pending",
            created_at=ld.created_at.isoformat() if ld.created_at else None,
        )
        for ld in legal_records
    ]

    return DashboardResponse(
        user=_user_public(user),
        ideas=idea_list,
        pitch_decks=deck_list,
        market_research=research_list,
        mvp_reports=mvp_list,
        legal_documents=legal_list,
    )
