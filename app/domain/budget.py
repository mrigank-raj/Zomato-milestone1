"""
BudgetMapper — maps budget tier labels to numeric cost-for-two ranges.

Default ranges (from architecture.md §9.3):
  low    → ₹0 – 500
  medium → ₹501 – 1500
  high   → ₹1501+
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CostRange:
    min_cost: int
    max_cost: int | None  # None means no upper limit


# Default budget tiers — can be overridden at construction time
_DEFAULT_RANGES: dict[str, CostRange] = {
    "low":    CostRange(min_cost=0,    max_cost=500),
    "medium": CostRange(min_cost=501,  max_cost=1500),
    "high":   CostRange(min_cost=1501, max_cost=None),
}


class BudgetMapper:
    """Maps a budget tier string to a numeric cost-for-two range."""

    def __init__(self, ranges: dict[str, CostRange] | None = None):
        self.ranges = ranges or dict(_DEFAULT_RANGES)

    def get_range(self, budget: Literal["low", "medium", "high"]) -> CostRange:
        """Return the CostRange for the given budget tier.

        Raises KeyError if the tier is not recognized.
        """
        tier = budget.lower().strip()
        if tier not in self.ranges:
            raise KeyError(f"Unknown budget tier: '{budget}'. Valid tiers: {list(self.ranges.keys())}")
        return self.ranges[tier]

    def matches(self, cost_for_two: int | None, budget: Literal["low", "medium", "high"]) -> bool:
        """Check whether a restaurant's cost falls within the budget range.

        Restaurants with unknown cost (None) are included by default so they
        are not silently dropped.
        """
        if cost_for_two is None:
            return True  # include unknown-cost restaurants

        cost_range = self.get_range(budget)
        if cost_for_two < cost_range.min_cost:
            return False
        if cost_range.max_cost is not None and cost_for_two > cost_range.max_cost:
            return False
        return True
