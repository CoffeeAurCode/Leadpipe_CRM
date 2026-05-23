import os
from datetime import datetime, timezone
from supabase import Client

BACKEND_URL = os.environ.get("BACKEND_URL", "https://tenant-management-mvp.onrender.com")


def provision_vapi_for_manager(manager_id: str, db: Client) -> None:
    """
    Provision ONE VAPI lease assistant for this manager account.
    Claims one number from twilio_number_pool, creates the assistant,
    links them, and writes to manager_vapi_config.

    Uses service DB for pool + manager_vapi_config writes (RLS blocks user-scoped db).
    Idempotent: if manager already has status='active', exits immediately.
    """
    from vapi import Vapi
    from app.db.session import get_service_db
    from app.config import settings
    from app.services.vapi_agent_config import build_lease_config

    svc_db = get_service_db()
    client = Vapi(token=settings.PRIVATE_VAPI_API)

    try:
        existing = (
            svc_db.table("manager_vapi_config")
            .select("id, vapi_provisioning_status")
            .eq("manager_id", manager_id)
            .limit(1)
            .execute()
        )
        if existing.data and existing.data[0].get("vapi_provisioning_status") == "active":
            print(f"[VAPI PROVISION] Manager {manager_id} already active, skipping")
            return

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
        pool_id = pool_row["id"]
        vapi_phone_number_id = pool_row["vapi_phone_number_id"]
        phone_number = pool_row["phone_number"]

        svc_db.table("twilio_number_pool").update({
            "status": "assigned",
            "assigned_manager_id": manager_id,
            "assigned_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", pool_id).eq("status", "available").execute()

        lease_cfg = build_lease_config(BACKEND_URL, manager_id)
        lease = client.assistants.create(**lease_cfg)

        from vapi.phone_numbers.types import UpdatePhoneNumbersRequestBody_Twilio
        client.phone_numbers.update(
            vapi_phone_number_id,
            request=UpdatePhoneNumbersRequestBody_Twilio(assistant_id=lease.id),
        )

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
