import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load env vars
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'app', '.env'))

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found")
    exit(1)

supabase: Client = create_client(url, key)

def run_migration():
    print("Running migration: ADD COLUMN bathrooms to flats table...")
    try:
        # Supabase/PostgREST doesn't allow DDl via API usually, but we can try rpc if setup, 
        # or we just rely on the user having done it if this fails.
        # Actually, best way in this environment is to assume we might not be able to run DDL via 'supabase-py' client 
        # unless we have a specific SQL function exposed.
        # However, for this task, I will TRY to use the 'rpc' method if a generic 'exec_sql' exists 
        # (common in some setups), otherwise I might have to ask the user.
        
        # BUT, looking at previous tasks, we access the DB directly. 
        # If I can't run DDL, I'll ask the user. 
        # Wait, the prompt said "If a migration is needed, make it minimal and safe."
        # I'll rely on the user running the SQL if I can't do it here. 
        # But I will try to use the raw SQL via a known workaround or just logging it.
        
        # Actually, let's just print the SQL heavily for the user to run if I can't execute it.
        # There is no standard DDL method in supabase-js/py without a stored proc.
        
        print("\n[IMPORTANT] Supabase Client cannot execute DDL directly (ALTER TABLE) without a stored procedure.")
        print("Please execute the following SQL in your Supabase SQL Editor:")
        print("\n    ALTER TABLE flats ADD COLUMN bathrooms INTEGER NULL;")
        print("\n")
        
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
