"""
seed_features.py
================
Backfill ALL flats that are missing feature rows in property_features.

Run from the backend/ directory with the project venv:
    .\\venv\\Scripts\\python.exe seed_features.py
"""

import os
import sys

# Ensure backend app modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env manually (no python-dotenv needed)
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    sys.exit(1)

# Default feature flags — matches Feature enum in core/features.py
DEFAULT_FEATURES = [
    ("rent_management",  True),
    ("rent_due_date",    False),
    ("flat_details",     True),
    ("voice_calls",      False),
    ("sms_reminders",    False),
    ("email_reminders",  False),
    ("tenant_details",   True),
    ("tenant_documents", False),
]


def main():
    db = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 1. Fetch all flat integer IDs
    flats_resp = db.table("flats").select("id, flat_number").execute()
    all_flats = flats_resp.data or []
    print(f"Total flats in DB: {len(all_flats)}")

    # 2. Fetch all unit_ids already in property_features (any feature row = covered)
    existing_resp = db.table("property_features").select("unit_id").execute()
    existing_unit_ids = {row["unit_id"] for row in (existing_resp.data or [])}
    print(f"Units already in property_features: {len(existing_unit_ids)}")

    # 3. Find flats with NO feature rows at all
    missing_flats = [f for f in all_flats if f["id"] not in existing_unit_ids]
    print(f"Flats missing from property_features: {len(missing_flats)}")

    if not missing_flats:
        print("Nothing to backfill — all flats already have feature rows.")
        return

    # 4. Build upsert rows
    rows = []
    for flat in missing_flats:
        for feature_key, enabled in DEFAULT_FEATURES:
            rows.append({
                "unit_id": flat["id"],
                "feature_key": feature_key,
                "enabled": enabled,
            })

    print(f"Inserting {len(rows)} rows ({len(missing_flats)} flats x {len(DEFAULT_FEATURES)} features)...")

    # 5. Upsert in batches of 500
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i: i + batch_size]
        db.table("property_features") \
            .upsert(batch, on_conflict="unit_id,feature_key") \
            .execute()
        print(f"  Upserted rows {i + 1} - {i + len(batch)}")

    # 6. Final count
    final_resp = db.table("property_features").select("unit_id").execute()
    unique_units = len({row["unit_id"] for row in (final_resp.data or [])})
    print(f"\nDone! property_features now covers {unique_units} unique units.")


if __name__ == "__main__":
    main()
