"""
Database session management using Supabase client.
Provides a dependency injection function for FastAPI routes.
"""
import os
from supabase import create_client, Client
from app.config import settings


def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance.
    
    Returns:
        Client: Configured Supabase client
    
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not configured
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    
    url = settings.SUPABASE_URL
    if not url.endswith('/'):
        url = url + '/'
    return create_client(url, settings.SUPABASE_KEY)


# Dependency for FastAPI routes
def get_db() -> Client:
    """
    FastAPI dependency that provides a Supabase client.
    
    Usage in routes:
        @router.get("/items")
        async def get_items(db: Client = Depends(get_db)):
            response = db.table("items").select("*").execute()
            return response.data
    
    Returns:
        Client: Supabase client instance
    """
    return get_supabase_client()

