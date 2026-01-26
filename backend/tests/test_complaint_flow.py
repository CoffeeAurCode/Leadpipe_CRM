"""
Integration test for complaint conversation flow.

This test simulates a complete conversation flow from raw user messages
to final structured JSON output, exercising the full pipeline:
- extract_fields() → partial extraction
- validate_complaint() → validation
- decide_next_action() → routing logic
"""

import sys
sys.path.insert(0, 'c:/Users/BIT/Coding/Tenant_management_MVP/backend')

from app.ai.extractor import extract_fields
from app.ai.decision_engine import decide_next_action


def test_complaint_flow_happy_path():
    """
    Simulate a complete conversation flow with hardcoded user messages.
    
    Conversation:
    User: "There is no electricity since morning"
    AI: Which flat are you in?
    User: "512"
    AI: How urgent is the issue? (low/medium/high)
    User: "high"
    AI: Returns JSON
    """
    
    complaint_data = {
        "flat_number": None,
        "category": None,
        "priority": None,
        "description": None
    }
    
    user_message_1 = "There is no electricity since morning"
    extracted = extract_fields(user_message_1)
    
    for field, value in extracted.items():
        if value is not None:
            complaint_data[field] = value
    
    action = decide_next_action(complaint_data)
    assert action["action"] == "ASK"
    assert action["field"] == "flat_number"
    
    user_message_2 = "512"
    extracted = extract_fields(user_message_2)
    
    for field, value in extracted.items():
        if value is not None and complaint_data[field] is None:
            complaint_data[field] = value
    
    action = decide_next_action(complaint_data)
    assert action["action"] == "ASK"
    assert action["field"] == "priority"
    
    user_message_3 = "high"
    extracted = extract_fields(user_message_3)
    
    for field, value in extracted.items():
        if value is not None and complaint_data[field] is None:
            complaint_data[field] = value
    
    action = decide_next_action(complaint_data)
    assert action["action"] == "RETURN_JSON"
    
    final_json = action["data"]
    
    assert final_json == {
        "flat_number": "512",
        "category": "electricity",
        "priority": "high",
        "description": "There is no electricity since morning"
    }
    
    print("[PASS] Test passed: Complete conversation flow works correctly")
    print(f"[PASS] Final JSON: {final_json}")


if __name__ == "__main__":
    test_complaint_flow_happy_path()
