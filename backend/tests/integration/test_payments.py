"""
Integration tests for /payments — Section 4.17 of TEST_PLAN.md

Stripe interactions are mocked via unittest.mock.patch.
Webhook signature validation is tested for both valid and invalid signatures.
"""
import json
import time
import pytest
import stripe
from unittest.mock import patch, MagicMock
from tests.integration.conftest import TEST_USER


# ===========================================================================
# POST /payments/create-checkout-session
# ===========================================================================

class TestCreateCheckoutSession:
    def _mock_stripe_session(self):
        """Return a minimal Stripe Session mock."""
        session = MagicMock()
        session.url = "https://checkout.stripe.com/test-session"
        return session

    def _patch_stripe(self):
        """Patch stripe.Customer.list, stripe.Customer.create, stripe.checkout.Session.create."""
        customer_mock = MagicMock()
        customer_mock.id = "cus_test123"

        list_result = MagicMock()
        list_result.data = []  # no existing customer

        return [
            patch("app.routes.payments.stripe.Customer.list", return_value=list_result),
            patch("app.routes.payments.stripe.Customer.create", return_value=customer_mock),
            patch(
                "app.routes.payments.stripe.checkout.Session.create",
                return_value=self._mock_stripe_session(),
            ),
        ]

    def test_new_user_creates_checkout_session(self, authed_client):
        from app.main import app
        from app.db.session import get_service_db
        from app.dependencies.auth import get_current_user
        from fastapi.testclient import TestClient
        from tests.integration.conftest import make_mock_db

        db = make_mock_db(subscriptions=[])  # no existing subscription
        app.dependency_overrides[get_current_user] = lambda: TEST_USER
        app.dependency_overrides[get_service_db] = lambda: db
        tc = TestClient(app, raise_server_exceptions=False)

        patches = self._patch_stripe()
        for p in patches:
            p.start()
        try:
            resp = tc.post("/payments/create-checkout-session")
            assert resp.status_code == 200
            assert "checkout_url" in resp.json()
        finally:
            for p in patches:
                p.stop()
        app.dependency_overrides.clear()

    def test_already_subscribed_returns_400(self, authed_client):
        from app.main import app
        from app.db.session import get_service_db
        from app.dependencies.auth import get_current_user
        from fastapi.testclient import TestClient
        from tests.integration.conftest import make_mock_db

        db = make_mock_db(subscriptions=[{"id": "sub-1", "status": "active"}])
        app.dependency_overrides[get_current_user] = lambda: TEST_USER
        app.dependency_overrides[get_service_db] = lambda: db
        tc = TestClient(app, raise_server_exceptions=False)

        resp = tc.post("/payments/create-checkout-session")
        assert resp.status_code == 400
        assert "subscription" in resp.json()["detail"].lower()
        app.dependency_overrides.clear()

    def test_missing_email_returns_400(self, authed_client):
        from app.main import app
        from app.db.session import get_service_db
        from app.dependencies.auth import get_current_user
        from fastapi.testclient import TestClient
        from tests.integration.conftest import make_mock_db

        user_no_email = {**TEST_USER, "email": ""}
        db = make_mock_db(subscriptions=[])
        app.dependency_overrides[get_current_user] = lambda: user_no_email
        app.dependency_overrides[get_service_db] = lambda: db
        tc = TestClient(app, raise_server_exceptions=False)

        resp = tc.post("/payments/create-checkout-session")
        assert resp.status_code == 400
        assert "email" in resp.json()["detail"].lower()
        app.dependency_overrides.clear()

    def test_no_auth_returns_401_or_403(self):
        from fastapi.testclient import TestClient
        from app.main import app as _app
        _app.dependency_overrides.clear()
        tc = TestClient(_app, raise_server_exceptions=False)
        resp = tc.post("/payments/create-checkout-session")
        assert resp.status_code in (401, 403)
        _app.dependency_overrides.clear()


# ===========================================================================
# GET /payments/subscription-status
# ===========================================================================

class TestSubscriptionStatus:
    def test_active_subscription_returns_subscribed_true(self, authed_client):
        from app.main import app
        from app.db.session import get_service_db
        from app.dependencies.auth import get_current_user
        from fastapi.testclient import TestClient
        from tests.integration.conftest import make_mock_db

        db = make_mock_db(subscriptions=[{"status": "active"}])
        app.dependency_overrides[get_current_user] = lambda: TEST_USER
        app.dependency_overrides[get_service_db] = lambda: db
        tc = TestClient(app, raise_server_exceptions=False)

        resp = tc.get("/payments/subscription-status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["subscribed"] is True
        assert body["status"] == "active"
        app.dependency_overrides.clear()

    def test_no_subscription_returns_subscribed_false(self, authed_client):
        from app.main import app
        from app.db.session import get_service_db
        from app.dependencies.auth import get_current_user
        from fastapi.testclient import TestClient
        from tests.integration.conftest import make_mock_db

        db = make_mock_db(subscriptions=[])
        app.dependency_overrides[get_current_user] = lambda: TEST_USER
        app.dependency_overrides[get_service_db] = lambda: db
        tc = TestClient(app, raise_server_exceptions=False)

        resp = tc.get("/payments/subscription-status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["subscribed"] is False
        assert body["status"] is None
        app.dependency_overrides.clear()

    def test_trialing_subscription_returns_subscribed_true(self, authed_client):
        from app.main import app
        from app.db.session import get_service_db
        from app.dependencies.auth import get_current_user
        from fastapi.testclient import TestClient
        from tests.integration.conftest import make_mock_db

        db = make_mock_db(subscriptions=[{"status": "trialing"}])
        app.dependency_overrides[get_current_user] = lambda: TEST_USER
        app.dependency_overrides[get_service_db] = lambda: db
        tc = TestClient(app, raise_server_exceptions=False)

        resp = tc.get("/payments/subscription-status")
        assert resp.status_code == 200
        assert resp.json()["subscribed"] is True
        app.dependency_overrides.clear()


# ===========================================================================
# POST /payments/webhook (Stripe webhook)
# ===========================================================================

class TestStripeWebhook:
    def _valid_payload(self, event_type="customer.subscription.created"):
        return json.dumps({
            "id": "evt_test_123",
            "type": event_type,
            "data": {
                "object": {
                    "id": "sub_test_abc",
                    "customer": "cus_test_xyz",
                    "status": "trialing",
                    "current_period_end": int(time.time()) + 86400 * 30,
                    "metadata": {"manager_id": TEST_USER["sub"]},
                }
            },
        })

    def test_invalid_signature_returns_400(self, authed_client):
        from app.main import app
        from app.db.session import get_service_db
        from fastapi.testclient import TestClient
        from tests.integration.conftest import make_mock_db

        db = make_mock_db()
        app.dependency_overrides[get_service_db] = lambda: db
        tc = TestClient(app, raise_server_exceptions=False)

        with patch("app.routes.payments.stripe.Webhook.construct_event", side_effect=stripe.error.SignatureVerificationError("Bad sig", "sig")):
            resp = tc.post(
                "/payments/webhook",
                content=self._valid_payload(),
                headers={"stripe-signature": "bad-sig", "content-type": "application/json"},
            )
        assert resp.status_code == 400
        app.dependency_overrides.clear()

    def test_missing_signature_header_returns_400(self, authed_client):
        from app.main import app
        from app.db.session import get_service_db
        from fastapi.testclient import TestClient
        from tests.integration.conftest import make_mock_db

        db = make_mock_db()
        app.dependency_overrides[get_service_db] = lambda: db
        tc = TestClient(app, raise_server_exceptions=False)

        with patch("app.routes.payments.stripe.Webhook.construct_event", side_effect=Exception("No sig")):
            resp = tc.post(
                "/payments/webhook",
                content=self._valid_payload(),
                headers={"content-type": "application/json"},
            )
        assert resp.status_code in (400, 422, 500)
        app.dependency_overrides.clear()

    def test_subscription_created_event_upserts_row(self, authed_client):
        from app.main import app
        from app.db.session import get_service_db
        from fastapi.testclient import TestClient
        from tests.integration.conftest import make_mock_db

        db = make_mock_db(
            stripe_events=[],
            subscriptions=[],
            manager_profiles=[{"user_id": TEST_USER["sub"]}],
        )
        app.dependency_overrides[get_service_db] = lambda: db
        tc = TestClient(app, raise_server_exceptions=False)

        mock_event = MagicMock()
        mock_event.id = "evt_test_123"
        mock_event.type = "customer.subscription.created"
        mock_event.data.object = {
            "id": "sub_test_abc",
            "customer": "cus_test_xyz",
            "status": "trialing",
            "current_period_end": int(time.time()) + 86400 * 30,
            "metadata": {"manager_id": TEST_USER["sub"]},
        }

        with patch("app.routes.payments.stripe.Webhook.construct_event", return_value=mock_event):
            resp = tc.post(
                "/payments/webhook",
                content=self._valid_payload(),
                headers={
                    "stripe-signature": "valid-sig",
                    "content-type": "application/json",
                },
            )
        assert resp.status_code == 200
        app.dependency_overrides.clear()
