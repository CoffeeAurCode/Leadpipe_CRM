from app.ai.validator import validate_complaint


def decide_next_action(data: dict) -> dict:
    """
    Determine the next action based on complaint data validation.
    
    This is the orchestration layer that decides whether to:
    - Ask for the next missing/invalid field
    - Return the completed complaint JSON
    
    Args:
        data: Current complaint data (may be partial or complete)
        
    Returns:
        Dictionary with action instruction:
        - If incomplete: {"action": "ASK", "field": "field_name"}
        - If complete: {"action": "RETURN_JSON", "data": {...}}
    """
    is_valid, invalid_fields = validate_complaint(data)
    
    if not is_valid:
        next_field = _get_next_missing_field(invalid_fields)
        return {
            "action": "ASK",
            "field": next_field
        }
    
    return {
        "action": "RETURN_JSON",
        "data": {
            "flat_number": data["flat_number"],
            "category": data["category"],
            "priority": data["priority"],
            "description": data["description"]
        }
    }


def _get_next_missing_field(invalid_fields: list) -> str:
    """
    Determine which field to ask for next based on conversation state order.
    
    Field priority order (as defined in conversation states):
    1. description
    2. flat_number
    3. category
    4. priority
    
    Args:
        invalid_fields: List of fields that are missing or invalid
        
    Returns:
        The name of the next field to ask for
    """
    field_order = ["description", "flat_number", "category", "priority"]
    
    for field in field_order:
        if field in invalid_fields:
            return field
    
    return invalid_fields[0]
