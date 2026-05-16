"""
Unit tests for app/integrations/twilio_client.py — Section 3.7 of TEST_PLAN.md
"""
import os
from unittest.mock import patch, MagicMock
import pytest

import app.integrations.twilio_client as twilio_module
from app.integrations.twilio_client import TwilioClient


@pytest.fixture(autouse=True)
def reset_singleton():
    """Clear the module-level singleton between tests."""
    twilio_module._twilio_client = None
    yield
    twilio_module._twilio_client = None


@pytest.fixture
def twilio_env(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "testtoken456")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15005550006")


class TestTwilioClientSendSms:
    def test_sends_sms_to_valid_number(self, twilio_env):
        with patch("app.integrations.twilio_client.Client") as MockClient:
            mock_messages = MockClient.return_value.messages
            mock_messages.create.return_value.sid = "SM_test_sid"

            client = TwilioClient()
            sid = client.send_sms(to="+919876543210", message="Test message")

        assert sid == "SM_test_sid"
        mock_messages.create.assert_called_once_with(
            body="Test message",
            from_="+15005550006",
            to="+919876543210",
        )

    def test_returns_none_when_credentials_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            client = TwilioClient()
            result = client.send_sms(to="+919876543210", message="Test")

        assert result is None

    def test_no_exception_when_credentials_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            client = TwilioClient()
            result = client.send_sms(to="+919876543210", message="Test")

        assert result is None  # No exception raised

    def test_twilio_api_exception_returns_none(self, twilio_env):
        with patch("app.integrations.twilio_client.Client") as MockClient:
            MockClient.return_value.messages.create.side_effect = Exception("Twilio API error")

            client = TwilioClient()
            result = client.send_sms(to="+919876543210", message="Test")

        assert result is None

    def test_client_not_initialized_when_creds_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            client = TwilioClient()
        assert client.client is None

    def test_client_initialized_when_creds_present(self, twilio_env):
        with patch("app.integrations.twilio_client.Client") as MockClient:
            client = TwilioClient()
        assert client.client is not None

    def test_singleton_returns_same_instance(self, twilio_env):
        from app.integrations.twilio_client import get_twilio_client
        with patch("app.integrations.twilio_client.Client"):
            c1 = get_twilio_client()
            c2 = get_twilio_client()
        assert c1 is c2

    def test_logs_warning_when_credentials_missing(self, caplog):
        import logging
        with patch.dict(os.environ, {}, clear=True):
            with caplog.at_level(logging.WARNING, logger="app.integrations.twilio_client"):
                TwilioClient()
        assert len(caplog.records) > 0
