"""
Unit tests for app/core/features.py — Section 3.9 of TEST_PLAN.md
"""
import pytest
from app.core.features import Feature, FEATURE_METADATA, get_default_state


class TestGetDefaultState:
    def test_voice_calls_default_is_false(self):
        # VOICE_CALLS default_enabled is False in features.py
        assert get_default_state(Feature.VOICE_CALLS) is False

    def test_sms_reminders_default_is_false(self):
        assert get_default_state(Feature.SMS_REMINDERS) is False

    def test_email_reminders_default_is_false(self):
        assert get_default_state(Feature.EMAIL_REMINDERS) is False

    def test_rent_due_date_default_is_false(self):
        assert get_default_state(Feature.RENT_DUE_DATE) is False

    def test_tenant_documents_default_is_false(self):
        assert get_default_state(Feature.TENANT_DOCUMENTS) is False

    def test_rent_management_default_is_true(self):
        assert get_default_state(Feature.RENT_MANAGEMENT) is True

    def test_flat_details_default_is_true(self):
        assert get_default_state(Feature.FLAT_DETAILS) is True

    def test_tenant_details_default_is_true(self):
        assert get_default_state(Feature.TENANT_DETAILS) is True

    def test_unknown_feature_returns_false(self):
        # Passing a non-Feature value should default to False
        assert get_default_state("nonexistent_feature") is False


class TestFeatureEnum:
    def test_all_feature_values_exist_in_metadata(self):
        for feature in Feature:
            assert feature in FEATURE_METADATA, (
                f"Feature {feature} is missing from FEATURE_METADATA"
            )

    def test_all_metadata_entries_have_required_keys(self):
        required_keys = {"category", "display_name", "description", "default_enabled"}
        for feature, meta in FEATURE_METADATA.items():
            missing = required_keys - set(meta.keys())
            assert not missing, (
                f"Feature {feature} metadata is missing keys: {missing}"
            )

    def test_default_enabled_is_bool(self):
        for feature, meta in FEATURE_METADATA.items():
            assert isinstance(meta["default_enabled"], bool), (
                f"Feature {feature} default_enabled is not a bool"
            )

    def test_feature_enum_values_are_lowercase_strings(self):
        for feature in Feature:
            assert feature.value == feature.value.lower()
            assert isinstance(feature.value, str)

    def test_feature_count_matches_metadata_count(self):
        assert len(list(Feature)) == len(FEATURE_METADATA)

    @pytest.mark.parametrize("feature,expected_category", [
        (Feature.RENT_MANAGEMENT, "Financial"),
        (Feature.RENT_DUE_DATE, "Financial"),
        (Feature.FLAT_DETAILS, "Property"),
        (Feature.VOICE_CALLS, "Communication"),
        (Feature.SMS_REMINDERS, "Communication"),
        (Feature.EMAIL_REMINDERS, "Communication"),
        (Feature.TENANT_DETAILS, "Tenant Management"),
        (Feature.TENANT_DOCUMENTS, "Tenant Management"),
    ])
    def test_feature_categories(self, feature, expected_category):
        assert FEATURE_METADATA[feature]["category"] == expected_category
