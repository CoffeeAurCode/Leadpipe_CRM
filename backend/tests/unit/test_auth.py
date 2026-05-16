"""
Unit tests for app/dependencies/auth.py — Section 3.4 of TEST_PLAN.md

Tests JWT validation for get_current_user.
ES256 (JWKS) path is mocked; HS256 fallback is exercised with real PyJWT.
"""
import time
from unittest.mock import patch, MagicMock
import pytest
import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies.auth import get_current_user
import app.dependencies.auth as auth_module

TEST_SECRET = "test-supabase-jwt-secret-that-is-long-enough-for-hs256"


def _make_hs256_token(payload: dict, secret: str = TEST_SECRET) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")


def _base_payload(extra: dict | None = None) -> dict:
    base = {
        "sub": "user-uuid-123",
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    if extra:
        base.update(extra)
    return base


@pytest.fixture(autouse=True)
def isolate_jwks_client():
    """Reset the cached JWKS client before every test."""
    auth_module._jwks_client = None
    yield
    auth_module._jwks_client = None


@pytest.fixture
def patch_hs256_settings():
    """Patch settings so HS256 fallback uses the test secret."""
    with patch("app.dependencies.auth.settings") as mock_settings:
        mock_settings.SUPABASE_JWT_SECRET = TEST_SECRET
        mock_settings.SUPABASE_URL = "https://test.supabase.co"
        yield mock_settings


def _patch_jwks_unavailable():
    """Make the JWKS client unavailable, forcing HS256 fallback."""
    return patch(
        "app.dependencies.auth._get_jwks_client",
        side_effect=Exception("JWKS not available in test"),
    )


# ---------------------------------------------------------------------------
# Valid tokens
# ---------------------------------------------------------------------------

class TestValidTokens:
    @pytest.mark.asyncio
    async def test_valid_hs256_token_returns_payload(self, patch_hs256_settings):
        token = _make_hs256_token(_base_payload())
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with _patch_jwks_unavailable():
            payload = await get_current_user(creds)

        assert payload["sub"] == "user-uuid-123"
        assert payload["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_payload_contains_sub_and_email(self, patch_hs256_settings):
        token = _make_hs256_token(_base_payload({"email": "manager@example.com"}))
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with _patch_jwks_unavailable():
            payload = await get_current_user(creds)

        assert "sub" in payload
        assert payload["email"] == "manager@example.com"

    @pytest.mark.asyncio
    async def test_es256_jwks_path_returns_payload_when_available(self):
        mock_signing_key = MagicMock()
        # Return a payload decoded by the mocked signing key
        mock_payload = {"sub": "es256-user", "email": "es@test.com"}

        with patch("app.dependencies.auth._get_jwks_client") as mock_get_jwks, \
             patch("app.dependencies.auth.jwt.decode", return_value=mock_payload):
            mock_get_jwks.return_value.get_signing_key_from_jwt.return_value = mock_signing_key
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake.jwt.token")
            payload = await get_current_user(creds)

        assert payload["sub"] == "es256-user"


# ---------------------------------------------------------------------------
# Expired tokens
# ---------------------------------------------------------------------------

class TestExpiredToken:
    @pytest.mark.asyncio
    async def test_expired_hs256_token_raises_401(self, patch_hs256_settings):
        expired_payload = _base_payload({"exp": int(time.time()) - 3600})
        token = _make_hs256_token(expired_payload)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with _patch_jwks_unavailable():
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_expired_es256_token_raises_401(self):
        """ES256 path: ExpiredSignatureError must propagate as 401."""
        with patch("app.dependencies.auth._get_jwks_client") as mock_get_jwks, \
             patch("app.dependencies.auth.jwt.decode", side_effect=jwt.ExpiredSignatureError):
            mock_get_jwks.return_value.get_signing_key_from_jwt.return_value = MagicMock()
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired.jwt")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)

        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Invalid / malformed tokens
# ---------------------------------------------------------------------------

class TestInvalidTokens:
    @pytest.mark.asyncio
    async def test_malformed_token_raises_401(self, patch_hs256_settings):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.jwt")

        with _patch_jwks_unavailable():
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_random_string_raises_401(self, patch_hs256_settings):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="randomstring")

        with _patch_jwks_unavailable():
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_tampered_signature_raises_401(self, patch_hs256_settings):
        token = _make_hs256_token(_base_payload())
        parts = token.split(".")
        # Corrupt the signature
        tampered = parts[0] + "." + parts[1] + ".invalidsignature"
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=tampered)

        with _patch_jwks_unavailable():
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret_raises_401(self, patch_hs256_settings):
        token = _make_hs256_token(_base_payload(), secret="wrong-secret")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with _patch_jwks_unavailable():
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_token_raises_401(self, patch_hs256_settings):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

        with _patch_jwks_unavailable():
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)

        assert exc_info.value.status_code == 401
