from app.core.constants import ALLOWED_CATEGORIES, PRIORITY_ENUM


def validate_complaint(data: dict) -> tuple[bool, list]:
    """
    Validate a complaint dictionary for completeness and correctness.
    
    Checks:
    - All required fields are present and not None/empty
    - Category is in ALLOWED_CATEGORIES
    - Priority is in PRIORITY_ENUM
    - Description length >= 10 characters
    
    Args:
        data: Complaint dictionary (may be partial or complete)
        
    Returns:
        Tuple of (is_valid, missing_or_invalid_fields)
        - is_valid: True only if all validations pass
        - missing_or_invalid_fields: List of field names that failed validation
    """
    required_fields = ["flat_number", "category", "priority", "description"]
    invalid_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            invalid_fields.append(field)
    
    if "category" in data and data["category"] is not None and data["category"] != "":
        if data["category"] not in ALLOWED_CATEGORIES:
            if "category" not in invalid_fields:
                invalid_fields.append("category")
    
    if "priority" in data and data["priority"] is not None and data["priority"] != "":
        if data["priority"] not in PRIORITY_ENUM:
            if "priority" not in invalid_fields:
                invalid_fields.append("priority")
    
    if "description" in data and data["description"] is not None and data["description"] != "":
        if len(data["description"]) < 10:
            if "description" not in invalid_fields:
                invalid_fields.append("description")
    
    is_valid = len(invalid_fields) == 0
    
    return (is_valid, invalid_fields)
