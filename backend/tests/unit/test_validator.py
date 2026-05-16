"""
Unit tests for app/ai/validator.py — Section 3.3 of TEST_PLAN.md

validate_complaint checks flat_number, category, appointment_date.
Returns: {is_complete: bool, missing_fields: list, data: dict}
"""
import pytest
from app.ai.validator import validate_complaint


class TestValidateComplaint:
    def test_all_required_fields_present(self):
        data = {
            "flat_number": "A-101",
            "category": "water",
            "appointment_date": "2026-05-20T10:00:00",
        }
        result = validate_complaint(data)
        assert result["is_complete"] is True
        assert result["missing_fields"] == []
        assert result["data"] is data

    def test_missing_flat_number(self):
        data = {"category": "water", "appointment_date": "2026-05-20T10:00:00"}
        result = validate_complaint(data)
        assert result["is_complete"] is False
        assert "flat_number" in result["missing_fields"]

    def test_missing_category(self):
        data = {"flat_number": "A-101", "appointment_date": "2026-05-20T10:00:00"}
        result = validate_complaint(data)
        assert result["is_complete"] is False
        assert "category" in result["missing_fields"]

    def test_missing_appointment_date(self):
        data = {"flat_number": "A-101", "category": "water"}
        result = validate_complaint(data)
        assert result["is_complete"] is False
        assert "appointment_date" in result["missing_fields"]

    def test_all_required_fields_missing(self):
        result = validate_complaint({})
        assert result["is_complete"] is False
        assert set(result["missing_fields"]) == {"flat_number", "category", "appointment_date"}

    def test_empty_string_treated_as_missing(self):
        data = {"flat_number": "", "category": "water", "appointment_date": "2026-05-20"}
        result = validate_complaint(data)
        assert result["is_complete"] is False
        assert "flat_number" in result["missing_fields"]

    def test_none_value_treated_as_missing(self):
        data = {"flat_number": None, "category": "water", "appointment_date": "2026-05-20"}
        result = validate_complaint(data)
        assert result["is_complete"] is False
        assert "flat_number" in result["missing_fields"]

    def test_extra_fields_ignored(self):
        data = {
            "flat_number": "A-101",
            "category": "noise",
            "appointment_date": "2026-05-20",
            "priority": "high",
            "description": "Loud music",
        }
        result = validate_complaint(data)
        assert result["is_complete"] is True

    def test_original_data_returned_untouched(self):
        data = {"flat_number": "B-202", "category": "electricity", "appointment_date": "2026-06-01"}
        result = validate_complaint(data)
        assert result["data"] == data

    def test_returns_dict_with_correct_keys(self):
        result = validate_complaint({})
        assert "is_complete" in result
        assert "missing_fields" in result
        assert "data" in result
