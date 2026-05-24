"""
One-time cleanup: delete duplicate VAPI lease agents, keeping only the ones
registered as active in manager_vapi_config.

Run from backend/ directory:
    py -3.13 scripts/cleanup_duplicate_lease_agents.py

Pass --dry-run to preview without deleting.
"""
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from vapi import Vapi
from supabase import create_client
from app.config import settings

VAPI_API_KEY = os.environ.get("PRIVATE_VAPI_API", "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview deletions without executing")
    args = parser.parse_args()

    if not VAPI_API_KEY:
        print("[ERROR] PRIVATE_VAPI_API not set in .env")
        sys.exit(1)

    client = Vapi(token=VAPI_API_KEY)
    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    # Fetch all active assistant IDs from DB
    rows = db.table("manager_vapi_config").select("vapi_lease_assistant_id, vapi_provisioning_status").execute()
    active_ids = {
        r["vapi_lease_assistant_id"]
        for r in (rows.data or [])
        if r.get("vapi_provisioning_status") == "active" and r.get("vapi_lease_assistant_id")
    }
    # Also protect the shared lease assistant
    shared_id = os.environ.get("VAPI_SHARED_LEASE_ASSISTANT_ID")
    if shared_id:
        active_ids.add(shared_id)
    print(f"Active VAPI assistant IDs in DB: {len(active_ids)}")
    for aid in active_ids:
        print(f"  KEEP  {aid}")

    # Fetch all assistants from VAPI and find lease agent duplicates
    all_assistants = client.assistants.list()
    lease_agents = [a for a in all_assistants if a.name and (a.name.startswith("Lease Agent [") or a.name.startswith("Shared Lease Agent"))]

    print(f"\nLease agents found in VAPI: {len(lease_agents)}")
    to_delete = []
    for a in lease_agents:
        if a.id in active_ids:
            print(f"  KEEP  {a.id}  {a.name}")
        else:
            print(f"  DELETE  {a.id}  {a.name}")
            to_delete.append(a)

    if not to_delete:
        print("\nNothing to delete.")
        return

    print(f"\n{len(to_delete)} agent(s) will be deleted.")
    if args.dry_run:
        print("DRY RUN — no deletions performed.")
        return

    confirm = input("Type 'yes' to confirm deletion: ")
    if confirm.strip().lower() != "yes":
        print("Aborted.")
        return

    for a in to_delete:
        try:
            client.assistants.delete(a.id)
            print(f"  Deleted {a.id}  {a.name}")
        except Exception as e:
            print(f"  FAILED to delete {a.id}: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
