import calendar
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import Client
from typing import List
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription
from app.schemas.workflow import SmsWorkflowRequest, SmsWorkflowResponse, SmsResult
from app.integrations.twilio_client import get_twilio_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["Workflow"])


def _next_due_date(billing_day: int, today: date) -> date:
    """Return the next rent due date given a billing day-of-month and today's date.

    Clamps the day to the last valid day of the target month to handle billing
    days of 29/30/31 in short months (e.g. billing day 31 in February → Feb 28/29).
    """
    def clamp(year: int, month: int, day: int) -> date:
        last = calendar.monthrange(year, month)[1]
        return date(year, month, min(day, last))

    candidate = clamp(today.year, today.month, billing_day)
    if today < candidate:
        return candidate
    next_month = today + relativedelta(months=1)
    return clamp(next_month.year, next_month.month, billing_day)


@router.post("/send-sms", response_model=SmsWorkflowResponse)
async def send_sms_workflow(
    payload: SmsWorkflowRequest,
    user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db),
):
    uuid_strs = [str(uid) for uid in payload.tenant_ids]
    needs_unit = "{unit}" in payload.message
    needs_rent = "{rent}" in payload.message
    needs_date = "{date}" in payload.message

    # ── Batch-fetch tenants (phone, name, flat_uuid) ──────────────────────────
    tenant_resp = (
        db.table("tenants")
        .select("uuid, phone, name, flat_uuid")
        .in_("uuid", uuid_strs)
        .execute()
    )
    tenant_map = {row["uuid"]: row for row in (tenant_resp.data or [])}

    # ── Collect flat_uuids whenever any flat-level lookup is needed ───────────
    flat_map = {}
    rent_map = {}
    due_date_map = {}

    if needs_unit or needs_rent or needs_date:
        flat_uuids = [
            t["flat_uuid"] for t in tenant_map.values() if t.get("flat_uuid")
        ]

        # ── Batch-fetch flat numbers if {unit} is used ────────────────────────
        if needs_unit and flat_uuids:
            flat_resp = (
                db.table("flats")
                .select("uuid, flat_number")
                .in_("uuid", flat_uuids)
                .execute()
            )
            flat_map = {row["uuid"]: row["flat_number"] for row in (flat_resp.data or [])}

        # ── Batch-fetch rent data if {rent} or {date} is used ────────────────
        if (needs_rent or needs_date) and flat_uuids:
            rents_resp = (
                db.table("rents")
                .select("flat_uuid, monthly_rent, effective_from")
                .eq("is_active", True)
                .in_("flat_uuid", flat_uuids)
                .execute()
            )
            today = date.today()
            for row in (rents_resp.data or []):
                fuuid = row["flat_uuid"]
                if needs_rent:
                    amount = row.get("monthly_rent")
                    if amount is not None:
                        rent_map[fuuid] = f"${amount:,.0f}"
                if needs_date:
                    raw = row.get("effective_from")
                    if raw:
                        try:
                            eff = date.fromisoformat(str(raw).split("T")[0])
                            due = _next_due_date(eff.day, today)
                            due_date_map[fuuid] = f"{due.strftime('%B')} {due.day}"
                        except (ValueError, AttributeError):
                            pass

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
        rent = rent_map.get(flat_uuid, "N/A") if flat_uuid else "N/A"
        due = due_date_map.get(flat_uuid, "N/A") if flat_uuid else "N/A"

        personalised = (
            payload.message
            .replace("{name}", name)
            .replace("{unit}", unit)
            .replace("{rent}", rent)
            .replace("{date}", due)
        )

        sid = get_twilio_client().send_sms(to=phone, message=personalised)
        if sid:
            logger.info(f"SMS sent to tenant {uuid_str}, SID: {sid}")
            results.append(SmsResult(tenant_id=uuid_str, success=True, sid=sid))
        else:
            logger.error(f"SMS failed for tenant {uuid_str}")
            results.append(SmsResult(tenant_id=uuid_str, success=False, sid=None))

    return SmsWorkflowResponse(results=results)


_DEFAULT_TEMPLATES = [
    {"id": 1, "name": "Rent Reminder", "message": "Hi {name}, your rent of {rent} is due on {date}. Please pay on time."},
    {"id": 2, "name": "Maintenance Notice", "message": "Hi {name}, maintenance is scheduled for your unit {unit}."},
    {"id": 3, "name": "General Announcement", "message": "Hi {name}, this is an update from your property manager."},
]


@router.get("/sms-templates")
async def get_sms_templates(user: dict = Depends(require_active_subscription)):
    return _DEFAULT_TEMPLATES


class SmsTemplateCreate(BaseModel):
    name: str
    message: str


@router.post("/sms-templates", status_code=201)
async def create_sms_template(
    body: SmsTemplateCreate,
    user: dict = Depends(require_active_subscription),
):
    new_id = len(_DEFAULT_TEMPLATES) + 1
    return {"id": new_id, "name": body.name, "message": body.message}


@router.post("/sms-broadcast", response_model=SmsWorkflowResponse)
async def sms_broadcast(
    payload: SmsWorkflowRequest,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    return await send_sms_workflow(payload, user, db)
