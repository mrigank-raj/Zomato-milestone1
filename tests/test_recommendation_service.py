"""
Integration tests for RecommendationService (Phase 4).

Uses a mock LLM client — no real Groq API calls.
"""

import json
import pytest
from app.domain.models import UserPreferences, Restaurant, Recommendation
from app.domain.validator import ValidationError
from app.infrastructure.config import AppConfig
from app.application.recommendation_service import RecommendationService


# ── Fixtures ──────────────────────────────────────────────────────


class MockLLMClient:
    """Mock LLM client that returns a deterministic JSON response."""

    def __init__(self, response: str | None = None, should_fail: bool = False):
        self._response = response
        self._should_fail = should_fail
        self.call_count = 0

    def complete(self, request):
        self.call_count += 1
        if self._should_fail:
            raise RuntimeError("Simulated Groq API error")
        return self._response or ""


def _make_restaurants() -> list[Restaurant]:
    """Create a small fixture restaurant list."""
    return [
        Restaurant(
            id="0", name="Spice Garden", location="Bangalore",
            cuisines=["North Indian", "Chinese"], rating=4.5,
            cost_for_two=800, address="MG Road", votes=200, raw={}
        ),
        Restaurant(
            id="1", name="Pasta Palace", location="Bangalore",
            cuisines=["Italian", "Continental"], rating=4.2,
            cost_for_two=1200, address="Indiranagar", votes=150, raw={}
        ),
        Restaurant(
            id="2", name="Dosa Corner", location="Bangalore",
            cuisines=["South Indian"], rating=4.8,
            cost_for_two=300, address="Koramangala", votes=500, raw={}
        ),
        Restaurant(
            id="3", name="Burger Barn", location="Mumbai",
            cuisines=["American", "Fast Food"], rating=4.0,
            cost_for_two=600, address="Bandra", votes=80, raw={}
        ),
        Restaurant(
            id="4", name="Tandoori Nights", location="Bangalore",
            cuisines=["North Indian", "Mughlai"], rating=3.8,
            cost_for_two=900, address="Whitefield", votes=60, raw={}
        ),
    ]


def _make_config() -> AppConfig:
    return AppConfig(
        groq_api_key="test-key",
        llm_model="test-model",
        llm_temperature=0.1,
        max_candidates=20,
    )


def _successful_llm_response(candidate_ids: list[str]) -> str:
    """Build a mock LLM JSON response using the given candidate IDs."""
    recs = [
        {
            "restaurant_id": cid,
            "rank": i + 1,
            "explanation": f"Great choice #{i + 1} for your preferences."
        }
        for i, cid in enumerate(candidate_ids)
    ]
    return json.dumps({"recommendations": recs, "summary": "Here are your top picks!"})


# ── Tests ─────────────────────────────────────────────────────────


class TestRecommendationServiceHappyPath:
    """End-to-end happy path through the service."""

    def test_returns_recommendations_for_valid_prefs(self):
        restaurants = _make_restaurants()
        config = _make_config()

        # Only id="0" (Spice Garden) and id="4" (Tandoori Nights) are
        # Bangalore + North Indian + medium budget (501-1500).
        # Spice Garden has higher rating so LLM gets it first.
        mock_response = _successful_llm_response(["0", "4"])
        mock_client = MockLLMClient(response=mock_response)

        service = RecommendationService(restaurants, mock_client, config)

        prefs = UserPreferences(
            location="Bangalore",
            budget="medium",
            cuisine="North Indian",
            min_rating=3.5,
            additional="family-friendly",
            top_n=5,
        )

        recs = service.get_recommendations(prefs)

        assert len(recs) == 2
        assert recs[0].restaurant.name == "Spice Garden"
        assert recs[1].restaurant.name == "Tandoori Nights"
        assert mock_client.call_count == 1

    def test_top_n_limits_results(self):
        restaurants = _make_restaurants()
        config = _make_config()

        mock_response = _successful_llm_response(["0", "4"])
        mock_client = MockLLMClient(response=mock_response)

        service = RecommendationService(restaurants, mock_client, config)

        prefs = UserPreferences(
            location="Bangalore",
            budget="medium",
            cuisine="North Indian",
            min_rating=3.5,
            additional=None,
            top_n=1,  # only want 1
        )

        recs = service.get_recommendations(prefs)
        assert len(recs) == 1


class TestRecommendationServiceEmptyResults:
    """When no restaurants match, the LLM should NOT be called."""

    def test_no_candidates_skips_llm(self):
        restaurants = _make_restaurants()
        config = _make_config()

        mock_client = MockLLMClient(response="should not be called")
        service = RecommendationService(restaurants, mock_client, config)

        # Impossible filter: no Italian restaurants with min_rating 5.0 in Bangalore
        prefs = UserPreferences(
            location="Bangalore",
            budget="medium",
            cuisine="Italian",
            min_rating=5.0,
            additional=None,
            top_n=5,
        )

        recs = service.get_recommendations(prefs)

        assert recs == []
        assert mock_client.call_count == 0  # LLM never called

    def test_unknown_location_returns_empty(self):
        restaurants = _make_restaurants()
        config = _make_config()

        mock_client = MockLLMClient()
        service = RecommendationService(restaurants, mock_client, config)

        prefs = UserPreferences(
            location="Timbuktu",
            budget="low",
            cuisine="North Indian",
            min_rating=0.0,
            additional=None,
        )

        recs = service.get_recommendations(prefs)
        assert recs == []
        assert mock_client.call_count == 0


class TestRecommendationServiceValidation:
    """Validation errors should prevent the LLM from being called."""

    def test_empty_location_raises_validation_error(self):
        restaurants = _make_restaurants()
        config = _make_config()
        mock_client = MockLLMClient()

        service = RecommendationService(restaurants, mock_client, config)

        prefs = UserPreferences(
            location="",
            budget="medium",
            cuisine="Italian",
            min_rating=4.0,
            additional=None,
        )

        with pytest.raises(ValidationError) as exc_info:
            service.get_recommendations(prefs)

        assert "Location is required" in str(exc_info.value)
        assert mock_client.call_count == 0

    def test_invalid_budget_raises_validation_error(self):
        restaurants = _make_restaurants()
        config = _make_config()
        mock_client = MockLLMClient()

        service = RecommendationService(restaurants, mock_client, config)

        prefs = UserPreferences(
            location="Bangalore",
            budget="super_expensive",
            cuisine="Italian",
            min_rating=4.0,
            additional=None,
        )

        with pytest.raises(ValidationError):
            service.get_recommendations(prefs)

        assert mock_client.call_count == 0


class TestRecommendationServiceLLMFailure:
    """When the LLM fails, the service should gracefully degrade."""

    def test_llm_failure_returns_fallback_recommendations(self):
        restaurants = _make_restaurants()
        config = _make_config()

        # Client that always fails
        mock_client = MockLLMClient(should_fail=True)
        service = RecommendationService(restaurants, mock_client, config)

        prefs = UserPreferences(
            location="Bangalore",
            budget="medium",
            cuisine="North Indian",
            min_rating=3.5,
            additional=None,
            top_n=5,
        )

        recs = service.get_recommendations(prefs)

        # Should still get fallback (rating-sorted) results
        assert len(recs) > 0
        assert recs[0].restaurant.rating >= recs[-1].restaurant.rating
        # LLM was called twice (initial + 1 retry)
        assert mock_client.call_count == 2

    def test_llm_returns_malformed_json_uses_fallback(self):
        restaurants = _make_restaurants()
        config = _make_config()

        mock_client = MockLLMClient(response="this is not json at all!!!")
        service = RecommendationService(restaurants, mock_client, config)

        prefs = UserPreferences(
            location="Bangalore",
            budget="medium",
            cuisine="North Indian",
            min_rating=3.5,
            additional=None,
            top_n=5,
        )

        recs = service.get_recommendations(prefs)

        # Fallback to rating-sorted
        assert len(recs) > 0
        assert "Fallback" in (recs[0].summary or "")
