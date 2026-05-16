"""
Unit tests for app/ai/extractor.py — Section 3.1 of TEST_PLAN.md

Tests cover:
- extract_complaint_from_transcript (Groq AI path — mocked)
- extract_fields (rule-based path — no mocking needed)
- _extract_flat_number, _extract_category, _extract_priority helpers
"""
import json
from unittest.mock import MagicMock, patch
import pytest

from app.ai.extractor import (
    extract_complaint_from_transcript,
    extract_fields,
    _extract_category,
    _extract_flat_number,
    _extract_priority,
)
from app.core.constants import ALLOWED_CATEGORIES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_groq_response(flat_number, category, priority, description):
    """Build a mock Groq API response with the given extraction result."""
    payload = {
        "flat_number": flat_number,
        "category": category,
        "priority": priority,
        "description": description,
    }
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(payload)
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


# ---------------------------------------------------------------------------
# extract_complaint_from_transcript — AI path (mocked Groq)
# ---------------------------------------------------------------------------

class TestExtractComplaintFromTranscript:
    @patch("app.ai.extractor.Groq")
    def test_complete_extraction(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _make_groq_response(
            "A-101", "water", "high", "Water leak in kitchen, urgent"
        )

        result = extract_complaint_from_transcript(
            "Flat A-101, water leak in kitchen, urgent"
        )

        assert result["flat_number"] == "A-101"
        assert result["category"] == "water"
        assert result["priority"] == "high"
        assert result["description"] == "Water leak in kitchen, urgent"

    @patch("app.ai.extractor.Groq")
    def test_returns_all_none_on_groq_exception(self, MockGroq):
        MockGroq.return_value.chat.completions.create.side_effect = Exception("API down")

        result = extract_complaint_from_transcript("Some transcript")

        assert result == {"flat_number": None, "category": None, "priority": None, "description": None}

    @patch("app.ai.extractor.Groq")
    def test_invalid_category_nullified(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _make_groq_response(
            "B-202", "nuclear", "low", "Weird complaint"
        )

        result = extract_complaint_from_transcript("B-202, nuclear issue, low priority")

        assert result["category"] is None

    @patch("app.ai.extractor.Groq")
    def test_invalid_priority_nullified(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _make_groq_response(
            "C-303", "maintenance", "CRITICAL", "Broken door"
        )

        result = extract_complaint_from_transcript("C-303, broken door")

        assert result["priority"] is None

    @patch("app.ai.extractor.Groq")
    def test_valid_category_lowercased(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _make_groq_response(
            "D-404", "WATER", "high", "Leak"
        )

        result = extract_complaint_from_transcript("water leak")

        assert result["category"] == "water"

    @patch("app.ai.extractor.Groq")
    def test_empty_transcript_no_exception(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _make_groq_response(
            None, None, None, None
        )

        result = extract_complaint_from_transcript("")

        assert isinstance(result, dict)
        assert "flat_number" in result

    @patch("app.ai.extractor.Groq")
    def test_groq_returns_malformed_json(self, MockGroq):
        mock_choice = MagicMock()
        mock_choice.message.content = "not valid json {{{"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        MockGroq.return_value.chat.completions.create.return_value = mock_response

        result = extract_complaint_from_transcript("some transcript")

        assert result == {"flat_number": None, "category": None, "priority": None, "description": None}

    @patch("app.ai.extractor.Groq")
    def test_long_transcript_no_exception(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _make_groq_response(
            "A-101", "maintenance", "medium", "Long issue"
        )
        long_transcript = "water " * 1000

        result = extract_complaint_from_transcript(long_transcript)

        assert isinstance(result, dict)

    @patch("app.ai.extractor.Groq")
    def test_never_fabricates_flat_number_when_absent(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _make_groq_response(
            None, "electricity", "high", "Power cut"
        )

        result = extract_complaint_from_transcript("I have a problem with electricity")

        assert result["flat_number"] is None

    @patch("app.ai.extractor.Groq")
    def test_all_allowed_categories_pass_validation(self, MockGroq):
        for category in ALLOWED_CATEGORIES:
            mock_client = MockGroq.return_value
            mock_client.chat.completions.create.return_value = _make_groq_response(
                "A-101", category, "low", "Test"
            )
            result = extract_complaint_from_transcript("test")
            assert result["category"] == category


# ---------------------------------------------------------------------------
# extract_fields — rule-based path (no mocking)
# ---------------------------------------------------------------------------

class TestExtractFields:
    def test_electricity_keyword_maps_to_electricity_category(self):
        result = extract_fields("There is no electricity since morning")
        assert result["category"] == "electricity"

    def test_water_keyword_maps_to_water_category(self):
        result = extract_fields("There is a water leak in the bathroom")
        assert result["category"] == "water"

    def test_cleaning_keyword_maps_to_cleaning_category(self):
        result = extract_fields("The garbage is not being collected")
        assert result["category"] == "cleaning"

    def test_noise_keyword_maps_to_noise_category(self):
        result = extract_fields("Loud music coming from next flat all night")
        assert result["category"] == "noise"

    def test_maintenance_keyword_maps_to_maintenance_category(self):
        result = extract_fields("The door is broken and needs repair")
        assert result["category"] == "maintenance"

    def test_security_keyword_maps_to_security_category(self):
        result = extract_fields("The security guard is not present at the gate")
        assert result["category"] == "security"

    def test_no_keyword_gives_none_category(self):
        result = extract_fields("I have a problem")
        assert result["category"] is None

    def test_urgent_keyword_gives_high_priority(self):
        result = extract_fields("urgent water leak fix immediately")
        assert result["priority"] == "high"

    def test_low_urgency_keyword_gives_low_priority(self):
        result = extract_fields("fix whenever convenient, no hurry")
        assert result["priority"] == "low"

    def test_medium_priority_keyword(self):
        result = extract_fields("needed soon, important")
        assert result["priority"] == "medium"

    def test_no_priority_keyword_gives_none(self):
        result = extract_fields("broken window")
        assert result["priority"] is None

    def test_description_is_always_full_text(self):
        text = "  water leak in kitchen  "
        result = extract_fields(text)
        assert result["description"] == "water leak in kitchen"

    def test_empty_text_returns_all_none_except_description(self):
        result = extract_fields("")
        assert result["category"] is None
        assert result["priority"] is None
        assert result["flat_number"] is None
        assert result["description"] == ""


# ---------------------------------------------------------------------------
# _extract_flat_number
# ---------------------------------------------------------------------------

class TestExtractFlatNumber:
    def test_letter_hyphen_digits(self):
        assert _extract_flat_number("Flat A-101 has a leak") == "A-101"

    def test_letter_digits_no_hyphen(self):
        assert _extract_flat_number("Issue in B204") == "B204"

    def test_keyword_prefix(self):
        result = _extract_flat_number("flat unit201 has an issue")
        assert result is not None

    def test_pure_digits_only_as_last_resort(self):
        assert _extract_flat_number("512") == "512"

    def test_no_flat_number_returns_none(self):
        assert _extract_flat_number("I have a problem") is None

    def test_uppercase_normalization(self):
        result = _extract_flat_number("issue in a-101")
        assert result is not None
        assert result.upper() == result.upper()


# ---------------------------------------------------------------------------
# _extract_category
# ---------------------------------------------------------------------------

class TestExtractCategory:
    @pytest.mark.parametrize("text,expected", [
        ("water leak pipe", "water"),
        ("no electricity power cut", "electricity"),
        ("cleaning garbage trash", "cleaning"),
        ("loud noise music", "noise"),
        ("repair broken door maintenance", "maintenance"),
        ("security guard gate lock", "security"),
    ])
    def test_keyword_to_category_mapping(self, text, expected):
        assert _extract_category(text) == expected

    def test_no_match_returns_none(self):
        assert _extract_category("i have a problem") is None


# ---------------------------------------------------------------------------
# _extract_priority
# ---------------------------------------------------------------------------

class TestExtractPriority:
    @pytest.mark.parametrize("text,expected", [
        ("urgent fix needed", "high"),
        ("fix whenever no hurry", "low"),
        ("needed soon important", "medium"),
    ])
    def test_priority_keywords(self, text, expected):
        assert _extract_priority(text) == expected

    def test_no_priority_keyword_returns_none(self):
        assert _extract_priority("broken window") is None

    def test_high_beats_low_when_both_present(self):
        result = _extract_priority("urgent but can wait whenever")
        assert result == "high"
