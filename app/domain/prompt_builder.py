import json
from app.domain.models import UserPreferences, Restaurant, LLMRequest
from app.infrastructure.config import AppConfig

class PromptBuilder:
    def __init__(self, config: AppConfig):
        self.config = config

    def _serialize_candidates(self, candidates: list[Restaurant]) -> str:
        # Compact JSON representation
        data = []
        for c in candidates:
            data.append({
                "id": c.id,
                "name": c.name,
                "cuisines": c.cuisines,
                "rating": c.rating,
                "cost_for_two": c.cost_for_two
            })
        return json.dumps(data, indent=2)

    def build(self, prefs: UserPreferences, candidates: list[Restaurant]) -> LLMRequest:
        top_n = min(prefs.top_n, len(candidates))

        system_prompt = f"""You are a restaurant recommendation assistant for a Zomato-like app.

Rules:
- Recommend ONLY from the CANDIDATES list provided.
- Do NOT invent restaurant names or attributes.
- Rank by best fit to USER PREFERENCES.
- Consider additional preferences (e.g. family-friendly) even if not in structured data.
- Return exactly {top_n} recommendations (or fewer only if fewer candidates exist).
- Return valid JSON matching the schema below.

Output schema:
{{
  "recommendations": [
    {{
      "restaurant_id": "<id from candidates>",
      "rank": 1,
      "explanation": "<2-3 sentences why this restaurant fits the user's preferences>"
    }}
  ],
  "summary": "<one-line overview of the recommendations>"
}}"""

        serialized_candidates = self._serialize_candidates(candidates)

        user_prompt = f"""USER PREFERENCES:
- Location: {prefs.location}
- Budget: {prefs.budget}
- Cuisine: {prefs.cuisine}
- Minimum rating: {prefs.min_rating}
- Additional: {prefs.additional or 'None'}
- Number of recommendations requested: {top_n}

CANDIDATES:
{serialized_candidates}"""

        return LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.config.llm_model,
            temperature=self.config.llm_temperature
        )
