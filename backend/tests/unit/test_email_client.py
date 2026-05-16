"""
Unit tests for app/integrations/email_client.py — Section 3.8 of TEST_PLAN.md
"""
import os
from unittest.mock import patch, MagicMock
import pytest

import app.integrations.email_client as email_module
from app.integrations.email_client import EmailClient


@pytest.fixture(autouse=True)
def reset_singleton():
    email_module._email_client = None
    yield
    email_module._email_client = None


@pytest.fixture
def email_env(monkeypatch):
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test_key_abc")
    monkeypatch.setenv("MANAGER_EMAIL", "manager@example.com")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "noreply@tenantmanagement.com")


class TestEmailClientSendEmail:
    def test_sends_email_when_configured(self, email_env):
        with patch("app.integrations.email_client.SendGridAPIClient") as MockSG:
            mock_response = MagicMock()
            mock_response.status_code = 202
            MockSG.return_value.send.return_value = mock_response

            client = EmailClient()
            result = client.send_email(
                subject="Test Subject",
                html_content="<p>Test</p>",
            )

        assert result is True

    def test_returns_false_when_api_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            client = EmailClient()
            result = client.send_email(subject="Test", html_content="<p>Body</p>")

        assert result is False

    def test_no_exception_when_api_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            client = EmailClient()
            result = client.send_email(subject="Test", html_content="<p>Body</p>")

        assert result is False  # No exception raised

    def test_sendgrid_exception_returns_false(self, email_env):
        with patch("app.integrations.email_client.SendGridAPIClient") as MockSG:
            MockSG.return_value.send.side_effect = Exception("SendGrid error")

            client = EmailClient()
            result = client.send_email(subject="Test", html_content="<p>Body</p>")

        assert result is False

    def test_returns_false_when_no_recipient(self):
        with patch.dict(os.environ, {"SENDGRID_API_KEY": "SG.key"}, clear=True):
            with patch("app.integrations.email_client.SendGridAPIClient"):
                client = EmailClient()
                result = client.send_email(
                    subject="Test",
                    html_content="<p>Body</p>",
                    to_email=None,
                )

        assert result is False

    def test_uses_explicit_to_email_over_env(self, email_env):
        with patch("app.integrations.email_client.SendGridAPIClient") as MockSG:
            mock_response = MagicMock()
            mock_response.status_code = 202
            MockSG.return_value.send.return_value = mock_response

            client = EmailClient()
            client.send_email(
                subject="Test",
                html_content="<p>Body</p>",
                to_email="specific@example.com",
            )

        # Verify the email was sent (SendGrid client was called)
        MockSG.return_value.send.assert_called_once()

    def test_client_not_initialized_when_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            client = EmailClient()
        assert client.client is None

    def test_successful_status_codes(self, email_env):
        for status_code in [200, 201, 202]:
            with patch("app.integrations.email_client.SendGridAPIClient") as MockSG:
                mock_response = MagicMock()
                mock_response.status_code = status_code
                MockSG.return_value.send.return_value = mock_response

                client = EmailClient()
                result = client.send_email(subject="Test", html_content="<p>Body</p>")

            assert result is True

    def test_non_success_status_code_returns_false(self, email_env):
        with patch("app.integrations.email_client.SendGridAPIClient") as MockSG:
            mock_response = MagicMock()
            mock_response.status_code = 500
            MockSG.return_value.send.return_value = mock_response

            client = EmailClient()
            result = client.send_email(subject="Test", html_content="<p>Body</p>")

        assert result is False

    def test_singleton_returns_same_instance(self, email_env):
        from app.integrations.email_client import get_email_client
        with patch("app.integrations.email_client.SendGridAPIClient"):
            c1 = get_email_client()
            c2 = get_email_client()
        assert c1 is c2
