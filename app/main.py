"""
CLI entry point for the AI-Powered Restaurant Recommendation System.

Supports two modes:
  1. Interactive — prompts the user for preferences via stdin.
  2. Quick args  — pass --location, --budget, etc. on the command line.

Usage:
  python -m app.main
  python -m app.main --location Bangalore --budget medium --cuisine "North Indian" --min-rating 4.0
"""

import sys
import argparse
import logging
from app.infrastructure.config import AppConfig
from app.infrastructure.dataset_loader import DatasetLoader
from app.domain.models import UserPreferences
from app.domain.validator import ValidationError


def _setup_logging(config: AppConfig) -> logging.Logger:
    """Configure root logging and return the app logger."""
    numeric_level = getattr(logging, config.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("zomato-rec")


def _parse_args() -> argparse.Namespace:
    """Parse optional CLI arguments for non-interactive usage."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Restaurant Recommendation System"
    )
    parser.add_argument("--location",   type=str, default=None, help="City/area name")
    parser.add_argument("--budget",     type=str, default=None, help="low | medium | high")
    parser.add_argument("--cuisine",    type=str, default=None, help="Cuisine type")
    parser.add_argument("--min-rating", type=float, default=None, dest="min_rating", help="Minimum rating (0-5)")
    parser.add_argument("--additional", type=str, default=None, help="Extra preferences (free text)")
    parser.add_argument("--top-n",      type=int, default=5, dest="top_n", help="Number of recommendations")
    return parser.parse_args()


def _collect_interactive_prefs() -> UserPreferences:
    """Prompt the user for preferences via stdin."""
    print("\n" + "=" * 60)
    print("  🍽️  Restaurant Recommendation System — Interactive Mode")
    print("=" * 60 + "\n")

    location   = input("📍 Location (e.g. Bangalore): ").strip()
    budget     = input("💰 Budget (low / medium / high): ").strip().lower()
    cuisine    = input("🍕 Cuisine (e.g. North Indian): ").strip()

    rating_str = input("⭐ Minimum rating (0.0 – 5.0) [default 3.5]: ").strip()
    min_rating = float(rating_str) if rating_str else 3.5

    additional = input("📝 Additional preferences (optional): ").strip() or None

    top_n_str  = input("🔢 How many recommendations? [default 5]: ").strip()
    top_n      = int(top_n_str) if top_n_str else 5

    return UserPreferences(
        location=location,
        budget=budget,
        cuisine=cuisine,
        min_rating=min_rating,
        additional=additional,
        top_n=top_n,
    )


def _print_recommendations(recs):
    """Pretty-print recommendations to the terminal."""
    if not recs:
        print("\n⚠️  No restaurants matched your criteria. Try relaxing your filters.\n")
        return

    # Print summary (from the first recommendation, if available)
    if recs[0].summary:
        print(f"\n📋 Summary: {recs[0].summary}\n")

    print(f"{'─' * 60}")
    for rec in recs:
        r = rec.restaurant
        cuisines_str = ", ".join(r.cuisines) if r.cuisines else "N/A"
        cost_str = f"₹{r.cost_for_two}" if r.cost_for_two else "N/A"

        print(f"  #{rec.rank}  {r.name}")
        print(f"       📍 {r.location}  |  🍽️ {cuisines_str}")
        print(f"       ⭐ {r.rating}/5  |  💰 {cost_str} for two")
        if r.address:
            print(f"       🏠 {r.address}")
        print(f"       💬 {rec.explanation}")
        print(f"{'─' * 60}")

    print()


def main():
    # ── Configuration ────────────────────────────────────────────
    config = AppConfig()
    logger = _setup_logging(config)
    logger.info("Initializing AI-Powered Restaurant Recommendation System...")

    logger.info("Loaded Configuration:")
    logger.info(f"  - LLM Model: {config.llm_model}")
    logger.info(f"  - LLM Temperature: {config.llm_temperature}")
    logger.info(f"  - Max Candidates: {config.max_candidates}")
    logger.info(f"  - Dataset Cache Path: {config.dataset_cache_path}")
    logger.info(f"  - Log Level: {config.log_level}")

    # ── Validate API key ─────────────────────────────────────────
    try:
        config.validate()
        logger.info("Configuration validation: SUCCESS")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n❌ {e}")
        print("   Set GROQ_API_KEY in your .env file and try again.\n")
        sys.exit(1)

    # ── Load dataset ─────────────────────────────────────────────
    loader = DatasetLoader(config)
    try:
        restaurants = loader.load()
        logger.info(f"Successfully loaded {len(restaurants)} restaurants.")
    except Exception as e:
        logger.error(f"Error loading dataset: {e}")
        print(f"\n❌ Failed to load dataset: {e}\n")
        sys.exit(1)

    # ── Build known locations for soft-validation ────────────────
    known_locations = {r.location.lower() for r in restaurants}
    logger.info(f"Unique locations in dataset: {len(known_locations)}")

    # ── Build RecommendationService ──────────────────────────────
    from app.application.recommendation_service import RecommendationService

    service = RecommendationService.from_config(
        restaurants=restaurants,
        config=config,
        known_locations=known_locations,
    )

    # ── Collect preferences ──────────────────────────────────────
    args = _parse_args()

    if args.location:
        # Non-interactive mode: build prefs from CLI args
        prefs = UserPreferences(
            location=args.location,
            budget=args.budget or "medium",
            cuisine=args.cuisine or "",
            min_rating=args.min_rating if args.min_rating is not None else 3.5,
            additional=args.additional,
            top_n=args.top_n,
        )
    else:
        # Interactive mode
        prefs = _collect_interactive_prefs()

    # ── Run recommendation pipeline ──────────────────────────────
    try:
        recs = service.get_recommendations(prefs)
        _print_recommendations(recs)
    except ValidationError as e:
        print(f"\n❌ Validation error(s):")
        for err in e.errors:
            print(f"   • {err}")
        print()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ An error occurred: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
