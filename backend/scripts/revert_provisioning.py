"""
Revert script: cleans up all orphaned VAPI objects created by failed provisioning
runs, then resets the DB provisioning status to not_applicable on all groups.

Run from backend/:
    python -m scripts.revert_provisioning

What it does:
  1. Lists all VAPI assistants — deletes every "Lease Agent" assistant whose ID is
     NOT one of the known-good .env IDs.
  2. Lists all VAPI phone numbers — deletes every VAPI-provisioned number (601/401
     area codes etc.) whose ID is NOT a known-good .env ID.
  3. Resets properties_list.vapi_provisioning_status to "not_applicable" for every
     group that has no vapi_lease_assistant_id stored (i.e. provisioning never
     fully completed).
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from vapi import Vapi
from supabase import create_client
from app.config import settings

KEEP_ASSISTANT_IDS = {
    settings.VAPI_ASSISTANT_ID,
    settings.VAPI_COMPLAINT_ASSISTANT_ID,
    settings.VAPI_SHARED_LEASE_ASSISTANT_ID,
}

KEEP_NUMBER_IDS = {
    settings.VAPI_NUMBER_ID,
    settings.VAPI_COMPLAINT_NUMBER_ID,
    settings.VAPI_SHARED_LEASE_NUMBER_ID,
}

# Remove None values (unset env vars)
KEEP_ASSISTANT_IDS.discard(None)
KEEP_NUMBER_IDS.discard(None)

client = Vapi(token=settings.PRIVATE_VAPI_API)
db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def delete_orphaned_assistants():
    print("\n=== VAPI ASSISTANTS ===")
    assistants = client.assistants.list()
    deleted = 0
    kept = 0
    for a in assistants:
        if a.id in KEEP_ASSISTANT_IDS:
            print(f"  KEEP   [{a.id}]  {a.name}")
            kept += 1
        else:
            print(f"  DELETE [{a.id}]  {a.name}")
            try:
                client.assistants.delete(a.id)
                deleted += 1
                time.sleep(0.8)
            except Exception as e:
                print(f"         ERROR: {e}")
                time.sleep(2)
    print(f"\n  Kept: {kept}  |  Deleted: {deleted}")


def delete_orphaned_phone_numbers():
    print("\n=== VAPI PHONE NUMBERS ===")
    numbers = client.phone_numbers.list()
    deleted = 0
    kept = 0
    for n in numbers:
        num_str = getattr(n, "number", None) or getattr(n, "phone_number", None) or "?"
        if n.id in KEEP_NUMBER_IDS:
            print(f"  KEEP   [{n.id}]  {num_str}")
            kept += 1
        else:
            print(f"  DELETE [{n.id}]  {num_str}")
            try:
                client.phone_numbers.delete(n.id)
                deleted += 1
                time.sleep(0.8)
            except Exception as e:
                print(f"         ERROR: {e}")
                time.sleep(2)
    print(f"\n  Kept: {kept}  |  Deleted: {deleted}")


def reset_db_provisioning_status():
    print("\n=== DB RESET ===")
    # Reset every property group that has no vapi_lease_assistant_id stored.
    # These are groups where provisioning was attempted but never fully completed.
    resp = (
        db.table("properties_list")
        .update({"vapi_provisioning_status": "not_applicable"})
        .is_("vapi_lease_assistant_id", "null")
        .execute()
    )
    count = len(resp.data) if resp.data else 0
    print(f"  Reset {count} group(s) to not_applicable")


if __name__ == "__main__":
    print("Starting revert...")
    delete_orphaned_assistants()
    delete_orphaned_phone_numbers()
    reset_db_provisioning_status()
    print("\nDone.")
