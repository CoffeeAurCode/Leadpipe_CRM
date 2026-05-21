import os
from supabase import Client
from app.config import settings
from app.services.vapi_agent_config import build_lease_config

BACKEND_URL = os.environ.get("BACKEND_URL", "https://tenant-management-mvp.onrender.com")


def provision_vapi_for_property_group(
    property_group_id: str,
    pg_name: str,
    db: Client,
) -> None:
    """
    BackgroundTask triggered on new PropertyGroup creation.
    Provisions a dedicated lease VAPI assistant + phone number for the group.
    The complaint assistant is global (shared), so we only provision a lease assistant here.
    """
    from vapi import Vapi

    client = Vapi(token=settings.PRIVATE_VAPI_API)

    try:
        lease_cfg = build_lease_config(BACKEND_URL, property_group_id, pg_name)

        lease = client.assistants.create(**lease_cfg)

        phone = client.phone_numbers.create()

        client.phone_numbers.update(id=phone.id, assistant_id=lease.id)

        db.table("properties_list").update({
            "vapi_lease_assistant_id":  lease.id,
            "vapi_phone_number_id":     phone.id,
            "vapi_phone_number":        phone.number,
            "vapi_provisioning_status": "active",
        }).eq("id", property_group_id).execute()

        print(f"[VAPI PROVISION] Success for group {property_group_id}: assistant={lease.id} phone={phone.number}")

    except Exception as e:
        print(f"[VAPI PROVISION] Failed for group {property_group_id}: {e}")
        db.table("properties_list").update({
            "vapi_provisioning_status": "failed",
        }).eq("id", property_group_id).execute()
        raise
