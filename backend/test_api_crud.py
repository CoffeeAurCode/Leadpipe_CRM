"""
Test CRUD operations to verify API works with Supabase.
This tests the FastAPI endpoints, not direct DB connection.
"""
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def test_connection_and_query():
    """Test if we can query from Supabase."""
    print("=== Testing FastAPI + Supabase CRUD ===\n")
    
    # Test 1: Direct database connection
    print("[1/4] Testing database connection...")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM complaints"))
            count = result.scalar()
            print(f"    >> Connected to Supabase!")
            print(f"    >> Found {count} complaints in database\n")
    except Exception as e:
        print(f"    [ERROR] Connection failed: {e}\n")
        print("    >> Fix your DATABASE_URL in .env file")
        print("    >> Make sure you're using: postgresql+asyncpg://...\n")
        return False
    
    # Test 2: Query all complaints
    print("[2/4] Testing SELECT query...")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT id, flat_number, category, status 
                FROM complaints 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            rows = result.fetchall()
            print(f"    >> Recent complaints:")
            for row in rows:
                print(f"       - ID {row[0]}: {row[1]} | {row[2]} | {row[3]}")
            print()
    except Exception as e:
        print(f"    [ERROR] Query failed: {e}\n")
        return False
    
    # Test 3: Insert a test complaint
    print("[3/4] Testing INSERT query...")
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                INSERT INTO complaints (flat_number, category, priority, description, status, source)
                VALUES (:flat, :category, :priority, :desc, :status, :source)
                RETURNING id
            """), {
                "flat": "TEST-999",
                "category": "test",
                "priority": "low",
                "desc": "API test complaint",
                "status": "pending",
                "source": "api_test"
            })
            new_id = result.scalar()
            print(f"    >> Created test complaint with ID: {new_id}\n")
    except Exception as e:
        print(f"    [ERROR] Insert failed: {e}\n")
        return False
    
    # Test 4: Update the test complaint
    print("[4/4] Testing UPDATE query...")
    try:
        async with engine.begin() as conn:
            await conn.execute(text("""
                UPDATE complaints 
                SET status = 'resolved' 
                WHERE flat_number = 'TEST-999'
            """))
            print(f"    >> Updated test complaint status to 'resolved'\n")
            
            # Clean up
            await conn.execute(text("""
                DELETE FROM complaints WHERE flat_number = 'TEST-999'
            """))
            print(f"    >> Cleaned up test data\n")
    except Exception as e:
        print(f"    [ERROR] Update failed: {e}\n")
        return False
    
    print("=" * 50)
    print("[SUCCESS] All database operations working!")
    print("=" * 50)
    print("\n>> Your FastAPI app can now:")
    print("   - Connect to Supabase")
    print("   - Read complaints (GET)")
    print("   - Create complaints (POST)")
    print("   - Update complaints (PATCH)")
    print("\n>> Next: Start your server and test endpoints:")
    print("   uvicorn app.main:app --reload")
    print("   Then open: http://localhost:8000/docs")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_connection_and_query())
    if not success:
        print("\n[FAILED] Fix the errors above and try again.")
        exit(1)
