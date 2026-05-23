"""
Push the latest vapi_agent_config.py system prompt to all active per-manager lease assistants.

Run from the project root:
    python backend/scripts/update_lease_agents.py

Requires .env with SUPABASE_URL, SUPABASE_SERVICE_KEY, PRIVATE_VAPI_API.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from supabase import create_client
from vapi import Vapi
from vapi.core.api_error import ApiError

from app.config import settings
from app.services.vapi_agent_config import build_lease_config

BACKEND_URL = "https://tenant-management-mvp.onrender.com"


def main():
    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    client = Vapi(token=settings.PRIVATE_VAPI_API)

    rows = (
        db.table("manager_vapi_config")
        .select("manager_id, vapi_lease_assistant_id, vapi_provisioning_status")
        .eq("vapi_provisioning_status", "active")
        .execute()
    )

    agents = rows.data or []
    print(f"Found {len(agents)} active lease agent(s) to update")
    print(f"Backend URL: {BACKEND_URL}")
    print("=" * 60)

    success = 0
    failed = 0
    for row in agents:
        manager_id = row["manager_id"]
        assistant_id = row.get("vapi_lease_assistant_id")
        if not assistant_id:
            print(f"  [{manager_id[:8]}] SKIP — no assistant_id in DB")
            continue

        cfg = build_lease_config(BACKEND_URL, manager_id)
        try:
            result = client.assistants.update(id=assistant_id, **cfg)
            print(f"  [{manager_id[:8]}] OK  assistant={result.id}")
            success += 1
        except ApiError as e:
            print(f"  [{manager_id[:8]}] FAILED {e.status_code}: {e.body}")
            failed += 1
        except Exception as e:
            print(f"  [{manager_id[:8]}] FAILED: {e}")
            failed += 1

    print("=" * 60)
    print(f"Done. {success} updated, {failed} failed.")


if __name__ == "__main__":
    main()
