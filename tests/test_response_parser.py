import json
from app.domain.models import Restaurant
from app.domain.response_parser import LLMResponseParser

def test_parse_valid_json():
    parser = LLMResponseParser()
    candidates = [
        Restaurant(id="r1", name="R1", location="", cuisines=[], rating=4.0, cost_for_two=500, address=None, votes=None, raw={}),
        Restaurant(id="r2", name="R2", location="", cuisines=[], rating=4.5, cost_for_two=600, address=None, votes=None, raw={})
    ]
    
    json_response = json.dumps({
        "recommendations": [
            {"restaurant_id": "r2", "rank": 1, "explanation": "Best."},
            {"restaurant_id": "r1", "rank": 2, "explanation": "Second best."}
        ],
        "summary": "Enjoy!"
    })
    
    recs = parser.parse(json_response, candidates)
    
    assert len(recs) == 2
    assert recs[0].restaurant.id == "r2"
    assert recs[0].explanation == "Best."
    assert recs[0].summary == "Enjoy!"
    
    assert recs[1].restaurant.id == "r1"
    assert recs[1].explanation == "Second best."
    assert recs[1].summary is None

def test_parse_hallucinated_id():
    parser = LLMResponseParser()
    candidates = [
        Restaurant(id="r1", name="R1", location="", cuisines=[], rating=4.0, cost_for_two=500, address=None, votes=None, raw={})
    ]
    
    json_response = json.dumps({
        "recommendations": [
            {"restaurant_id": "r1", "rank": 1, "explanation": "Valid"},
            {"restaurant_id": "hallucinated_123", "rank": 2, "explanation": "Fake"}
        ]
    })
    
    recs = parser.parse(json_response, candidates)
    
    assert len(recs) == 1
    assert recs[0].restaurant.id == "r1"

def test_parse_malformed_json_fallback():
    parser = LLMResponseParser()
    candidates = [
        Restaurant(id="r1", name="R1", location="", cuisines=[], rating=4.0, cost_for_two=500, address=None, votes=None, raw={}),
        Restaurant(id="r2", name="R2", location="", cuisines=[], rating=4.5, cost_for_two=600, address=None, votes=None, raw={})
    ]
    
    malformed_response = "Here are your recommendations: oops this is not json"
    
    recs = parser.parse(malformed_response, candidates)
    
    # Should fallback to rating sort (R2 has 4.5, R1 has 4.0)
    assert len(recs) == 2
    assert recs[0].restaurant.id == "r2"
    assert recs[1].restaurant.id == "r1"
    assert "Fallback:" in recs[0].summary
