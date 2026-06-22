import json
import re
import logging
from app.domain.models import Recommendation, Restaurant

class LLMResponseParser:
    def parse(self, raw_text: str, candidates: list[Restaurant]) -> list[Recommendation]:
        # Try parsing JSON
        parsed_data = self._extract_json(raw_text)
        if not parsed_data or "recommendations" not in parsed_data:
            logging.warning("Failed to parse LLM JSON or missing 'recommendations' key. Falling back to rating sort.")
            return self._fallback(candidates)
        
        candidate_map = {c.id: c for c in candidates}
        recommendations = []
        
        summary = parsed_data.get("summary")
        is_first = True
        
        for item in parsed_data.get("recommendations", []):
            rid = str(item.get("restaurant_id")) # Ensure string comparison
            if rid not in candidate_map:
                logging.warning(f"Hallucinated restaurant_id: {rid}")
                continue
                
            rank = item.get("rank", len(recommendations) + 1)
            explanation = item.get("explanation", "")
            
            rec = Recommendation(
                restaurant=candidate_map[rid],
                rank=rank,
                explanation=explanation,
                summary=summary if is_first else None
            )
            recommendations.append(rec)
            is_first = False
            
        # Sort by rank
        recommendations.sort(key=lambda x: x.rank)
        return recommendations
        
    def _extract_json(self, text: str) -> dict | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # Try to extract JSON from markdown code block if present
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
                
        # Look for { } blocks
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return None

    def _fallback(self, candidates: list[Restaurant]) -> list[Recommendation]:
        sorted_candidates = sorted(candidates, key=lambda c: c.rating, reverse=True)
        return [
            Recommendation(
                restaurant=c,
                rank=i + 1,
                explanation="Recommended based on rating and hard filters.",
                summary="Fallback: sorted by rating." if i == 0 else None
            ) for i, c in enumerate(sorted_candidates)
        ]
