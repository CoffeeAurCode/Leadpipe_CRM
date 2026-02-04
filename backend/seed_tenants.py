"""
Seed script to populate the tenants table with mock data.
Run this script after seeding flats to create sample tenants.
"""
import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_flat_id(flat_number):
    """Get flat ID by flat number"""
    try:
        response = supabase.table("flats").select("id").eq("flat_number", flat_number).execute()
        if response.data:
            return response.data[0]["id"]
        return None
    except Exception as e:
        print(f"Error getting flat ID for {flat_number}: {e}")
        return None


def seed_tenants():
    """Seed the tenants table with mock data"""
    
    # Mock tenant data with flat assignments
    tenants_data = [
        {"name": "Rahul Sharma", "phone": "+91-9876543210", "flat_number": "A101"},
        {"name": "Priya Patel", "phone": "+91-9876543211", "flat_number": "A102"},
        {"name": "Amit Kumar", "phone": "+91-9876543212", "flat_number": "A201"},
        {"name": "Sneha Reddy", "phone": "+91-9876543213", "flat_number": "A202"},
        {"name": "Vikram Singh", "phone": "+91-9876543214", "flat_number": "A301"},
        
        {"name": "Ananya Iyer", "phone": "+91-9876543215", "flat_number": "B101"},
        {"name": "Rohan Gupta", "phone": "+91-9876543216", "flat_number": "B102"},
        {"name": "Kavya Nair", "phone": "+91-9876543217", "flat_number": "B201"},
        {"name": "Arjun Mehta", "phone": "+91-9876543218", "flat_number": "B202"},
        {"name": "Meera Joshi", "phone": "+91-9876543219", "flat_number": "B301"},
        
        {"name": "Siddharth Verma", "phone": "+91-9876543220", "flat_number": "C101"},
        {"name": "Ishita Das", "phone": "+91-9876543221", "flat_number": "C102"},
        {"name": "Karan Chopra", "phone": "+91-9876543222", "flat_number": "C103"},
        {"name": "Neha Kapoor", "phone": "+91-9876543223", "flat_number": "C201"},
        {"name": "Aditya Rao", "phone": "+91-9876543224", "flat_number": "C202"},
        
        {"name": "Pooja Desai", "phone": "+91-9876543225", "flat_number": "101"},
        {"name": "Nikhil Bansal", "phone": "+91-9876543226", "flat_number": "102"},
        {"name": "Riya Agarwal", "phone": "+91-9876543227", "flat_number": "103"},
        {"name": "Manish Tiwari", "phone": "+91-9876543228", "flat_number": "104"},
        {"name": "Shreya Malhotra", "phone": "+91-9876543229", "flat_number": "105"},
    ]
    
    print(f"Seeding {len(tenants_data)} tenants...")
    
    # Prepare tenant records with flat_id references
    tenant_records = []
    for tenant in tenants_data:
        flat_number = tenant.pop("flat_number")
        flat_id = get_flat_id(flat_number)
        
        if flat_id:
            tenant["flat_id"] = flat_id
            tenant_records.append(tenant)
            print(f"  ✓ {tenant['name']} → Flat {flat_number}")
        else:
            print(f"  ⚠ Skipping {tenant['name']}: Flat {flat_number} not found")
    
    try:
        # Insert all tenants
        if tenant_records:
            response = supabase.table("tenants").insert(tenant_records).execute()
            print(f"\n✅ Successfully seeded {len(tenant_records)} tenants!")
            return response.data
        else:
            print("\n⚠ No tenants to seed. Make sure flats are seeded first.")
            return None
    except Exception as e:
        print(f"\n❌ Error seeding tenants: {e}")
        print("   Note: If you see 'duplicate key' errors, the tenants may already exist.")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("SEEDING TENANTS TABLE")
    print("=" * 60)
    seed_tenants()
    print("=" * 60)
