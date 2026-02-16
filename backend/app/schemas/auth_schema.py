"""Authentication request/response schemas."""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Password policy
# ---------------------------------------------------------------------------
COMMON_PASSWORDS = {
    "password", "password1", "123456", "12345678", "123456789",
    "qwerty", "abc123", "letmein", "welcome", "admin",
    "monkey", "master", "dragon", "login", "princess",
    "football", "shadow", "sunshine", "trustno1", "iloveyou",
}

_PW_MIN_LENGTH = 8
_PW_RULES = [
    (r"[A-Z]", "one uppercase letter"),
    (r"[a-z]", "one lowercase letter"),
    (r"[0-9]", "one number"),
    (r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", "one special character"),
]


def validate_password_strength(password: str) -> str:
    """Validate password meets strength requirements. Returns password or raises ValueError."""
    errors: list[str] = []
    if len(password) < _PW_MIN_LENGTH:
        errors.append(f"at least {_PW_MIN_LENGTH} characters")
    for pattern, label in _PW_RULES:
        if not re.search(pattern, password):
            errors.append(label)
    # Check if the password (or its alphabetic core) is a common password
    pw_lower = password.lower()
    pw_alpha = re.sub(r"[^a-z]", "", pw_lower)
    if pw_lower in COMMON_PASSWORDS or pw_alpha in COMMON_PASSWORDS:
        errors.append("not be a common password")
    if errors:
        raise ValueError(
            f"Password must contain {', '.join(errors)}."
        )
    return password


# ---------------------------------------------------------------------------
# Username policy
# ---------------------------------------------------------------------------
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")


def validate_username(username: str) -> str:
    """Validate username: 3-20 chars, letters/numbers/underscores only."""
    if not _USERNAME_RE.match(username):
        raise ValueError(
            "Username must be 3–20 characters and contain only letters, numbers, or underscores."
        )
    return username


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., description="Unique username (3-20 chars, alphanumeric + underscore)")
    password: str = Field(..., description="Strong password")

    @field_validator("username")
    @classmethod
    def check_username(cls, v: str) -> str:
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Password")


class AuthResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer")
    user: "UserPublic"


class UserPublic(BaseModel):
    id: str
    email: str
    username: str
    auth_provider: str
    is_email_verified: bool

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str


class UserDashboardIdea(BaseModel):
    id: str
    startup_name: str
    industry: str
    created_at: Optional[str] = None
    final_viability_score: Optional[float] = None


class UserDashboardPitchDeck(BaseModel):
    id: str
    idea_id: str
    title: str
    status: str  # pending | completed | failed
    view_url: Optional[str] = None
    pdf_url: Optional[str] = None
    created_at: Optional[str] = None


class UserDashboardMarketResearch(BaseModel):
    id: str
    idea_id: str
    status: str  # pending | completed | failed
    tam_max: Optional[float] = None
    sam_max: Optional[float] = None
    som_max: Optional[float] = None
    demand_strength: Optional[float] = None
    created_at: Optional[str] = None


class UserDashboardMVP(BaseModel):
    id: str
    idea_id: str
    status: str  # pending | generated | failed
    mvp_type: Optional[str] = None
    created_at: Optional[str] = None


class UserDashboardLegal(BaseModel):
    id: str
    idea_id: str
    document_type: str
    jurisdiction: Optional[str] = None
    status: str  # pending | generated | failed
    created_at: Optional[str] = None


class DashboardResponse(BaseModel):
    user: UserPublic
    ideas: list[UserDashboardIdea] = []
    pitch_decks: list[UserDashboardPitchDeck] = []
    market_research: list[UserDashboardMarketResearch] = []
    mvp_reports: list[UserDashboardMVP] = []
    legal_documents: list[UserDashboardLegal] = []
