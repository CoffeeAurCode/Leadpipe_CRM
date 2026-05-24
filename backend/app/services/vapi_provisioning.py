import os
import httpx
from datetime import datetime, timezone
from supabase import Client

BACKEND_URL = os.environ.get("BACKEND_URL", "https://tenant-management-mvp.onrender.com")
VAPI_API_BASE = "https://api.vapi.ai"


def provision_vapi_for_manager(manager_id: str, db: Client) -> None:
    from vapi import Vapi
    from app.db.session import get_service_db
    from app.config import settings
    from app.services.vapi_agent_config import build_lease_config

    svc_db = get_service_db()
    client = Vapi(token=settings.PRIVATE_VAPI_API)

    try:
        existing = (
            svc_db.table("manager_vapi_config")
            .select("id, vapi_provisioning_status, vapi_lease_assistant_id")
            .eq("manager_id", manager_id)
            .limit(1)
            .execute()
        )
        if existing.data and existing.data[0].get("vapi_provisioning_status") == "active":
            print(f"[VAPI PROVISION] Manager {manager_id} already active, skipping")
            return

        existing_assistant_id = existing.data[0].get("vapi_lease_assistant_id") if existing.data else None

        # Guard: if this manager already claimed a pool row, don't claim another.
        # Handles concurrent retries landing here simultaneously.
        already_claimed = (
            svc_db.table("twilio_number_pool")
            .select("id, phone_number, vapi_phone_number_id")
            .eq("assigned_manager_id", manager_id)
            .limit(1)
            .execute()
        )
        if already_claimed.data:
            pool_row = already_claimed.data[0]
            print(f"[VAPI PROVISION] Manager {manager_id} already has pool row {pool_row['id']}, reusing")
        else:
            pool_resp = (
                svc_db.table("twilio_number_pool")
                .select("id, phone_number, vapi_phone_number_id")
                .eq("status", "available")
                .order("created_at")
                .limit(1)
                .execute()
            )
            if not pool_resp.data:
                print(f"[VAPI PROVISION] Pool empty — marking manager {manager_id} as failed")
                svc_db.table("manager_vapi_config").upsert({
                    "manager_id": manager_id,
                    "vapi_provisioning_status": "failed",
                }, on_conflict="manager_id").execute()
                return

            pool_row = pool_resp.data[0]
            # Atomic claim: only succeeds if still available; DB unique index prevents double-claim.
            svc_db.table("twilio_number_pool").update({
                "status": "assigned",
                "assigned_manager_id": manager_id,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", pool_row["id"]).eq("status", "available").execute()

        pool_id = pool_row["id"]
        vapi_phone_number_id = pool_row["vapi_phone_number_id"]
        phone_number = pool_row["phone_number"]

        lease_cfg = build_lease_config(BACKEND_URL, manager_id)
        if existing_assistant_id:
            print(f"[VAPI PROVISION] Updating existing assistant {existing_assistant_id} (no duplicate)")
            lease = client.assistants.update(id=existing_assistant_id, **lease_cfg)
        else:
            lease = client.assistants.create(**lease_cfg)

        # VAPI's update endpoint rejects any `provider` field in the body.
        # The SDK discriminated-union types always include it, so call the REST API directly.
        resp = httpx.patch(
            f"{VAPI_API_BASE}/phone-number/{vapi_phone_number_id}",
            headers={
                "Authorization": f"Bearer {settings.PRIVATE_VAPI_API}",
                "Content-Type": "application/json",
            },
            json={"assistantId": lease.id},
            timeout=30,
        )
        resp.raise_for_status()

        svc_db.table("manager_vapi_config").upsert({
            "manager_id": manager_id,
            "vapi_lease_assistant_id": lease.id,
            "vapi_phone_number_id": vapi_phone_number_id,
            "vapi_phone_number": phone_number,
            "vapi_provisioning_status": "active",
            "pool_row_id": pool_id,
        }, on_conflict="manager_id").execute()

        print(
            f"[VAPI PROVISION] Success for manager {manager_id}: "
            f"assistant={lease.id} phone={phone_number}"
        )

    except Exception as e:
        print(f"[VAPI PROVISION] Failed for manager {manager_id}: {e}")
        svc_db.table("manager_vapi_config").upsert({
            "manager_id": manager_id,
            "vapi_provisioning_status": "failed",
        }, on_conflict="manager_id").execute()
        raise
