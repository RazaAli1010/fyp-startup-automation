"""Authentication tests — signup, login, email verification, JWT, password policy, username, Google status."""

import os
import sys

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.services.auth_utils import (
    create_access_token,
    create_email_verification_token,
    decode_access_token,
    decode_email_verification_token,
    hash_password,
    verify_password,
)
from app.schemas.auth_schema import validate_password_strength, validate_username

# ---------------------------------------------------------------------------
# Test database setup (file-based SQLite for compatibility)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Counter to generate unique usernames per test helper call
_user_counter = 0


def _next_username(prefix="testuser"):
    global _user_counter
    _user_counter += 1
    return f"{prefix}_{_user_counter}"


# Strong password that passes all rules
STRONG_PW = "Str0ng!Pass"


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


# ===================================================================== #
#  Unit tests: auth_utils                                                 #
# ===================================================================== #

class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "securePassword123!"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("Correct1!")
        assert verify_password("wrong", hashed) is False


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token("user-123", "test@example.com", "testuser")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert payload["username"] == "testuser"

    def test_invalid_token(self):
        assert decode_access_token("garbage.token.here") is None


class TestEmailVerificationToken:
    def test_create_and_decode(self):
        token = create_email_verification_token("user-456", "verify@test.com")
        payload = decode_email_verification_token(token)
        assert payload is not None
        assert payload["sub"] == "user-456"
        assert payload["email"] == "verify@test.com"
        assert payload["purpose"] == "email_verification"

    def test_invalid_token(self):
        assert decode_email_verification_token("bad.token") is None


# ===================================================================== #
#  Unit tests: password policy                                             #
# ===================================================================== #

class TestPasswordPolicy:
    def test_strong_password_accepted(self):
        result = validate_password_strength(STRONG_PW)
        assert result == STRONG_PW

    def test_weak_no_uppercase(self):
        with pytest.raises(ValueError, match="uppercase"):
            validate_password_strength("weak1pass!")

    def test_weak_no_number(self):
        with pytest.raises(ValueError, match="number"):
            validate_password_strength("WeakPass!!")

    def test_weak_no_special(self):
        with pytest.raises(ValueError, match="special"):
            validate_password_strength("WeakPass11")

    def test_weak_too_short(self):
        with pytest.raises(ValueError, match="8 characters"):
            validate_password_strength("Ab1!")

    def test_common_password_rejected(self):
        with pytest.raises(ValueError, match="common"):
            validate_password_strength("Password1!")  # "password" is common

    def test_weak_no_lowercase(self):
        with pytest.raises(ValueError, match="lowercase"):
            validate_password_strength("STRONG1!!")


# ===================================================================== #
#  Unit tests: username validation                                         #
# ===================================================================== #

class TestUsernameValidation:
    def test_valid_username(self):
        assert validate_username("hello_world") == "hello_world"

    def test_too_short(self):
        with pytest.raises(ValueError):
            validate_username("ab")

    def test_too_long(self):
        with pytest.raises(ValueError):
            validate_username("a" * 21)

    def test_invalid_chars(self):
        with pytest.raises(ValueError):
            validate_username("user@name")


# ===================================================================== #
#  Integration tests: auth routes                                         #
# ===================================================================== #

class TestSignup:
    def test_signup_success(self):
        resp = client.post("/auth/signup", json={
            "email": "newuser@example.com",
            "username": _next_username(),
            "password": STRONG_PW,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "verify" in data["message"].lower() or "check" in data["message"].lower()

    def test_signup_duplicate_email(self):
        uname1 = _next_username()
        uname2 = _next_username()
        client.post("/auth/signup", json={
            "email": "dup@example.com",
            "username": uname1,
            "password": STRONG_PW,
        })
        resp = client.post("/auth/signup", json={
            "email": "dup@example.com",
            "username": uname2,
            "password": STRONG_PW,
        })
        assert resp.status_code == 409

    def test_signup_duplicate_username(self):
        uname = _next_username()
        client.post("/auth/signup", json={
            "email": "user1@example.com",
            "username": uname,
            "password": STRONG_PW,
        })
        resp = client.post("/auth/signup", json={
            "email": "user2@example.com",
            "username": uname,
            "password": STRONG_PW,
        })
        assert resp.status_code == 409
        assert "username" in resp.json()["detail"].lower()

    def test_signup_weak_password_rejected(self):
        resp = client.post("/auth/signup", json={
            "email": "weak@example.com",
            "username": _next_username(),
            "password": "weakpass",
        })
        assert resp.status_code == 422

    def test_signup_common_password_rejected(self):
        resp = client.post("/auth/signup", json={
            "email": "common@example.com",
            "username": _next_username(),
            "password": "Password1!",  # "password" is common
        })
        assert resp.status_code == 422

    def test_signup_invalid_username_rejected(self):
        resp = client.post("/auth/signup", json={
            "email": "baduser@example.com",
            "username": "ab",
            "password": STRONG_PW,
        })
        assert resp.status_code == 422


class TestLoginBeforeVerification:
    def test_login_blocked_unverified(self):
        client.post("/auth/signup", json={
            "email": "unverified@example.com",
            "username": _next_username(),
            "password": STRONG_PW,
        })
        resp = client.post("/auth/login", json={
            "email": "unverified@example.com",
            "password": STRONG_PW,
        })
        assert resp.status_code == 403
        assert "not verified" in resp.json()["detail"].lower() or "email" in resp.json()["detail"].lower()


class TestEmailVerification:
    def test_verify_then_login(self):
        uname = _next_username()
        client.post("/auth/signup", json={
            "email": "verifytest@example.com",
            "username": uname,
            "password": STRONG_PW,
        })

        db = TestingSessionLocal()
        from app.models.user import User
        user = db.query(User).filter(User.email == "verifytest@example.com").first()
        assert user is not None
        assert user.is_email_verified is False

        token = create_email_verification_token(str(user.id), user.email)
        resp = client.get(f"/auth/verify-email?token={token}")
        assert resp.status_code == 200
        assert "verified" in resp.json()["message"].lower()

        resp = client.post("/auth/login", json={
            "email": "verifytest@example.com",
            "password": STRONG_PW,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "verifytest@example.com"
        assert data["user"]["username"] == uname
        assert data["user"]["is_email_verified"] is True
        db.close()

    def test_invalid_verification_token(self):
        resp = client.get("/auth/verify-email?token=invalid.token.here")
        assert resp.status_code == 400


class TestLogin:
    def _create_verified_user(self, email="login@example.com", password=STRONG_PW):
        uname = _next_username()
        client.post("/auth/signup", json={"email": email, "username": uname, "password": password})
        db = TestingSessionLocal()
        from app.models.user import User
        user = db.query(User).filter(User.email == email).first()
        user.is_email_verified = True
        db.commit()
        db.close()
        return uname

    def test_login_success(self):
        uname = self._create_verified_user()
        resp = client.post("/auth/login", json={
            "email": "login@example.com",
            "password": STRONG_PW,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == uname

    def test_login_wrong_password(self):
        self._create_verified_user()
        resp = client.post("/auth/login", json={
            "email": "login@example.com",
            "password": "WrongPass1!",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self):
        resp = client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": STRONG_PW,
        })
        assert resp.status_code == 401


class TestGoogleAuthStatus:
    def test_google_status_endpoint(self):
        resp = client.get("/auth/google/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "google_auth_enabled" in data
        assert isinstance(data["google_auth_enabled"], bool)

    def test_google_login_disabled_gracefully(self):
        resp = client.get("/auth/google/login", follow_redirects=False)
        # If Google is not configured, should return 503 (not crash)
        if resp.status_code == 503:
            assert "unavailable" in resp.json()["detail"].lower()
        else:
            # If configured, should redirect (307)
            assert resp.status_code in (302, 307)


class TestProtectedRoutes:
    def _get_auth_header(self, email="protected@example.com"):
        uname = _next_username()
        client.post("/auth/signup", json={"email": email, "username": uname, "password": STRONG_PW})
        db = TestingSessionLocal()
        from app.models.user import User
        user = db.query(User).filter(User.email == email).first()
        user.is_email_verified = True
        db.commit()
        db.close()
        resp = client.post("/auth/login", json={"email": email, "password": STRONG_PW})
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}, uname

    def test_me_requires_auth(self):
        resp = client.get("/auth/me")
        assert resp.status_code in (401, 403)

    def test_me_with_auth(self):
        headers, uname = self._get_auth_header()
        resp = client.get("/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "protected@example.com"
        assert data["username"] == uname

    def test_dashboard_requires_auth(self):
        resp = client.get("/auth/dashboard")
        assert resp.status_code in (401, 403)

    def test_dashboard_with_auth(self):
        headers, uname = self._get_auth_header("dash@example.com")
        resp = client.get("/auth/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["email"] == "dash@example.com"
        assert data["user"]["username"] == uname
        assert isinstance(data["ideas"], list)

    def test_ideas_requires_auth(self):
        resp = client.post("/ideas/", json={
            "startup_name": "Test",
            "one_line_description": "A test idea",
            "industry": "tech",
            "target_customer_type": "B2B",
            "geography": "Global",
            "customer_size": "SMB",
            "revenue_model": "Subscription",
            "pricing_estimate": 29.99,
            "estimated_cac": 100,
            "estimated_ltv": 1000,
            "team_size": 3,
            "tech_complexity": 0.5,
            "regulatory_risk": 0.2,
        })
        assert resp.status_code in (401, 403)

    def test_idea_creation_with_auth(self):
        headers, _ = self._get_auth_header("ideauser@example.com")
        resp = client.post("/ideas/", json={
            "startup_name": "TestBot",
            "one_line_description": "AI testing tool",
            "industry": "SaaS",
            "target_customer_type": "B2B",
            "geography": "Global",
            "customer_size": "SMB",
            "revenue_model": "Subscription",
            "pricing_estimate": 49.99,
            "estimated_cac": 50,
            "estimated_ltv": 500,
            "team_size": 2,
            "tech_complexity": 0.5,
            "regulatory_risk": 0.3,
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "idea_id" in data

        # Verify idea is linked to user via dashboard
        dash = client.get("/auth/dashboard", headers=headers)
        assert dash.status_code == 200
        ideas = dash.json()["ideas"]
        assert len(ideas) == 1
        assert ideas[0]["startup_name"] == "TestBot"
