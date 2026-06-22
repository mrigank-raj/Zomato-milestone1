from app.domain.models import UserPreferences, Restaurant
from app.infrastructure.config import AppConfig
from app.domain.prompt_builder import PromptBuilder

def test_prompt_builder_includes_prefs_and_candidates():
    config = AppConfig(llm_model="test-model", llm_temperature=0.1)
    builder = PromptBuilder(config)
    
    prefs = UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        additional="family-friendly",
        top_n=5
    )
    
    candidates = [
        Restaurant(
            id="r1", name="Pizza Place", location="Bangalore", 
            cuisines=["Italian"], rating=4.5, cost_for_two=800, 
            address=None, votes=100, raw={}
        ),
        Restaurant(
            id="r2", name="Pasta Hub", location="Bangalore", 
            cuisines=["Italian"], rating=4.2, cost_for_two=1200, 
            address=None, votes=50, raw={}
        )
    ]
    
    req = builder.build(prefs, candidates)
    
    assert req.model == "test-model"
    assert req.temperature == 0.1
    
    # Check user prompt contents
    assert "Bangalore" in req.user_prompt
    assert "medium" in req.user_prompt
    assert "family-friendly" in req.user_prompt
    
    # Check candidates serialization
    assert "r1" in req.user_prompt
    assert "Pizza Place" in req.user_prompt
    assert "r2" in req.user_prompt
    assert "Pasta Hub" in req.user_prompt
