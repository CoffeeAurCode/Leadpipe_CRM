"""
Migration script to fix inconsistent status values via Supabase Client (REST API).

This script performs data normalization:
1. Fetches all complaints
2. Identifies invalid statuses (e.g., 'in_progress', 'in - progress')
3. Updates them to canonical 'in-progress'
4. Verifies the fix

Note: This script relies on `supabase` package being installed.
"""
import os
import sys

# Try to load env vars manually if python-dotenv fails
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[WARN] python-dotenv not installed. Manually parsing .env...")
    try:
        with open('.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
    except Exception as e:
        print(f"[ERROR] Failed to read .env: {e}")

from supabase import create_client, Client

# Get env vars (either from system or manual .env parse)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    # Fallback: check if we just parsed them into local vars but os.environ didn't pick up (unlikely)
    print("[ERROR] SUPABASE_URL and SUPABASE_KEY must be set in .env file.")

    sys.exit(1)

def migrate():
    print(f"Connecting to Supabase at: {SUPABASE_URL[:30]}...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. Fetch ALL complaints
    print("\n1. Scanning complaints table...")
    try:
        # Fetching in chunks if needed, but for MVP assuming < 1000 records fits in one request
        response = supabase.table("complaints").select("id, status").execute()
        complaints = response.data
        print(f"   Found {len(complaints)} total complaints.")
    except Exception as e:
        print(f"[ERROR] Failed to fetch complaints: {e}")
        return

    # 2. Identify and Update
    updated_count = 0
    errors = 0
    
    print("\n2. Normalizing status values...")
    for c in complaints:
        original_status = c.get("status")
        if not original_status:
            continue
            
        # Check for non-canonical values
        canonical_status = original_status
        
        if original_status in ['in_progress', 'in - progress', 'in progress']:
            canonical_status = 'in-progress'
        
        # If changed, update
        if canonical_status != original_status:
            print(f"   [FIX] ID {c['id']}: '{original_status}' -> '{canonical_status}'")
            try:
                supabase.table("complaints").update({"status": canonical_status}).eq("id", c['id']).execute()
                updated_count += 1
            except Exception as e:
                print(f"     [ERR] Update failed: {e}")
                errors += 1
    
    if updated_count == 0:
        print("   No complaints needed normalization.")
    else:
        print(f"   Successfully normalized {updated_count} complaints.")
        if errors > 0:
            print(f"   [WARN] {errors} updates failed.")

    # 3. Verify
    print("\n3. Verifying Results...")
    response = supabase.table("complaints").select("status").execute()
    statuses = [item['status'] for item in response.data]
    
    unique_statuses = set(statuses)
    print(f"   Current distinct statuses: {unique_statuses}")
    
    invalid_found = False
    for s in unique_statuses:
        if s not in ['pending', 'in-progress', 'resolved']:
            print(f"   [WARN] Invalid status remaining: '{s}'")
            invalid_found = True
            
    if not invalid_found:
        print("\n✅ Migration complete! All statuses are canonical.")
    else:
        print("\n⚠️ Migration finished but some invalid statuses match remain.")

if __name__ == "__main__":
    migrate()
