"""
One-time script: provision a per-group VAPI lease assistant + phone number
for every property group that does not already have one (status != "active").

Run from the backend/ directory:
    python -m scripts.reprovision_existing_groups

Requires .env with SUPABASE_URL, SUPABASE_SERVICE_KEY, PRIVATE_VAPI_API, BACKEND_URL.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.config import settings
from app.services.vapi_provisioning import provision_vapi_for_property_group


def main():
    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    rows = (
        db.table("properties_list")
        .select("id, name, vapi_provisioning_status")
        .neq("vapi_provisioning_status", "active")
        .execute()
    )

    groups = rows.data or []
    print(f"Found {len(groups)} group(s) to provision")

    success = 0
    failed = 0
    for pg in groups:
        pg_id = pg["id"]
        pg_name = pg["name"] or "Unnamed"
        status = pg.get("vapi_provisioning_status", "unknown")
        print(f"\n[{pg_id}] '{pg_name}' (current status: {status})")
        try:
            provision_vapi_for_property_group(pg_id, pg_name, db)
            print(f"  -> SUCCESS")
            success += 1
        except Exception as e:
            print(f"  -> FAILED: {e}")
            failed += 1

    print(f"\nDone. {success} succeeded, {failed} failed.")


if __name__ == "__main__":
    main()
