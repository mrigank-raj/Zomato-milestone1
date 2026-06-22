"""
InputValidator — validates and normalizes raw user input into a typed UserPreferences.

Validation rules (from architecture.md §8.2 and implementation-plan.md Phase 2):
  - location:   non-empty string
  - budget:     must be one of "low", "medium", "high"
  - cuisine:    non-empty string
  - min_rating: float in [0.0, 5.0]
  - additional: optional free text (None OK)
"""

import logging
from app.domain.models import UserPreferences

logger = logging.getLogger("zomato-rec")

VALID_BUDGETS = {"low", "medium", "high"}


class ValidationError(Exception):
    """Raised when user input fails validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class InputValidator:
    """Validates raw user preferences and returns a clean UserPreferences object."""

    def __init__(self, known_locations: set[str] | None = None):
        """
        Args:
            known_locations: Optional set of known location strings (lowercased)
                             for soft validation. If provided, a warning is
                             logged for unknown locations but no error is raised.
        """
        self.known_locations = known_locations

    def validate(
        self,
        location: str,
        budget: str,
        cuisine: str,
        min_rating: float,
        additional: str | None = None,
        top_n: int = 5,
    ) -> UserPreferences:
        """Validate and normalize inputs.

        Returns a UserPreferences dataclass on success.
        Raises ValidationError with a list of error messages on failure.
        """
        errors: list[str] = []

        # --- Location ---
        location = (location or "").strip()
        if not location:
            errors.append("Location is required.")

        if self.known_locations and location and location.lower() not in self.known_locations:
            logger.warning(f"Location '{location}' not found in known dataset locations. Results may be empty.")

        # --- Budget ---
        budget = (budget or "").strip().lower()
        if budget not in VALID_BUDGETS:
            errors.append(f"Budget must be one of {sorted(VALID_BUDGETS)}. Got: '{budget}'.")

        # --- Cuisine ---
        cuisine = (cuisine or "").strip()
        if not cuisine:
            errors.append("Cuisine is required.")

        # --- Min rating ---
        try:
            min_rating = float(min_rating)
        except (TypeError, ValueError):
            errors.append(f"Minimum rating must be a number. Got: '{min_rating}'.")
            min_rating = 0.0

        if not (0.0 <= min_rating <= 5.0):
            errors.append(f"Minimum rating must be between 0.0 and 5.0. Got: {min_rating}.")

        # --- Additional ---
        if additional is not None:
            additional = additional.strip() or None

        # --- top_n ---
        if top_n < 1:
            errors.append(f"top_n must be at least 1. Got: {top_n}.")

        if errors:
            raise ValidationError(errors)

        return UserPreferences(
            location=location,
            budget=budget,
            cuisine=cuisine,
            min_rating=min_rating,
            additional=additional,
            top_n=top_n,
        )
