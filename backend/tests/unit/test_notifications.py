"""
Unit tests for app/services/notifications.py — Section 3.6 of TEST_PLAN.md

Only notify_tenant_appointment is unit-tested here.
notify_manager_appointment_scheduled creates its own DB client and is tested at integration level.
"""
from unittest.mock import MagicMock, patch, call
import pytest

from app.services.notifications import notify_tenant_appointment


def _make_db_with_tenant(name="John", phone="+919876543210"):
    """Mock DB that returns a tenant with the given name and phone."""
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "name": name,
        "phone": phone,
    }
    return mock_db


def _make_db_no_tenant():
    """Mock DB that returns no tenant."""
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
    return mock_db


class TestNotifyTenantAppointmentCreated:
    def test_created_event_sends_sms(self):
        db = _make_db_with_tenant(name="Rahul", phone="+919876543210")
        mock_twilio = MagicMock()

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            notify_tenant_appointment("flat-uuid-1", "created", "A-101", db)

        mock_twilio.send_sms.assert_called_once()
        call_kwargs = mock_twilio.send_sms.call_args
        assert call_kwargs.kwargs["to"] == "+919876543210"
        assert "A-101" in call_kwargs.kwargs["message"]
        assert "Rahul" in call_kwargs.kwargs["message"]

    def test_created_event_message_content(self):
        db = _make_db_with_tenant(name="Priya", phone="+911234567890")
        mock_twilio = MagicMock()

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            notify_tenant_appointment("flat-uuid-1", "created", "B-205", db)

        message = mock_twilio.send_sms.call_args.kwargs["message"]
        assert "appointment" in message.lower() or "scheduled" in message.lower()


class TestNotifyTenantAppointmentRescheduled:
    def test_rescheduled_event_sends_sms_with_new_date(self):
        db = _make_db_with_tenant()
        mock_twilio = MagicMock()

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            notify_tenant_appointment(
                "flat-uuid-1", "rescheduled", "C-303", db,
                new_date="2026-06-15T10:00:00"
            )

        mock_twilio.send_sms.assert_called_once()
        message = mock_twilio.send_sms.call_args.kwargs["message"]
        assert "rescheduled" in message.lower()

    def test_rescheduled_message_includes_formatted_date(self):
        db = _make_db_with_tenant()
        mock_twilio = MagicMock()

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            notify_tenant_appointment(
                "flat-uuid-1", "rescheduled", "A-101", db,
                new_date="2026-06-15T10:00:00"
            )

        message = mock_twilio.send_sms.call_args.kwargs["message"]
        # Date should appear in the message in some readable form
        assert "2026" in message or "Jun" in message or "15" in message


class TestNotifyTenantAppointmentCancelled:
    def test_cancelled_event_sends_sms(self):
        db = _make_db_with_tenant()
        mock_twilio = MagicMock()

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            notify_tenant_appointment("flat-uuid-1", "cancelled", "D-404", db)

        mock_twilio.send_sms.assert_called_once()
        message = mock_twilio.send_sms.call_args.kwargs["message"]
        assert "cancelled" in message.lower()


class TestNotifyTenantAppointmentAttended:
    def test_attended_event_sends_sms(self):
        db = _make_db_with_tenant()
        mock_twilio = MagicMock()

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            notify_tenant_appointment("flat-uuid-1", "attended", "E-505", db)

        mock_twilio.send_sms.assert_called_once()


class TestNotifyTenantAppointmentReactivated:
    def test_reactivated_event_sends_sms(self):
        db = _make_db_with_tenant()
        mock_twilio = MagicMock()

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            notify_tenant_appointment("flat-uuid-1", "reactivated", "F-606", db)

        mock_twilio.send_sms.assert_called_once()


class TestNotifyTenantGuardCases:
    def test_no_tenant_for_flat_does_not_call_twilio(self):
        db = _make_db_no_tenant()
        mock_twilio = MagicMock()

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            notify_tenant_appointment("flat-uuid-1", "created", "A-101", db)

        mock_twilio.send_sms.assert_not_called()

    def test_tenant_with_no_phone_does_not_call_twilio(self):
        db = _make_db_with_tenant(name="John", phone=None)
        mock_twilio = MagicMock()

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            notify_tenant_appointment("flat-uuid-1", "created", "A-101", db)

        mock_twilio.send_sms.assert_not_called()

    def test_unknown_event_does_not_call_twilio(self):
        db = _make_db_with_tenant()
        mock_twilio = MagicMock()

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            notify_tenant_appointment("flat-uuid-1", "unknown_event", "A-101", db)

        mock_twilio.send_sms.assert_not_called()

    def test_twilio_failure_does_not_raise(self):
        db = _make_db_with_tenant()
        mock_twilio = MagicMock()
        mock_twilio.send_sms.side_effect = Exception("Twilio down")

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            # Must not raise
            notify_tenant_appointment("flat-uuid-1", "created", "A-101", db)

    def test_db_failure_does_not_raise(self):
        mock_db = MagicMock()
        mock_db.table.side_effect = Exception("DB connection lost")
        mock_twilio = MagicMock()

        with patch("app.services.notifications.get_twilio_client", return_value=mock_twilio):
            notify_tenant_appointment("flat-uuid-1", "created", "A-101", mock_db)
