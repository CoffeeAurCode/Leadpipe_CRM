"""
Feature Control System - Centralized Feature Registry

This module defines all available features and their metadata.
Single source of truth for feature definitions across the application.
"""

from enum import Enum
from typing import Dict


class Feature(str, Enum):
    """Centralized feature registry for property-level feature flags"""
    
    # Financial Features
    RENT_MANAGEMENT = "rent_management"
    RENT_DUE_DATE = "rent_due_date"
    
    # Property Management
    FLAT_DETAILS = "flat_details"
    
    # Communication Features
    OUTBOUND_CALLS = "outbound_calls"
    SMS_AUTOMATION = "sms_automation"
    EMAIL_AUTOMATION = "email_automation"
    
    # Tenant Management
    TENANT_DETAILS = "tenant_details"
    TENANT_DOCUMENTS = "tenant_documents"


# Feature metadata for UI grouping and display
FEATURE_METADATA: Dict[Feature, dict] = {
    Feature.RENT_MANAGEMENT: {
        "category": "Financial",
        "display_name": "Rent Management",
        "description": "Set and manage rent amounts",
        "default_enabled": True  # Core feature
    },
    Feature.RENT_DUE_DATE: {
        "category": "Financial",
        "display_name": "Rent Due Date",
        "description": "Configure rent payment deadlines",
        "default_enabled": False
    },
    Feature.FLAT_DETAILS: {
        "category": "Property",
        "display_name": "Flat Details",
        "description": "Edit owner, bedrooms, bathrooms, address",
        "default_enabled": True  # Core feature
    },
    Feature.OUTBOUND_CALLS: {
        "category": "Communication",
        "display_name": "Outbound Calls",
        "description": "Twilio-powered voice calls",
        "default_enabled": False
    },
    Feature.SMS_AUTOMATION: {
        "category": "Communication",
        "display_name": "SMS Automation",
        "description": "Automated rent reminders via SMS",
        "default_enabled": False
    },
    Feature.EMAIL_AUTOMATION: {
        "category": "Communication",
        "display_name": "Email Automation",
        "description": "Automated rent reminders via email",
        "default_enabled": False
    },
    Feature.TENANT_DETAILS: {
        "category": "Tenant Management",
        "display_name": "Tenant Details",
        "description": "Edit and view tenant information",
        "default_enabled": True  # Core feature
    },
    Feature.TENANT_DOCUMENTS: {
        "category": "Tenant Management",
        "display_name": "Tenant Documents",
        "description": "Upload/download tenant documents",
        "default_enabled": False
    }
}


def get_default_state(feature: Feature) -> bool:
    """Get the default enabled state for a feature"""
    return FEATURE_METADATA.get(feature, {}).get("default_enabled", False)
