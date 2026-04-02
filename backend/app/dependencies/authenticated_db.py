"""
Authenticated DB dependency — sets the user's JWT on the Supabase anon client
so that RLS policies resolve auth.uid() correctly for each request.
"""
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.db.session import get_db

security = HTTPBearer()


async def get_authenticated_db(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Client = Depends(get_db),
) -> Client:
    """
    Attach the user's JWT to the Supabase postgrest client so RLS
    policies resolve auth.uid() for this request.
    """
    db.postgrest.auth(credentials.credentials)
    return db
