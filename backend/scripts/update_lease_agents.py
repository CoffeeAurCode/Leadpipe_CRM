"""
Push the latest vapi_agent_config.py config to all active lease agents:
  - Per-manager agents (from manager_vapi_config table)
  - Shared lease agent (from VAPI_SHARED_LEASE_ASSISTANT_ID env var)

After each update, asserts serverMessages == ["end-of-call-report"]. Exits non-zero if any assertion fails.

Run from the project root:
    python backend/scripts/update_lease_agents.py [--dry-run]

Requires .env with SUPABASE_URL, SUPABASE_SERVICE_KEY, PRIVATE_VAPI_API, VAPI_SHARED_LEASE_ASSISTANT_ID.
"""
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from supabase import create_client
from vapi import Vapi
from vapi.core.api_error import ApiError

from app.config import settings
from app.services.vapi_agent_config import build_lease_config, build_lease_config_shared

BACKEND_URL = "https://tenant-management-mvp.onrender.com"
EXPECTED_SERVER_MESSAGES = ["end-of-call-report"]


def update_and_verify(client: Vapi, assistant_id: str, cfg: dict, label: str, dry_run: bool) -> bool:
    print(f"\n  [{label}]  id={assistant_id}")
    if dry_run:
        print(f"    DRY RUN — would update with name={cfg.get('name')}")
        return True

    try:
        result = client.assistants.update(id=assistant_id, **cfg)
        actual = getattr(result, "server_messages", None)
        if actual != EXPECTED_SERVER_MESSAGES:
            print(f"    [FAIL] serverMessages = {actual} — expected {EXPECTED_SERVER_MESSAGES}")
            return False
        print(f"    [OK]  name={result.name}  serverMessages={actual}")
        return True
    except ApiError as e:
        print(f"    [FAIL] {e.status_code}: {e.body}")
        return False
    except Exception as e:
        print(f"    [FAIL] {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without executing")
    args = parser.parse_args()

    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    client = Vapi(token=settings.PRIVATE_VAPI_API)

    shared_id = os.environ.get("VAPI_SHARED_LEASE_ASSISTANT_ID", "")

    rows = (
        db.table("manager_vapi_config")
        .select("manager_id, vapi_lease_assistant_id")
        .eq("vapi_provisioning_status", "active")
        .execute()
    )
    agents = rows.data or []

    total = len(agents) + (1 if shared_id else 0)
    print(f"Lease agents to update: {len(agents)} per-manager + {'1 shared' if shared_id else '0 shared'}")
    print(f"Backend URL: {BACKEND_URL}")
    if args.dry_run:
        print("DRY RUN mode — no changes will be made")
    print("=" * 60)

    success = 0
    failed = 0

    for row in agents:
        manager_id = row["manager_id"]
        assistant_id = row.get("vapi_lease_assistant_id")
        if not assistant_id:
            print(f"\n  [{manager_id[:8]}]  SKIP — no assistant_id in DB")
            continue
        cfg = build_lease_config(BACKEND_URL, manager_id)
        ok = update_and_verify(client, assistant_id, cfg, manager_id[:8], args.dry_run)
        if ok:
            success += 1
        else:
            failed += 1

    if shared_id:
        cfg = build_lease_config_shared(BACKEND_URL)
        ok = update_and_verify(client, shared_id, cfg, "shared", args.dry_run)
        if ok:
            success += 1
        else:
            failed += 1
    else:
        print("\n  [shared]  SKIP — VAPI_SHARED_LEASE_ASSISTANT_ID not set")

    print("\n" + "=" * 60)
    print(f"Done. {success} updated, {failed} failed.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
