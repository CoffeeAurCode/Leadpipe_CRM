def clean_db_error(e: Exception) -> str:
    text = str(e)
    code = str(getattr(e, 'code', ''))

    if '23514' in code or '23514' in text:
        return "One or more field values are not allowed. Check that status fields match the accepted values."

    if '23505' in code or '23505' in text:
        return "This record already exists."

    if '23503' in code or '23503' in text:
        if 'lease_listings' in text:
            return "This unit has an active lease listing. Remove the listing before deleting the unit."
        return "This record is linked to other data and cannot be deleted."

    if '23502' in code or '23502' in text:
        return "A required field is missing."

    if '42501' in code or '42501' in text:
        return "You do not have permission to perform this action."

    msg = getattr(e, 'message', None)
    if msg and isinstance(msg, str) and not msg.startswith('{'):
        return msg

    return "A database error occurred. Please try again."
