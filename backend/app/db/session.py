"""
Database session management using Supabase client.
Provides a dependency injection function for FastAPI routes.

The client is created ONCE at module load time (singleton pattern).
This avoids the overhead of creating a new HTTP session and connection
pool on every API request, which was a measurable source of latency.
"""
from supabase import create_client, Client
from app.config import settings

if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# Singleton — created once when the server process starts, reused forever.
_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def get_db() -> Client:
    """
    FastAPI dependency that provides the shared Supabase client.

    Usage in routes:
        @router.get("/items")
        async def get_items(db: Client = Depends(get_db)):
            response = db.table("items").select("*").execute()
            return response.data

    Returns:
        Client: The shared Supabase client instance.
    """
    return _client

