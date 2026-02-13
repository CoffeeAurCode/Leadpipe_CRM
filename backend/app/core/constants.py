"""
Central constants for the AI Complaint Management System.

This module defines the single source of truth for allowed complaint values.
These constants are used across AI logic, API validation, and database ingestion.
"""

from enum import Enum


# ========== COMPLAINT CATEGORIES ==========

ALLOWED_CATEGORIES = [
    "water",
    "electricity",
    "cleaning",
    "noise",
    "maintenance",
    "security",
    "other"
]


# ========== COMPLAINT STATUSES (CANONICAL VALUES) ==========
# These are the ONLY allowed status values in the system.
# Database CHECK constraint enforces these exact values.

class ComplaintStatus(str, Enum):
    """Canonical complaint status values.
    
    DO NOT add new statuses without:
    1. Adding to this enum
    2. Adding to database CHECK constraint via migration
    3. Updating frontend STATUS constants
    """
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    RESOLVED = "resolved"


ALLOWED_STATUSES = [status.value for status in ComplaintStatus]


# ========== PRIORITY (DEPRECATED - REMOVED IN FAVOR OF APPOINTMENTS) ==========
# Kept for backward compatibility with old code
PRIORITY_ENUM = ["low", "medium", "high"]
