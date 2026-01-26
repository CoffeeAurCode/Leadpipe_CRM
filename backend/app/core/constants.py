"""
Central constants for the AI Complaint Management System.

This module defines the single source of truth for allowed complaint values.
These constants are used across AI logic, API validation, and database ingestion.
"""

ALLOWED_CATEGORIES = [
    "water",
    "electricity",
    "cleaning",
    "noise",
    "maintenance",
    "security",
    "other"
]

PRIORITY_ENUM = ["low", "medium", "high"]
