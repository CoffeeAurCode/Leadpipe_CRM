def validate_complaint(data: dict) -> dict:
    """
    This function only checks existence and non-emptiness of:
    - flat_number
    - category
    - appointment_date (for scheduling manager visit)
    
    Args:
        data: Complaint dictionary extracted from transcript
        
    Returns:
        Dictionary with validation results:
        {
            "is_complete": bool,
            "missing_fields": list[str],
            "data": dict  # original data untouched
        }
    """
    required_fields = ["flat_number", "category", "appointment_date"]
    missing_fields = []
    
    for field in required_fields:
        value = data.get(field)
        if value is None or value == "":
            missing_fields.append(field)
    
    return {
        "is_complete": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "data": data
    }

