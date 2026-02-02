"""
Utility script to create all database tables in Supabase.
Run this once to initialize your database schema.

Usage:
    python create_tables.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings
from app.db.base import Base

# Import all models to ensure they're registered with Base.metadata
from app.db.models import User, Unit, Tenant, Complaint, CallLog


async def create_tables():
    """Create all tables defined in SQLAlchemy models."""
    print(">> Connecting to Supabase...")
    print(f">> Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Not configured'}")
    
    # Create engine with SSL configuration for Supabase
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,  # Show SQL queries for debugging
        connect_args={
            "ssl": "require",
            "server_settings": {"application_name": "tenant_management_setup"}
        }
    )
    
    try:
        print("\n>> Creating tables...")
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        print("\n[SUCCESS] Tables created successfully!")
        print("\n>> Created tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")
        
        print("\n>> Next steps:")
        print("   1. Check your Supabase dashboard -> Table Editor")
        print("   2. Verify all tables are visible")
        print("   3. Start your FastAPI server: uvicorn app.main:app --reload")
        
    except Exception as e:
        print(f"\n[ERROR] Error creating tables: {e}")
        raise
    finally:
        await engine.dispose()
        print("\n>> Database connection closed.")


if __name__ == "__main__":
    asyncio.run(create_tables())
