"""
Quick test script to check if appointments table exists and test insertion
"""
import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Testing appointments table...")
print("=" * 60)

# Test 1: Check if table exists by trying to select
try:
    result = supabase.table("appointments").select("*").limit(1).execute()
    print("✅ Appointments table exists")
    print(f"   Current appointments count: {len(result.data)}")
except Exception as e:
    print(f"❌ Appointments table error: {e}")
    print("\n💡 The appointments table doesn't exist in Supabase yet.")
    print("   You need to run the schema.sql to create it.")
    exit(1)

# Test 2: Try to insert a test appointment
print("\nTrying to create a test appointment...")
try:
    test_data = {
        "flat_number": "101",
        "appointment_date": (datetime.now() + timedelta(days=3)).isoformat(),
        "status": "scheduled",
        "notes": "Test appointment from script"
    }
    
    result = supabase.table("appointments").insert(test_data).execute()
    print(f"✅ Successfully created test appointment: {result.data}")
    
    # Clean up - delete the test appointment
    if result.data:
        supabase.table("appointments").delete().eq("id", result.data[0]["id"]).execute()
        print("   (Test appointment cleaned up)")
        
except Exception as e:
    print(f"❌ Failed to create appointment: {e}")
    print("\n🔍 This is likely the same error the frontend is seeing.")

print("=" * 60)
