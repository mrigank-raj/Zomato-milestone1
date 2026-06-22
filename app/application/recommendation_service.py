"""
RecommendationService — orchestrates the full recommendation workflow.

Pipeline (from implementation-plan.md Phase 4):
  1. Validate user preferences
  2. Filter restaurants → candidates
  3. If empty → return [] (no LLM call)
  4. Build LLM prompt
  5. Call Groq (with retry on transient error)
  6. Parse response
  7. Return recommendations

Error handling (from architecture.md §11):
  - Validation errors → do not call LLM
  - Zero candidates  → skip LLM, return empty
  - Groq failure     → retry once, then fallback to rating-sorted list
"""

import logging
import time
from app.domain.models import UserPreferences, Restaurant, Recommendation
from app.domain.validator import InputValidator, ValidationError
from app.domain.filter import RestaurantFilter
from app.domain.budget import BudgetMapper
from app.domain.prompt_builder import PromptBuilder
from app.domain.response_parser import LLMResponseParser
from app.infrastructure.llm.base import LLMClient
from app.infrastructure.config import AppConfig

logger = logging.getLogger("zomato-rec")


class RecommendationService:
    """Single entry point for the recommendation workflow.

    Usage:
        service = RecommendationService(restaurants, llm_client, config)
        recs = service.get_recommendations(prefs)
    """

    def __init__(
        self,
        restaurants: list[Restaurant],
        llm_client: LLMClient,
        config: AppConfig,
        known_locations: set[str] | None = None,
    ):
        self.restaurants = restaurants
        self.llm_client = llm_client
        self.config = config

        # Build sub-components
        self.validator = InputValidator(known_locations=known_locations)
        self.budget_mapper = BudgetMapper()
        self.filter = RestaurantFilter(
            budget_mapper=self.budget_mapper,
            max_candidates=config.max_candidates,
        )
        self.prompt_builder = PromptBuilder(config)
        self.response_parser = LLMResponseParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_recommendations(self, prefs: UserPreferences) -> list[Recommendation]:
        """Run the full recommendation pipeline.

        Args:
            prefs: Validated UserPreferences (if coming from the UI, the
                   presentation layer may pre-validate; the service validates
                   again defensively).

        Returns:
            A list of Recommendation objects (may be empty).

        Raises:
            ValidationError: If user preferences are invalid.
        """
        # Step 1 — validate (defensive; UI may have already done this)
        logger.info("Step 1/6: Validating user preferences...")
        prefs = self.validator.validate(
            location=prefs.location,
            budget=prefs.budget,
            cuisine=prefs.cuisine,
            min_rating=prefs.min_rating,
            additional=prefs.additional,
            top_n=prefs.top_n,
        )
        logger.info(f"  Preferences valid: {prefs.location}, {prefs.cuisine}, "
                     f"budget={prefs.budget}, min_rating={prefs.min_rating}")

        # Step 2 — filter
        logger.info("Step 2/6: Filtering restaurants...")
        candidates = self.filter.apply(self.restaurants, prefs)
        logger.info(f"  {len(candidates)} candidate(s) after filtering.")

        # Step 3 — empty guard
        if not candidates:
            logger.info("Step 3/6: No candidates found — skipping LLM call.")
            return []

        # Step 4 — build prompt
        logger.info("Step 4/6: Building LLM prompt...")
        llm_request = self.prompt_builder.build(prefs, candidates)

        # Step 5 — call Groq (with 1 retry)
        logger.info("Step 5/6: Calling Groq LLM...")
        raw_response = self._call_llm_with_retry(llm_request)

        # Step 6 — parse response
        logger.info("Step 6/6: Parsing LLM response...")
        recommendations = self.response_parser.parse(raw_response, candidates)

        # Truncate to requested top_n
        recommendations = recommendations[: prefs.top_n]
        logger.info(f"  Returning {len(recommendations)} recommendation(s).")
        return recommendations

    # ------------------------------------------------------------------
    # Helpers (convenience for building from config)
    # ------------------------------------------------------------------

    @staticmethod
    def from_config(
        restaurants: list[Restaurant],
        config: AppConfig,
        known_locations: set[str] | None = None,
    ) -> "RecommendationService":
        """Factory that wires up the LLM client from config.

        Raises ValueError if GROQ_API_KEY is missing.
        """
        config.validate()  # ensures GROQ_API_KEY is set
        from app.infrastructure.config import get_llm_client
        llm_client = get_llm_client(config)
        return RecommendationService(
            restaurants=restaurants,
            llm_client=llm_client,
            config=config,
            known_locations=known_locations,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call_llm_with_retry(self, llm_request, max_retries: int = 1) -> str:
        """Call the LLM with one automatic retry on transient failure.

        On final failure, returns an empty string so the response parser
        falls back to rating-sorted results.
        """
        last_error = None
        for attempt in range(1 + max_retries):
            try:
                raw = self.llm_client.complete(llm_request)
                return raw
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait = 2 ** attempt  # 1s, then 2s
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}): {e}. "
                        f"Retrying in {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"LLM call failed after {max_retries + 1} attempts: {e}")

        # Fallback: return empty string → parser will produce rating-sorted fallback
        logger.warning("Returning empty LLM response — parser will use rating-sorted fallback.")
        return ""
