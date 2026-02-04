"""
Seed script to add test complaints with appointment dates to see on calendar.
Run this to create sample complaints with scheduled visit dates.
"""
import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def seed_complaints_with_appointments():
    """Seed complaints table with appointment dates"""
    
    # Create complaints for the next few days
    base_date = datetime.now()
    
    complaints_data = [
        {
            "flat_number": "101",
            "category": "plumbing",
            "priority": "high",
            "description": "Kitchen sink is leaking heavily. Water pooling on floor.",
            "status": "pending",
            "source": "web",
            "appointment_date": (base_date + timedelta(days=1, hours=10)).isoformat()
        },
        {
            "flat_number": "A201",
            "category": "electrical",
            "priority": "high",
            "description": "Main circuit breaker keeps tripping. No power in living room.",
            "status": "pending",
            "source": "voice",
            "appointment_date": (base_date + timedelta(days=1, hours=14)).isoformat()
        },
        {
            "flat_number": "B102",
            "category": "maintenance",
            "priority": "medium",
            "description": "Door lock is jammed, difficult to open from outside.",
            "status": "pending",
            "source": "web",
            "appointment_date": (base_date + timedelta(days=2, hours=9)).isoformat()
        },
        {
            "flat_number": "A102",
            "category": "hvac",
            "priority": "medium",
            "description": "Air conditioning not cooling properly, making strange noises.",
            "status": "in-progress",
            "source": "voice",
            "appointment_date": (base_date + timedelta(days=3, hours=11)).isoformat()
        },
        {
            "flat_number": "C101",
            "category": "plumbing",
            "priority": "low",
            "description": "Bathroom faucet drips occasionally.",
            "status": "pending",
            "source": "web",
            "appointment_date": (base_date + timedelta(days=4, hours=15)).isoformat()
        },
        {
            "flat_number": "B201",
            "category": "cleaning",
            "priority": "low",
            "description": "Regular deep cleaning service needed.",
            "status": "pending",
            "source": "web",
            "appointment_date": (base_date + timedelta(days=5, hours=10)).isoformat()
        },
        {
            "flat_number": "103",
            "category": "appliance",
            "priority": "medium",
            "description": "Refrigerator not cooling properly, food is spoiling.",
            "status": "pending",
            "source": "voice",
            "appointment_date": (base_date + timedelta(days=6, hours=13)).isoformat()
        },
    ]
    
    print(f"Seeding {len(complaints_data)} complaints with appointment dates...")
    
    try:
        # Insert all complaints
        response = supabase.table("complaints").insert(complaints_data).execute()
        print(f"✅ Successfully seeded {len(complaints_data)} complaints!")
        print("\nScheduled visits:")
        for i, complaint in enumerate(complaints_data):
            visit_date = datetime.fromisoformat(complaint["appointment_date"])
            print(f"  {visit_date.strftime('%A, %b %d at %I:%M %p')} - Flat {complaint['flat_number']} ({complaint['category']})")
        return response.data
    except Exception as e:
        print(f"❌ Error seeding complaints: {e}")
        return None


if __name__ == "__main__":
    print("=" * 70)
    print("SEEDING COMPLAINTS WITH APPOINTMENT DATES")
    print("=" * 70)
    seed_complaints_with_appointments()
    print("=" * 70)
    print("\n💡 Now check the calendar in the frontend to see the scheduled visits!")
