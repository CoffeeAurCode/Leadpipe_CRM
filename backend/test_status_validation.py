import pytest
from app.schemas.complaint import ComplaintCreate
from pydantic import ValidationError

def test_valid_statuses():
    """Valid statuses should pass validation."""
    for status in ['pending', 'in-progress', 'resolved']:
        complaint = ComplaintCreate(
            category="maintenance",
            appointment_datetime="2026-02-14T10:00:00",
            description="Test complaint",
            status=status,
            source="test"
        )
        assert complaint.status == status

def test_invalid_status_underscore():
    """Status with underscore should fail validation."""
    with pytest.raises(ValidationError) as exc:
        ComplaintCreate(
            category="maintenance",
            appointment_datetime="2026-02-14T10:00:00",
            description="Test",
            status="in_progress",  # Invalid format
            source="test"
        )
    assert "Invalid status" in str(exc.value)

def test_invalid_status_random():
    """Random string status should fail validation."""
    with pytest.raises(ValidationError) as exc:
        ComplaintCreate(
            category="maintenance",
            appointment_datetime="2026-02-14T10:00:00",
            description="Test",
            status="unknown_status",
            source="test"
        )
    assert "Invalid status" in str(exc.value)
