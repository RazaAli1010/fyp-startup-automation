"""Pitch Deck tests — generation, retrieval, auth, Alai Slides API integration.

All tests mock the Alai Slides API since the generator requires Alai (no fallback).
The Alai Slides API returns generation_id, view_url, and pdf_url (not slide content).
"""

import os
import sys

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.services.auth_utils import create_access_token, hash_password

# ---------------------------------------------------------------------------
# Test database setup
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///./test_pitch_deck.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_user_counter = 0


def _next_username(prefix="deckuser"):
    global _user_counter
    _user_counter += 1
    return f"{prefix}_{_user_counter}"


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_verified_user(username=None):
    """Create a verified user directly in DB, return (user_id, token)."""
    from app.models.user import User
    import uuid

    db = TestingSessionLocal()
    uid = str(uuid.uuid4())
    uname = username or _next_username()
    user = User(
        id=uid,
        email=f"{uname}@test.com",
        username=uname,
        hashed_password=hash_password(STRONG_PW),
        is_email_verified=True,
        auth_provider="local",
    )
    db.add(user)
    db.commit()
    db.close()

    token = create_access_token(uid, f"{uname}@test.com", uname)
    return uid, token


def _create_idea(token, idea_data=None):
    """Submit an idea via the API, return idea_id."""
    data = idea_data or {
        "startup_name": "TestDeck Startup",
        "one_line_description": "AI-powered widget optimizer for SMBs",
        "industry": "SaaS",
        "target_customer_type": "B2B",
        "geography": "North America",
        "customer_size": "SMB",
        "revenue_model": "Subscription",
        "pricing_estimate": 49.0,
        "estimated_cac": 120.0,
        "estimated_ltv": 800.0,
        "team_size": 3,
        "tech_complexity": 0.4,
        "regulatory_risk": 0.2,
    }
    res = client.post(
        "/ideas/",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, f"Idea creation failed: {res.text}"
    return res.json()["idea_id"]


# Mock the external API calls so tests don't hit Reddit/Trend/Competitor APIs
def _mock_evaluation_signals():
    """Return a context manager that patches all external signal fetchers."""
    from app.schemas.reddit_schema import RedditPainSignals
    from app.schemas.trend_schema import TrendDemandSignals
    from app.schemas.competitor_schema import CompetitorSignals

    reddit = RedditPainSignals(
        total_posts_analyzed=10,
        complaint_post_count=5,
        avg_upvotes=15.0,
        avg_comments=8.0,
        pain_intensity_score=0.55,
        top_pain_keywords=["slow", "expensive", "buggy"],
    )
    trend = TrendDemandSignals(
        avg_search_volume=65.0,
        growth_rate_5y=0.12,
        momentum_score=0.60,
        volatility_index=0.3,
        demand_strength_score=0.65,
        trend_data_available=True,
        trend_data_source_tier="tier_1",
    )
    competitor = CompetitorSignals(
        total_competitors=3,
        competitor_names=["CompA", "CompB", "CompC"],
        avg_company_age=5.0,
        competitor_density_score=0.40,
        feature_overlap_score=0.35,
    )

    return (
        patch("app.routes.pitch_deck.fetch_reddit_pain_signals", return_value=reddit),
        patch("app.routes.pitch_deck.fetch_trend_demand_signals", return_value=trend),
        patch("app.routes.pitch_deck.fetch_competitor_signals", return_value=competitor),
    )


def _valid_alai_result():
    """Return a valid Alai Slides API result dict (generation_id + links)."""
    return {
        "generation_id": "gen_test_abc123",
        "view_url": "https://slides-api.getalai.com/view/gen_test_abc123",
        "pdf_url": "https://slides-api.getalai.com/pdf/gen_test_abc123",
    }


def _mock_alai_success():
    """Return patches that mock a successful Alai Slides API call."""
    return (
        patch("app.agents.pitch_deck_agent.generator.is_alai_available", return_value=True),
        patch(
            "app.agents.pitch_deck_agent.generator.generate_pitch_deck_via_alai",
            return_value=_valid_alai_result(),
        ),
    )


# ---------------------------------------------------------------------------
# Tests — Route-level (mock Alai + evaluation signals)
# ---------------------------------------------------------------------------

class TestPitchDeckGeneration:
    def test_generate_valid_deck(self):
        """Generate a pitch deck and verify output has Alai links."""
        uid, token = _create_verified_user()
        idea_id = _create_idea(token)

        p1, p2, p3 = _mock_evaluation_signals()
        alai_avail, alai_call = _mock_alai_success()
        with p1, p2, p3, alai_avail, alai_call:
            res = client.post(
                "/pitch-deck/generate",
                params={"idea_id": idea_id},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert res.status_code == 201, f"Generation failed: {res.text}"
        data = res.json()

        # Verify PitchDeckRecord fields
        assert "id" in data
        assert "title" in data
        assert data["status"] == "completed"
        assert data["provider"] == "alai"
        assert data["generation_id"] == "gen_test_abc123"
        assert "view_url" in data and data["view_url"]
        assert "pdf_url" in data and data["pdf_url"]
        assert "created_at" in data

    def test_generate_persists_to_db(self):
        """Generated deck is persisted and retrievable."""
        uid, token = _create_verified_user()
        idea_id = _create_idea(token)

        p1, p2, p3 = _mock_evaluation_signals()
        alai_avail, alai_call = _mock_alai_success()
        with p1, p2, p3, alai_avail, alai_call:
            gen_res = client.post(
                "/pitch-deck/generate",
                params={"idea_id": idea_id},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert gen_res.status_code == 201

        # Retrieve by idea
        get_res = client.get(
            f"/pitch-deck/idea/{idea_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_res.status_code == 200
        assert get_res.json()["id"] == gen_res.json()["id"]
        assert get_res.json()["title"] == gen_res.json()["title"]
        assert get_res.json()["status"] == "completed"
        assert get_res.json()["generation_id"] == gen_res.json()["generation_id"]
        assert get_res.json()["view_url"] == gen_res.json()["view_url"]
        assert get_res.json()["pdf_url"] == gen_res.json()["pdf_url"]

    def test_regenerate_overwrites(self):
        """Regenerating a deck for the same idea overwrites the old one."""
        uid, token = _create_verified_user()
        idea_id = _create_idea(token)

        p1, p2, p3 = _mock_evaluation_signals()
        alai_avail, alai_call = _mock_alai_success()
        with p1, p2, p3, alai_avail, alai_call:
            res1 = client.post(
                "/pitch-deck/generate",
                params={"idea_id": idea_id},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert res1.status_code == 201

        alai_avail2, alai_call2 = _mock_alai_success()
        with p1, p2, p3, alai_avail2, alai_call2:
            res2 = client.post(
                "/pitch-deck/generate",
                params={"idea_id": idea_id},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert res2.status_code == 201

        # Only one deck should exist — GET returns 200
        get_res = client.get(
            f"/pitch-deck/idea/{idea_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_res.status_code == 200
        assert get_res.json()["status"] == "completed"

    def test_output_contains_links(self):
        """Generated deck contains valid view_url and pdf_url."""
        uid, token = _create_verified_user()
        idea_id = _create_idea(token)

        p1, p2, p3 = _mock_evaluation_signals()
        alai_avail, alai_call = _mock_alai_success()
        with p1, p2, p3, alai_avail, alai_call:
            res = client.post(
                "/pitch-deck/generate",
                params={"idea_id": idea_id},
                headers={"Authorization": f"Bearer {token}"},
            )

        data = res.json()
        assert data["view_url"].startswith("https://")
        assert data["pdf_url"].startswith("https://")
        assert data["generation_id"]


class TestPitchDeckAuth:
    def test_generate_requires_auth(self):
        """POST /pitch-deck/generate without token returns 401."""
        res = client.post("/pitch-deck/generate", params={"idea_id": "fake-id"})
        assert res.status_code == 401

    def test_get_requires_auth(self):
        """GET /pitch-deck/{id} without token returns 401."""
        res = client.get("/pitch-deck/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 401

    def test_get_by_idea_requires_auth(self):
        """GET /pitch-deck/idea/{id} without token returns 401."""
        res = client.get("/pitch-deck/idea/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 401

    def test_get_nonexistent_returns_404(self):
        """GET for a non-existent deck returns 404."""
        uid, token = _create_verified_user()
        res = client.get(
            "/pitch-deck/idea/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404

    def test_list_decks_requires_auth(self):
        """GET /pitch-deck/ without token returns 401."""
        res = client.get("/pitch-deck/")
        assert res.status_code == 401

    def test_list_decks_empty(self):
        """GET /pitch-deck/ with no decks returns empty list."""
        uid, token = _create_verified_user()
        res = client.get(
            "/pitch-deck/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["pitch_decks"] == []


# ---------------------------------------------------------------------------
# Tests — Unit generator (mock Alai, no DB)
# ---------------------------------------------------------------------------

class TestPitchDeckUnitGenerator:
    """Unit tests for the generator function directly (no API/DB).

    Since the generator REQUIRES Alai (no fallback), all tests mock Alai.
    """

    def test_generator_returns_valid_output(self):
        from app.agents.pitch_deck_agent.generator import generate_pitch_deck

        with (
            patch("app.agents.pitch_deck_agent.generator.is_alai_available", return_value=True),
            patch(
                "app.agents.pitch_deck_agent.generator.generate_pitch_deck_via_alai",
                return_value=_valid_alai_result(),
            ),
        ):
            deck = generate_pitch_deck(
                idea_name="UnitTest Co",
                idea_description="A test startup for unit testing",
                idea_industry="Testing",
                idea_target_customer="B2B",
                idea_geography="Global",
                idea_revenue_model="Subscription",
                idea_pricing_estimate=99.0,
                idea_team_size=2,
                final_score=52.3,
                verdict="Moderate",
                risk_level="Medium",
                key_strength="Market Timing",
                key_risk="Problem Intensity",
                problem_intensity=40.0,
                market_timing=58.0,
                competition_pressure=75.0,
                market_potential=55.0,
                execution_feasibility=60.0,
            )

        assert deck.deck_title == "UnitTest Co"
        assert deck.provider == "alai"
        assert deck.generation_id == "gen_test_abc123"
        assert deck.view_url.startswith("https://")
        assert deck.pdf_url.startswith("https://")

        # Validate JSON serialization round-trip
        json_str = deck.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["deck_title"] == "UnitTest Co"
        assert parsed["provider"] == "alai"
        assert parsed["generation_id"] == "gen_test_abc123"

    def test_tagline_early_stage_for_low_score(self):
        """Low-score ideas get 'early-stage concept' tagline."""
        from app.agents.pitch_deck_agent.generator import generate_pitch_deck

        with (
            patch("app.agents.pitch_deck_agent.generator.is_alai_available", return_value=True),
            patch(
                "app.agents.pitch_deck_agent.generator.generate_pitch_deck_via_alai",
                return_value=_valid_alai_result(),
            ),
        ):
            deck = generate_pitch_deck(
                idea_name="LowScore Co",
                idea_description="A low-scoring startup",
                idea_industry="EdTech",
                idea_target_customer="B2C",
                idea_geography="India",
                idea_revenue_model="One-time",
                idea_pricing_estimate=10.0,
                idea_team_size=1,
                final_score=35.0,
                verdict="Weak",
                risk_level="High",
                key_strength="Execution Feasibility",
                key_risk="Problem Intensity",
                problem_intensity=20.0,
                market_timing=30.0,
                competition_pressure=40.0,
                market_potential=25.0,
                execution_feasibility=50.0,
            )

        assert "early-stage" in deck.tagline.lower()

    def test_tagline_validated_for_high_score(self):
        """High-score ideas get 'validated opportunity' tagline."""
        from app.agents.pitch_deck_agent.generator import generate_pitch_deck

        with (
            patch("app.agents.pitch_deck_agent.generator.is_alai_available", return_value=True),
            patch(
                "app.agents.pitch_deck_agent.generator.generate_pitch_deck_via_alai",
                return_value=_valid_alai_result(),
            ),
        ):
            deck = generate_pitch_deck(
                idea_name="HighScore Inc",
                idea_description="A high-scoring startup",
                idea_industry="FinTech",
                idea_target_customer="B2C",
                idea_geography="USA",
                idea_revenue_model="Subscription",
                idea_pricing_estimate=29.0,
                idea_team_size=5,
                final_score=80.0,
                verdict="Strong",
                risk_level="Low",
                key_strength="Market Timing",
                key_risk="Competition Pressure",
                problem_intensity=85.0,
                market_timing=78.0,
                competition_pressure=70.0,
                market_potential=82.0,
                execution_feasibility=75.0,
            )

        assert "validated opportunity" in deck.tagline.lower()

    def test_missing_key_raises_error(self):
        """When ALAI_API_KEY is missing, generator raises AlaiError — no fallback."""
        from app.agents.pitch_deck_agent.generator import generate_pitch_deck
        from app.services.alai_client import AlaiError

        with patch("app.agents.pitch_deck_agent.generator.is_alai_available", return_value=False):
            with pytest.raises(AlaiError, match="Alai API key missing"):
                generate_pitch_deck(
                    idea_name="NoKey Co",
                    idea_description="Testing missing key",
                    idea_industry="SaaS",
                    idea_target_customer="B2B",
                    idea_geography="US",
                    idea_revenue_model="Subscription",
                    idea_pricing_estimate=50.0,
                    idea_team_size=2,
                    final_score=55.0,
                    verdict="Moderate",
                    risk_level="Medium",
                    key_strength="Market Timing",
                    key_risk="Problem Intensity",
                    problem_intensity=45.0,
                    market_timing=55.0,
                    competition_pressure=60.0,
                    market_potential=50.0,
                    execution_feasibility=55.0,
                )

    def test_alai_error_propagates(self):
        """When Alai API raises an error, it propagates — no fallback."""
        from app.agents.pitch_deck_agent.generator import generate_pitch_deck
        from app.services.alai_client import AlaiError

        with (
            patch("app.agents.pitch_deck_agent.generator.is_alai_available", return_value=True),
            patch(
                "app.agents.pitch_deck_agent.generator.generate_pitch_deck_via_alai",
                side_effect=AlaiError("API timeout"),
            ),
        ):
            with pytest.raises(AlaiError, match="API timeout"):
                generate_pitch_deck(
                    idea_name="AlaiErr Co",
                    idea_description="Testing Alai error",
                    idea_industry="FinTech",
                    idea_target_customer="B2C",
                    idea_geography="EU",
                    idea_revenue_model="Subscription",
                    idea_pricing_estimate=30.0,
                    idea_team_size=3,
                    final_score=60.0,
                    verdict="Moderate",
                    risk_level="Medium",
                    key_strength="Market Potential",
                    key_risk="Competition Pressure",
                    problem_intensity=50.0,
                    market_timing=55.0,
                    competition_pressure=45.0,
                    market_potential=65.0,
                    execution_feasibility=60.0,
                )

    def test_alai_missing_links_raises_error(self):
        """When Alai returns result without links, AlaiError propagates."""
        from app.agents.pitch_deck_agent.generator import generate_pitch_deck
        from app.services.alai_client import AlaiError

        bad_result = {"generation_id": "gen_123", "view_url": "", "pdf_url": ""}

        with (
            patch("app.agents.pitch_deck_agent.generator.is_alai_available", return_value=True),
            patch(
                "app.agents.pitch_deck_agent.generator.generate_pitch_deck_via_alai",
                return_value=bad_result,
            ),
        ):
            with pytest.raises(AlaiError, match="missing required fields"):
                generate_pitch_deck(
                    idea_name="NoLinks Co",
                    idea_description="Testing missing links",
                    idea_industry="EdTech",
                    idea_target_customer="B2C",
                    idea_geography="India",
                    idea_revenue_model="Freemium",
                    idea_pricing_estimate=0.0,
                    idea_team_size=1,
                    final_score=40.0,
                    verdict="Weak",
                    risk_level="High",
                    key_strength="Execution Feasibility",
                    key_risk="Problem Intensity",
                    problem_intensity=30.0,
                    market_timing=35.0,
                    competition_pressure=50.0,
                    market_potential=40.0,
                    execution_feasibility=55.0,
                )


# ---------------------------------------------------------------------------
# Tests — Alai integration (route-level error handling)
# ---------------------------------------------------------------------------

class TestAlaiIntegration:
    """Tests for Alai Slides API integration — mocked, no real API calls."""

    def test_missing_alai_key_returns_503(self):
        """When ALAI_API_KEY is empty, route returns HTTP 503."""
        uid, token = _create_verified_user()
        idea_id = _create_idea(token)

        p1, p2, p3 = _mock_evaluation_signals()
        with (
            p1, p2, p3,
            patch("app.agents.pitch_deck_agent.generator.is_alai_available", return_value=False),
        ):
            res = client.post(
                "/pitch-deck/generate",
                params={"idea_id": idea_id},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert res.status_code == 503
        assert "Alai" in res.json()["detail"]

    def test_alai_api_error_returns_503(self):
        """When Alai API raises an error, route returns HTTP 503."""
        from app.services.alai_client import AlaiError

        uid, token = _create_verified_user()
        idea_id = _create_idea(token)

        p1, p2, p3 = _mock_evaluation_signals()
        with (
            p1, p2, p3,
            patch("app.agents.pitch_deck_agent.generator.is_alai_available", return_value=True),
            patch(
                "app.agents.pitch_deck_agent.generator.generate_pitch_deck_via_alai",
                side_effect=AlaiError("Connection refused"),
            ),
        ):
            res = client.post(
                "/pitch-deck/generate",
                params={"idea_id": idea_id},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert res.status_code == 503
        assert "Alai service unavailable" in res.json()["detail"]

    def test_alai_success_returns_links(self):
        """When Alai returns valid result, response includes links."""
        uid, token = _create_verified_user()
        idea_id = _create_idea(token)

        p1, p2, p3 = _mock_evaluation_signals()
        alai_avail, alai_call = _mock_alai_success()
        with p1, p2, p3, alai_avail, alai_call:
            res = client.post(
                "/pitch-deck/generate",
                params={"idea_id": idea_id},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "completed"
        assert data["provider"] == "alai"
        assert data["generation_id"] == "gen_test_abc123"
        assert data["view_url"].startswith("https://")
        assert data["pdf_url"].startswith("https://")

    def test_input_text_builder(self):
        """Verify _build_input_text produces structured text with all fields."""
        from app.agents.pitch_deck_agent.generator import _build_input_text
        from app.agents.pitch_deck_agent.schema import (
            IdeaContext, ModuleScoresContext, PitchDeckInput, ValidationContext,
        )

        ctx = PitchDeckInput(
            idea=IdeaContext(
                name="TestCo", description="Test startup", industry="SaaS",
                target_customer="B2B", geography="US", revenue_model="Subscription",
                pricing_estimate=50.0, team_size=3,
            ),
            validation=ValidationContext(
                final_score=65.0, verdict="Moderate", risk_level="Medium",
                key_strength="Market Timing", key_risk="Problem Intensity",
                module_scores=ModuleScoresContext(
                    problem_intensity=50.0, market_timing=68.0,
                    competition_pressure=55.0, market_potential=60.0,
                    execution_feasibility=58.0,
                ),
            ),
        )

        text = _build_input_text(ctx)
        assert "TestCo" in text
        assert "SaaS" in text
        assert "65.0/100" in text
        assert "Market Timing" in text
        assert "investor-grade" in text

    def test_input_text_conservative_for_low_score(self):
        """Low-score ideas get conservative language guidance in input_text."""
        from app.agents.pitch_deck_agent.generator import _build_input_text
        from app.agents.pitch_deck_agent.schema import (
            IdeaContext, ModuleScoresContext, PitchDeckInput, ValidationContext,
        )

        ctx = PitchDeckInput(
            idea=IdeaContext(
                name="LowCo", description="Low score test", industry="EdTech",
                target_customer="B2C", geography="India", revenue_model="One-time",
                pricing_estimate=10.0, team_size=1,
            ),
            validation=ValidationContext(
                final_score=30.0, verdict="Weak", risk_level="High",
                key_strength="Execution Feasibility", key_risk="Problem Intensity",
                module_scores=ModuleScoresContext(
                    problem_intensity=20.0, market_timing=25.0,
                    competition_pressure=40.0, market_potential=30.0,
                    execution_feasibility=50.0,
                ),
            ),
        )

        text = _build_input_text(ctx)
        assert "conservative" in text.lower()
        assert "education" in text.lower() or "awareness" in text.lower()
