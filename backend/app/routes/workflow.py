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
    results = []

    for tenant_uuid in payload.tenant_ids:
        uuid_str = str(tenant_uuid)
        tenant_resp = db.table("tenants").select("phone").eq("uuid", uuid_str).execute()

        if not tenant_resp.data:
            logger.warning(f"Tenant not found: {uuid_str}")
            results.append(SmsResult(tenant_id=tenant_uuid, success=False, sid=None))
            continue

        phone = tenant_resp.data[0].get("phone")
        if not phone:
            logger.warning(f"Tenant {uuid_str} has no phone number")
            results.append(SmsResult(tenant_id=tenant_uuid, success=False, sid=None))
            continue

        sid = get_twilio_client().send_sms(to=phone, message=payload.message)
        if sid:
            logger.info(f"SMS sent to tenant {uuid_str}, SID: {sid}")
            results.append(SmsResult(tenant_id=tenant_uuid, success=True, sid=sid))
        else:
            logger.error(f"SMS failed for tenant {uuid_str}")
            results.append(SmsResult(tenant_id=tenant_uuid, success=False, sid=None))

    return SmsWorkflowResponse(results=results)
