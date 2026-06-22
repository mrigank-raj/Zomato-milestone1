"""
FastAPI server — thin REST API wrapping the RecommendationService.

Endpoints:
  GET  /api/metadata          → unique locations & cuisines for dropdowns
  POST /api/recommendations   → accepts UserPreferences, returns recommendations

Run:
  uvicorn app.server:app --reload --port 8000
"""

import os
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.infrastructure.config import AppConfig
from app.infrastructure.dataset_loader import DatasetLoader
from app.domain.models import UserPreferences
from app.domain.validator import ValidationError
from app.application.recommendation_service import RecommendationService

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("zomato-rec")

# ── Module-level singletons (populated in lifespan) ──────────────
_service: RecommendationService | None = None
_locations: list[str] = []
_cuisines: list[str] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load dataset and build service once at startup."""
    global _service, _locations, _cuisines

    logger.info("Starting up — loading dataset...")
    config = AppConfig()

    loader = DatasetLoader(config)
    restaurants = loader.load()
    logger.info(f"Loaded {len(restaurants)} restaurants.")

    # Unique sorted locations & cuisines for the frontend dropdowns
    location_set: set[str] = set()
    cuisine_set: set[str] = set()
    for r in restaurants:
        location_set.add(r.location)
        for c in r.cuisines:
            cuisine_set.add(c)

    _locations = sorted(location_set)
    _cuisines = sorted(cuisine_set)
    logger.info(f"Unique locations: {len(_locations)}, cuisines: {len(_cuisines)}")

    # Build the service (validates API key)
    try:
        config.validate()
        known_locations = {loc.lower() for loc in _locations}
        _service = RecommendationService.from_config(
            restaurants=restaurants,
            config=config,
            known_locations=known_locations,
        )
        logger.info("RecommendationService ready.")
    except ValueError as e:
        logger.error(f"Config validation failed: {e}")
        logger.warning("Server will start but /api/recommendations will fail until GROQ_API_KEY is set.")

    yield  # app is running

    logger.info("Shutting down.")


# ── FastAPI app ──────────────────────────────────────────────────
app = FastAPI(
    title="Zomato AI Recommender API",
    version="1.0.0",
    lifespan=lifespan,
)

allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]
else:
    origins = ["*"]

allow_credentials = True
if "*" in origins:
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response schemas ───────────────────────────────────

class PreferencesRequest(BaseModel):
    location: str
    budget: str = "medium"
    cuisine: str
    min_rating: float = Field(default=3.5, ge=0.0, le=5.0)
    additional: str | None = None
    top_n: int = Field(default=5, ge=1, le=20)


class RestaurantResponse(BaseModel):
    id: str
    name: str
    location: str
    cuisines: list[str]
    rating: float
    cost_for_two: int | None
    address: str | None
    votes: int | None


class RecommendationResponse(BaseModel):
    rank: int
    restaurant: RestaurantResponse
    explanation: str
    summary: str | None


class MetadataResponse(BaseModel):
    locations: list[str]
    cuisines: list[str]


# ── Endpoints ────────────────────────────────────────────────────

@app.get("/api/metadata", response_model=MetadataResponse)
async def get_metadata():
    """Return unique locations and cuisines for frontend dropdowns."""
    return MetadataResponse(locations=_locations, cuisines=_cuisines)


@app.post("/api/recommendations", response_model=list[RecommendationResponse])
async def get_recommendations(body: PreferencesRequest):
    """Run the full recommendation pipeline and return results."""
    if _service is None:
        raise HTTPException(
            status_code=503,
            detail="Service not ready. Check that GROQ_API_KEY is configured.",
        )

    prefs = UserPreferences(
        location=body.location,
        budget=body.budget,
        cuisine=body.cuisine,
        min_rating=body.min_rating,
        additional=body.additional,
        top_n=body.top_n,
    )

    try:
        recs = _service.get_recommendations(prefs)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors)
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return [
        RecommendationResponse(
            rank=rec.rank,
            restaurant=RestaurantResponse(
                id=rec.restaurant.id,
                name=rec.restaurant.name,
                location=rec.restaurant.location,
                cuisines=rec.restaurant.cuisines,
                rating=rec.restaurant.rating,
                cost_for_two=rec.restaurant.cost_for_two,
                address=rec.restaurant.address,
                votes=rec.restaurant.votes,
            ),
            explanation=rec.explanation,
            summary=rec.summary,
        )
        for rec in recs
    ]
