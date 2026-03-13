import logging
from fastapi import APIRouter, Depends
from supabase import Client
from app.db.session import get_db
from app.schemas.workflow import SmsWorkflowRequest, SmsWorkflowResponse, SmsResult
from app.integrations.twilio_client import get_twilio_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["Workflow"])


@router.post("/send-sms", response_model=SmsWorkflowResponse)
async def send_sms_workflow(
    payload: SmsWorkflowRequest,
    db: Client = Depends(get_db),
):
    uuid_strs = [str(uid) for uid in payload.tenant_ids]
    needs_unit = "{unit}" in payload.message

    # ── Batch-fetch tenants (phone, name, flat_uuid) ──────────────────────────
    tenant_resp = (
        db.table("tenants")
        .select("uuid, phone, name, flat_uuid")
        .in_("uuid", uuid_strs)
        .execute()
    )
    tenant_map = {row["uuid"]: row for row in (tenant_resp.data or [])}

    # ── Batch-fetch flat numbers if {unit} is used ────────────────────────────
    flat_map = {}
    if needs_unit:
        flat_uuids = [
            t["flat_uuid"] for t in tenant_map.values() if t.get("flat_uuid")
        ]
        if flat_uuids:
            flat_resp = (
                db.table("flats")
                .select("uuid, flat_number")
                .in_("uuid", flat_uuids)
                .execute()
            )
            flat_map = {row["uuid"]: row["flat_number"] for row in (flat_resp.data or [])}

    # ── Send per tenant ───────────────────────────────────────────────────────
    results = []
    for uuid_str in uuid_strs:
        tenant = tenant_map.get(uuid_str)

        if not tenant:
            logger.warning(f"Tenant not found: {uuid_str}")
            results.append(SmsResult(tenant_id=uuid_str, success=False, sid=None))
            continue

        phone = tenant.get("phone")
        if not phone:
            logger.warning(f"Tenant {uuid_str} has no phone number")
            results.append(SmsResult(tenant_id=uuid_str, success=False, sid=None))
            continue

        name = tenant.get("name") or "Tenant"
        flat_uuid = tenant.get("flat_uuid")
        unit = flat_map.get(flat_uuid, "Unknown Flat") if flat_uuid else "Unknown Flat"

        personalised = payload.message.replace("{name}", name).replace("{unit}", unit)

        sid = get_twilio_client().send_sms(to=phone, message=personalised)
        if sid:
            logger.info(f"SMS sent to tenant {uuid_str}, SID: {sid}")
            results.append(SmsResult(tenant_id=uuid_str, success=True, sid=sid))
        else:
            logger.error(f"SMS failed for tenant {uuid_str}")
            results.append(SmsResult(tenant_id=uuid_str, success=False, sid=None))

    return SmsWorkflowResponse(results=results)
