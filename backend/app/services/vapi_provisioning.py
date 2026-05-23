import os
from datetime import datetime, timezone
from supabase import Client
from app.config import settings
from app.services.vapi_agent_config import build_lease_config

BACKEND_URL = os.environ.get("BACKEND_URL", "https://tenant-management-mvp.onrender.com")


def _assign_shared_agent_fallback(svc_db: Client, db: Client, property_group_id: str) -> None:
    """
    Assign the shared lease agent to a property group when no dedicated pool number is available.
    Both svc_db (for pool operations) and db (for properties_list update) are passed in.
    """
    shared_assistant_id = settings.VAPI_SHARED_LEASE_ASSISTANT_ID
    shared_number_id    = settings.VAPI_SHARED_LEASE_NUMBER_ID
    shared_phone        = settings.VAPI_SHARED_LEASE_PHONE_NUMBER

    if not shared_assistant_id or not shared_phone:
        print(f"[TWILIO PROVISION] Pool empty and shared agent not configured — marking group {property_group_id} as failed")
        db.table("properties_list").update({
            "vapi_provisioning_status": "failed",
        }).eq("id", property_group_id).execute()
        return

    db.table("properties_list").update({
        "vapi_lease_assistant_id":  shared_assistant_id,
        "vapi_phone_number_id":     shared_number_id,
        "vapi_phone_number":        shared_phone,
        "vapi_provisioning_status": "active",
    }).eq("id", property_group_id).execute()

    print(f"[TWILIO PROVISION] Pool empty — shared agent assigned to group {property_group_id}: phone={shared_phone}")


def provision_vapi_for_property_group(
    property_group_id: str,
    pg_name: str,
    db: Client,
) -> None:
    """
    BackgroundTask triggered on new PropertyGroup creation.
    Picks an available Twilio number from twilio_number_pool, creates a per-group
    lease assistant in VAPI, and links them together.

    Uses the service DB for pool operations (RLS blocks the user-scoped db arg
    from writing twilio_number_pool).
    """
    from vapi import Vapi
    from app.db.session import get_service_db

    svc_db = get_service_db()
    client = Vapi(token=settings.PRIVATE_VAPI_API)

    try:
        # 1. Claim the first available pool entry (FIFO by created_at)
        pool_resp = (
            svc_db.table("twilio_number_pool")
            .select("id, phone_number, vapi_phone_number_id")
            .eq("status", "available")
            .order("created_at")
            .limit(1)
            .execute()
        )
        if not pool_resp.data:
            # Pool is empty — fall back to shared lease agent so the group is never left as 'failed'
            _assign_shared_agent_fallback(svc_db, db, property_group_id)
            return

        pool_row = pool_resp.data[0]
        pool_id = pool_row["id"]
        vapi_phone_number_id = pool_row["vapi_phone_number_id"]
        phone_number = pool_row["phone_number"]

        # 2. Mark as assigned before creating the assistant (optimistic lock).
        #    The .eq("status", "available") guard ensures only one concurrent
        #    provisioning task can claim this row.
        svc_db.table("twilio_number_pool").update({
            "status": "assigned",
            "assigned_property_group_id": property_group_id,
            "assigned_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", pool_id).eq("status", "available").execute()

        # 3. Create the per-group lease assistant in VAPI
        lease_cfg = build_lease_config(BACKEND_URL, property_group_id, pg_name)
        lease = client.assistants.create(**lease_cfg)

        # 4. Link the assistant to the Twilio phone number in VAPI.
        #    Try UpdatePhoneNumberDto first; fall back to keyword-arg form if
        #    the installed SDK version uses a different import path.
        try:
            from vapi.types import UpdatePhoneNumberDto
            client.phone_numbers.update(
                vapi_phone_number_id,
                request=UpdatePhoneNumberDto(assistant_id=lease.id),
            )
        except ImportError:
            client.phone_numbers.update(vapi_phone_number_id, assistant_id=lease.id)

        # 5. Persist IDs on the property group row
        db.table("properties_list").update({
            "vapi_lease_assistant_id":  lease.id,
            "vapi_phone_number_id":     vapi_phone_number_id,
            "vapi_phone_number":        phone_number,
            "vapi_provisioning_status": "active",
        }).eq("id", property_group_id).execute()

        print(
            f"[TWILIO PROVISION] Success for group {property_group_id}: "
            f"assistant={lease.id} phone={phone_number}"
        )

    except Exception as e:
        print(f"[TWILIO PROVISION] Failed for group {property_group_id}: {e}")
        db.table("properties_list").update({
            "vapi_provisioning_status": "failed",
        }).eq("id", property_group_id).execute()
        raise
