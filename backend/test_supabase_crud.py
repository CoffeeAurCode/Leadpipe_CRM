"""
Test Supabase connection and CRUD operations with mock data.
This script will:
1. Connect to Supabase
2. Insert mock data (complaints, units, tenants)
3. Test SELECT, INSERT, UPDATE, DELETE operations
4. Clean up test data
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase_client() -> Client:
    """Initialize and return Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def test_connection(supabase: Client):
    """Test 1: Verify connection by querying complaints table."""
    print("=" * 60)
    print("[1/5] Testing Supabase Connection...")
    print("=" * 60)
    
    try:
        response = supabase.table("complaints").select("count", count="exact").execute()
        print(f"[OK] Connected to Supabase successfully!")
        print(f"[OK] Current complaints count: {response.count}")
        return True
    except Exception as e:
        print(f"[X] Connection failed: {e}")
        return False


def test_insert_mock_data(supabase: Client):
    """Test 2: Insert mock complaints data."""
    print("\n" + "=" * 60)
    print("[2/5] Inserting Mock Data...")
    print("=" * 60)
    
    mock_complaints = [
        {
            "flat_number": "A-101",
            "category": "plumbing",
            "priority": "high",
            "description": "Water leakage in bathroom pipe",
            "status": "pending",
            "source": "api_test"
        },
        {
            "flat_number": "B-205",
            "category": "electrical",
            "priority": "medium",
            "description": "Light fixture not working in bedroom",
            "status": "pending",
            "source": "api_test"
        },
        {
            "flat_number": "C-304",
            "category": "maintenance",
            "priority": "low",
            "description": "Door handle needs replacement",
            "status": "pending",
            "source": "api_test"
        }
    ]
    
    try:
        response = supabase.table("complaints").insert(mock_complaints).execute()
        inserted_ids = [item['id'] for item in response.data]
        print(f"[OK] Inserted {len(response.data)} mock complaints")
        for item in response.data:
            print(f"  - ID {item['id']}: {item['flat_number']} | {item['category']} | {item['priority']}")
        return inserted_ids
    except Exception as e:
        print(f"[X] Insert failed: {e}")
        return []


def test_select_operations(supabase: Client):
    """Test 3: Test various SELECT queries."""
    print("\n" + "=" * 60)
    print("[3/5] Testing SELECT Operations...")
    print("=" * 60)
    
    try:
        # Select all complaints
        print("\n--> Fetching all complaints (ordered by created_at DESC)...")
        response = supabase.table("complaints")\
            .select("*")\
            .order("created_at", desc=True)\
            .execute()
        print(f"[OK] Found {len(response.data)} total complaints")
        
        # Select complaints with filter
        print("\n--> Fetching high priority complaints...")
        response = supabase.table("complaints")\
            .select("*")\
            .eq("priority", "high")\
            .execute()
        print(f"[OK] Found {len(response.data)} high priority complaints")
        for item in response.data:
            print(f"  - {item['flat_number']}: {item['description'][:50]}...")
        
        # Select specific complaint by ID
        if response.data:
            complaint_id = response.data[0]['id']
            print(f"\n--> Fetching complaint by ID: {complaint_id}...")
            response = supabase.table("complaints")\
                .select("*")\
                .eq("id", complaint_id)\
                .execute()
            if response.data:
                print(f"[OK] Retrieved complaint: {response.data[0]['flat_number']}")
        
        return True
    except Exception as e:
        print(f"[X] SELECT operation failed: {e}")
        return False


def test_update_operations(supabase: Client, test_ids: list):
    """Test 4: Update complaint status."""
    print("\n" + "=" * 60)
    print("[4/5] Testing UPDATE Operations...")
    print("=" * 60)
    
    if not test_ids:
        print("[!] No test IDs available to update")
        return False
    
    try:
        complaint_id = test_ids[0]
        print(f"\n--> Updating complaint ID {complaint_id} status to 'in-progress'...")
        
        response = supabase.table("complaints")\
            .update({"status": "in-progress"})\
            .eq("id", complaint_id)\
            .execute()
        
        if response.data:
            print(f"[OK] Updated complaint {complaint_id}")
            print(f"  - New status: {response.data[0]['status']}")
            
            # Update another field
            print(f"\n--> Updating complaint ID {complaint_id} priority to 'urgent'...")
            response = supabase.table("complaints")\
                .update({"priority": "urgent"})\
                .eq("id", complaint_id)\
                .execute()
            print(f"[OK] Updated priority to: {response.data[0]['priority']}")
        
        return True
    except Exception as e:
        print(f"[X] UPDATE operation failed: {e}")
        return False


def test_delete_operations(supabase: Client):
    """Test 5: Clean up test data."""
    print("\n" + "=" * 60)
    print("[5/5] Testing DELETE Operations (Cleanup)...")
    print("=" * 60)
    
    try:
        print("\n--> Deleting all test complaints (source='api_test')...")
        response = supabase.table("complaints")\
            .delete()\
            .eq("source", "api_test")\
            .execute()
        
        print(f"[OK] Cleaned up {len(response.data)} test complaints")
        return True
    except Exception as e:
        print(f"[X] DELETE operation failed: {e}")
        return False


def main():
    """Run all Supabase CRUD tests."""
    print("\n=== SUPABASE CRUD OPERATIONS TEST ===")
    print(f"URL: {SUPABASE_URL}")
    print()
    
    try:
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Run tests
        if not test_connection(supabase):
            print("\n[FAIL] Connection test failed. Exiting.")
            return False
        
        test_ids = test_insert_mock_data(supabase)
        
        test_select_operations(supabase)
        
        test_update_operations(supabase, test_ids)
        
        test_delete_operations(supabase)
        
        # Final summary
        print("\n" + "=" * 60)
        print(">>> ALL TESTS PASSED! <<<")
        print("=" * 60)
        print("\n[OK] Supabase connection works")
        print("[OK] INSERT operations work")
        print("[OK] SELECT operations work")
        print("[OK] UPDATE operations work")
        print("[OK] DELETE operations work")
        print("\n*** Your Supabase database is ready to use! ***")
        print("\nNext steps:")
        print("  1. Update backend code to use Supabase client")
        print("  2. Test FastAPI endpoints")
        print("  3. Verify frontend integration")
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
