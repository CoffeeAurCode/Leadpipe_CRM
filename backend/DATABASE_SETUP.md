# Database Setup Instructions

## ⚠️ Important: Apply Database Schema First

Before running the seed scripts or testing the new endpoints, you need to create the new tables in your Supabase database.

## Step 1: Apply Database Schema

1. Open your **Supabase Dashboard**
2. Navigate to the **SQL Editor** (from the left sidebar)
3. Create a new query
4. Copy and paste the contents of `backend/schema.sql` into the editor
5. Click **Run** to execute the SQL

This will create the new tables:
- `flats` - Store flat/apartment information
- `appointments` - Store appointment schedules
- Update `complaints` table with new `appointment_date` field
- Update `tenants` table with `flat_id` reference

## Step 2: Seed Mock Data

After the schema is applied, run these commands from the `backend` directory:

```powershell
# Seed flats data (30+ flats across 3 buildings)
python seed_flats.py

# Seed tenants data (20 tenants linked to flats)
python seed_tenants.py
```

## Step 3: Verify Tables Created

In Supabase, run this query to verify all tables exist:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

You should see:
- appointments
- call_logs
- complaints
- flats
- tenants
- units
- users

## Step 4: Test the New Endpoints

Start the backend server:

```powershell
cd backend
uvicorn app.main:main --reload
```

Test the flat verification endpoint (for VAPI):

```powershell
curl -X POST http://localhost:8000/flats/verify -H "Content-Type: application/json" -d "{\"flat_number\": \"101\"}"
```

Expected response:
```json
{
  "exists": true,
  "flat": {
    "id": 1,
    "flat_number": "101",
    "building_name": "Main Building",
    "floor_number": 1,
    "bedrooms": 2,
    "occupied": true,
    "created_at": "2024-..."
  }
}
```

## Next Steps

After database setup is complete, the backend is ready. Then we'll proceed to:
- Frontend calendar integration with appointments
- Update complaint forms with new fields
- Test VAPI integration with flat verification
