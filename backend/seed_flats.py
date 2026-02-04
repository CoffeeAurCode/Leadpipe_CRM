"""
Seed script to populate the flats table with mock data.
Run this script to create sample flats across multiple buildings.
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


def seed_flats():
    """Seed the flats table with mock data"""
    
    flats_data = []
    
    # Building A - Floors 1-5, 2 flats per floor
    for floor in range(1, 6):
        for unit in range(1, 3):
            flat_number = f"A{floor}0{unit}"
            flats_data.append({
                "flat_number": flat_number,
                "building_name": "Building A",
                "floor_number": floor,
                "bedrooms": 2 if unit == 1 else 3,
                "occupied": True if floor <= 3 else False  # Lower floors are occupied
            })
    
    # Building B - Floors 1-5, 2 flats per floor
    for floor in range(1, 6):
        for unit in range(1, 3):
            flat_number = f"B{floor}0{unit}"
            flats_data.append({
                "flat_number": flat_number,
                "building_name": "Building B",
                "floor_number": floor,
                "bedrooms": 1 if unit == 1 else 2,
                "occupied": True
            })
    
    # Building C - Floors 1-3, 3 flats per floor (larger building)
    for floor in range(1, 4):
        for unit in range(1, 4):
            flat_number = f"C{floor}0{unit}"
            flats_data.append({
                "flat_number": flat_number,
                "building_name": "Building C",
                "floor_number": floor,
                "bedrooms": 3 if unit == 3 else 2,
                "occupied": floor != 3  # Third floor is vacant
            })
    
    # Simple flat numbers for testing VAPI
    for i in range(101, 106):
        flats_data.append({
            "flat_number": str(i),
            "building_name": "Main Building",
            "floor_number": (i - 100),
            "bedrooms": 2,
            "occupied": True
        })
    
    print(f"Seeding {len(flats_data)} flats...")
    
    try:
        # Insert all flats
        response = supabase.table("flats").insert(flats_data).execute()
        print(f"✅ Successfully seeded {len(flats_data)} flats!")
        print(f"   Sample flats: A101, A102, B101, C101, 101-105")
        return response.data
    except Exception as e:
        print(f"❌ Error seeding flats: {e}")
        print("   Note: If you see 'duplicate key' errors, the flats may already exist.")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("SEEDING FLATS TABLE")
    print("=" * 60)
    seed_flats()
    print("=" * 60)
