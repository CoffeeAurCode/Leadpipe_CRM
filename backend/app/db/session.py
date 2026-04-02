"""
Database session management using Supabase client.
Provides dependency injection functions for FastAPI routes.

Two clients:
  - _anon_client: respects RLS, used for authenticated manager requests
  - _service_client: bypasses RLS, used for webhooks/VAPI/admin ops
"""
from supabase import create_client, Client
from app.config import settings

if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# Anon client — RLS enforced. Per-request JWT set via postgrest.auth().
_anon_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Service-role client — bypasses RLS. Used for Stripe webhooks, VAPI lookup, admin.
_service_client: Client | None = None
if settings.SUPABASE_SERVICE_KEY:
    _service_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def get_db() -> Client:
    """Anon Supabase client (RLS enforced). Use with authenticated_db for per-user scoping."""
    return _anon_client


def get_service_db() -> Client:
    """Service-role Supabase client (RLS bypassed). For webhooks, VAPI, admin operations."""
    if _service_client is None:
        raise ValueError("SUPABASE_SERVICE_KEY is not configured")
    return _service_client
