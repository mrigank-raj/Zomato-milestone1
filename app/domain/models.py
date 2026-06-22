from dataclasses import dataclass
from typing import Literal

@dataclass
class UserPreferences:
    location: str              # e.g. "Bangalore"
    budget: Literal["low", "medium", "high"]
    cuisine: str               # e.g. "Italian"
    min_rating: float          # e.g. 4.0
    additional: str | None     # e.g. "family-friendly, quick service"
    top_n: int = 5             # number of recommendations to return

@dataclass
class Restaurant:
    id: str
    name: str
    location: str
    cuisines: list[str]
    rating: float
    cost_for_two: int | None   # normalized numeric cost
    address: str | None
    votes: int | None
    raw: dict                  # original row for debugging / future fields

@dataclass
class Recommendation:
    restaurant: Restaurant
    rank: int
    explanation: str           # LLM-generated
    summary: str | None        # optional overall summary (first item only)

@dataclass
class LLMRequest:
    system_prompt: str
    user_prompt: str
    model: str
    temperature: float

@dataclass
class LLMResponse:
    raw_text: str
    parsed_recommendations: list[Recommendation]
