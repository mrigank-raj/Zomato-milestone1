import sys
import logging
import os
from dotenv import load_dotenv

# Load env before config
load_dotenv()

from app.infrastructure.config import AppConfig, get_llm_client
from app.infrastructure.dataset_loader import DatasetLoader
from app.domain.models import UserPreferences, Restaurant
from app.domain.prompt_builder import PromptBuilder
from app.domain.response_parser import LLMResponseParser

logging.basicConfig(level=logging.WARNING)

def main():
    config = AppConfig()
    config.validate()

    loader = DatasetLoader(config)
    restaurants = loader.load()

    # Manual filtering
    candidates = []
    for r in restaurants:
        if r.location and "bellandur" in r.location.lower():
            if r.rating >= 4.3:
                if r.cost_for_two is not None and r.cost_for_two <= 1500:
                    candidates.append(r)

    # Cap candidates
    candidates = sorted(candidates, key=lambda x: x.rating, reverse=True)[:20]

    if not candidates:
        print("No candidates found.")
        return

    prefs = UserPreferences(
        location="Bellandur",
        budget="medium",
        cuisine="Any",
        min_rating=4.3,
        additional="budget around 1500",
        top_n=5
    )

    pb = PromptBuilder(config)
    req = pb.build(prefs, candidates)

    client = get_llm_client(config)
    raw_text = client.complete(req)

    parser = LLMResponseParser()
    recs = parser.parse(raw_text, candidates)

    print(f"Found {len(candidates)} candidates. Top {len(recs)} Recommendations:")
    print("=" * 60)
    for rec in recs:
        print(f"Rank {rec.rank}: {rec.restaurant.name}")
        print(f"  Cuisines: {', '.join(rec.restaurant.cuisines)}")
        print(f"  Rating: {rec.restaurant.rating}")
        print(f"  Cost for two: {rec.restaurant.cost_for_two}")
        print(f"  Explanation: {rec.explanation}")
        print("-" * 60)

if __name__ == "__main__":
    main()
