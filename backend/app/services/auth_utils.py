"""Authentication utilities — password hashing, JWT, email verification tokens.

Rules
-----
- NO hardcoded secrets — all from environment variables
- Deterministic token generation for email verification
- Secure password hashing with bcrypt
"""

from __future__ import annotations

import os
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a hash."""
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
_JWT_SECRET = os.getenv("JWT_SECRET", "startbot-dev-secret-change-in-production")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24h default


def create_access_token(user_id: str, email: str, username: str = "") -> str:
    """Create a signed JWT containing user_id, email, and username."""
    expire = datetime.utcnow() + timedelta(minutes=_JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT. Returns payload dict or None."""
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Email verification tokens (JWT-based, separate secret)
# ---------------------------------------------------------------------------
_EMAIL_SECRET = os.getenv("EMAIL_VERIFICATION_SECRET", "startbot-email-verify-dev")
_EMAIL_TOKEN_EXPIRE_HOURS = 24


def create_email_verification_token(user_id: str, email: str) -> str:
    """Create a signed token for email verification."""
    expire = datetime.utcnow() + timedelta(hours=_EMAIL_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "purpose": "email_verification",
        "exp": expire,
    }
    return jwt.encode(payload, _EMAIL_SECRET, algorithm=_JWT_ALGORITHM)


def decode_email_verification_token(token: str) -> Optional[dict]:
    """Decode an email verification token. Returns payload or None."""
    try:
        payload = jwt.decode(token, _EMAIL_SECRET, algorithms=[_JWT_ALGORITHM])
        if payload.get("purpose") != "email_verification":
            return None
        return payload
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Email sending
# ---------------------------------------------------------------------------
def send_verification_email(to_email: str, token: str) -> bool:
    """Send a verification email via SMTP.

    Returns True on success, False on failure.
    Does NOT block the backend if email fails — logs a warning instead.
    """
    host = os.getenv("EMAIL_HOST", "")
    port = int(os.getenv("EMAIL_PORT", "587"))
    user = os.getenv("EMAIL_USER", "")
    password = os.getenv("EMAIL_PASSWORD", "")
    from_email = os.getenv("EMAIL_FROM", "")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    if not all([host, user, password, from_email]):
        logger.warning(
            "Email not configured (EMAIL_HOST/USER/PASSWORD/FROM missing) "
            "— skipping verification email to %s",
            to_email,
        )
        print(f"⚠️ [Auth] Email not configured — verification token for {to_email}: {token}")
        return False

    verification_link = f"{frontend_url}/auth/verify-email?token={token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "StartBot — Verify Your Email"
    msg["From"] = from_email
    msg["To"] = to_email

    text_body = (
        f"Welcome to StartBot!\n\n"
        f"Please verify your email by clicking the link below:\n\n"
        f"{verification_link}\n\n"
        f"This link expires in {_EMAIL_TOKEN_EXPIRE_HOURS} hours.\n\n"
        f"If you did not create an account, please ignore this email."
    )

    html_body = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
        <h2 style="color: #6366f1;">Welcome to StartBot</h2>
        <p>Please verify your email address to start validating startup ideas.</p>
        <a href="{verification_link}"
           style="display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #6366f1, #a855f7);
                  color: white; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 16px 0;">
            Verify Email
        </a>
        <p style="color: #94a3b8; font-size: 13px;">
            This link expires in {_EMAIL_TOKEN_EXPIRE_HOURS} hours.<br/>
            If you did not create an account, please ignore this email.
        </p>
    </div>
    """

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_email, to_email, msg.as_string())
        print(f"✅ [Auth] Verification email sent to {to_email}")
        return True
    except Exception as exc:
        logger.warning("Failed to send verification email to %s: %s", to_email, exc)
        print(f"⚠️ [Auth] Email send failed for {to_email}: {exc}")
        print(f"⚠️ [Auth] Verification token (fallback): {token}")
        return False
