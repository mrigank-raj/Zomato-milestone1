"""
RestaurantFilter — applies hard filters to the restaurant dataset.

Filter chain (from architecture.md §9.3):
  1. Location   — case-insensitive match
  2. Min rating — restaurant.rating >= prefs.min_rating
  3. Cuisine    — any entry in restaurant.cuisines matches (case-insensitive)
  4. Budget     — cost_for_two within BudgetMapper range

After filtering, candidates are capped to MAX_CANDIDATES sorted by rating descending.
"""

import logging
from app.domain.models import Restaurant, UserPreferences
from app.domain.budget import BudgetMapper

logger = logging.getLogger("zomato-rec")


class RestaurantFilter:
    """Filters restaurants based on UserPreferences."""

    def __init__(self, budget_mapper: BudgetMapper | None = None, max_candidates: int = 20):
        self.budget_mapper = budget_mapper or BudgetMapper()
        self.max_candidates = max_candidates

    def apply(self, restaurants: list[Restaurant], prefs: UserPreferences) -> list[Restaurant]:
        """Apply all hard filters and return capped, rating-sorted candidates.

        Returns an empty list (no exception) if nothing matches.
        """
        candidates = []
        location_lower = prefs.location.lower()
        cuisine_lower = prefs.cuisine.lower()

        for r in restaurants:
            # 1. Location — case-insensitive match
            if r.location.lower() != location_lower:
                continue

            # 2. Min rating
            if r.rating < prefs.min_rating:
                continue

            # 3. Cuisine — any cuisine in the restaurant's list matches
            if not any(cuisine_lower in c.lower() for c in r.cuisines):
                continue

            # 4. Budget
            if not self.budget_mapper.matches(r.cost_for_two, prefs.budget):
                continue

            candidates.append(r)

        # Sort by rating descending, then by votes descending as tiebreaker
        candidates.sort(key=lambda r: (r.rating, r.votes or 0), reverse=True)

        # Cap to MAX_CANDIDATES
        if len(candidates) > self.max_candidates:
            logger.info(
                f"Capping candidates from {len(candidates)} to {self.max_candidates} "
                f"(sorted by rating desc)."
            )
            candidates = candidates[: self.max_candidates]

        logger.info(f"Filter returned {len(candidates)} candidates for prefs: {prefs.location}, {prefs.cuisine}")
        return candidates
