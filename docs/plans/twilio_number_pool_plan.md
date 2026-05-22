# Twilio Number Pool — Implementation Plan

## Problem

VAPI's free tier has a hard limit on the number of VAPI-owned phone numbers that can be provisioned. With 10+ property groups, every new group creation triggers `CreatePhoneNumbersRequest_Vapi`, which hits the limit and fails with "No available area codes." This makes per-group lease agent provisioning unreliable.

## Solution

Pre-register Twilio-owned numbers into VAPI once (via admin script), storing them in a `twilio_number_pool` DB table. When a new property group is created, the provisioning service **picks a number from the pool** instead of asking VAPI to acquire a new one. The per-group assistant is still created fresh on demand and linked to the pooled number via VAPI's phone number update API.

## Do NOT Touch

The following numbers are live and must never be reassigned:

| Env Var | Number | Role |
|---|---|---|
| `VAPI_NUMBER_ID` | +19734904520 | Legacy complaint + outbound |
| `VAPI_COMPLAINT_NUMBER_ID` | +14382314283 | Complaint agent inbound |
| `VAPI_SHARED_LEASE_NUMBER_ID` | +14313415768 | Shared lease agent |

---

## 1. Database Changes

### Migration 1 — `notifications` table (prerequisite)

The `notifications` table is referenced by `NotificationPanel.jsx` and `routes/notifications.py` but may not exist in production yet:

```sql
CREATE TABLE IF NOT EXISTS notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id  UUID NOT NULL REFERENCES auth.users(id),
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    type        TEXT NOT NULL,  -- 'appointment' | 'complaint' | 'rent' | 'system' | 'lead'
    entity_id   UUID,           -- lead UUID for type='lead'
    is_read     BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notifications_manager
    ON notifications(manager_id, created_at DESC);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "manager sees own notifications"
    ON notifications FOR ALL
    USING (manager_id = auth.uid());
```

### Migration 2 — `twilio_number_pool` table (new)

```sql
CREATE TABLE twilio_number_pool (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number                TEXT NOT NULL UNIQUE,  -- E.164: +15551234567
    vapi_phone_number_id        TEXT NOT NULL UNIQUE,  -- VAPI's internal phone number ID
    status                      TEXT NOT NULL DEFAULT 'available'
                                    CHECK (status IN ('available', 'assigned')),
    assigned_property_group_id  UUID REFERENCES properties_list(id) ON DELETE SET NULL,
    assigned_at                 TIMESTAMPTZ,
    notes                       TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE twilio_number_pool ENABLE ROW LEVEL SECURITY;

-- Only service role reads/writes this table (admin script + provisioning background task)
-- Managers see their phone number through properties_list.vapi_phone_number, not this table.
CREATE POLICY "service only"
    ON twilio_number_pool FOR ALL
    TO service_role
    USING (true);
```

---

## 2. Config Changes

`TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` are in `.env` but missing from `config.py`'s `Settings` class. Add them so provisioning code can use `settings.*` instead of `os.getenv()`:

**File:** `backend/app/config.py`

```python
# Twilio
TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "")
```

---

## 3. Admin Script — `add_twilio_number_to_vapi.py`

**File:** `backend/scripts/add_twilio_number_to_vapi.py`

Purpose: one-time script to register a Twilio-purchased E.164 number into VAPI and store the resulting VAPI phone number ID in the pool table. Run once per number you want available for auto-assignment.

```python
"""
Register a Twilio-owned number into VAPI and add it to the pool.

Usage:
    python backend/scripts/add_twilio_number_to_vapi.py +15551234567
    python backend/scripts/add_twilio_number_to_vapi.py +15551234567 --notes "US East pool"
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.config import settings
from supabase import create_client


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phone_number", help="E.164 Twilio number, e.g. +15551234567")
    parser.add_argument("--notes", default="", help="Optional notes for this pool entry")
    args = parser.parse_args()

    number = args.phone_number.strip()
    if not number.startswith("+"):
        print(f"ERROR: phone_number must be E.164 (start with +). Got: {number}")
        sys.exit(1)

    from vapi import Vapi
    from vapi.phone_numbers.types import CreatePhoneNumbersRequest_Twilio

    client = Vapi(token=settings.PRIVATE_VAPI_API)

    print(f"Registering {number} into VAPI as a Twilio number...")
    phone = client.phone_numbers.create(
        request=CreatePhoneNumbersRequest_Twilio(
            provider="twilio",
            number=number,
            twilio_account_sid=settings.TWILIO_ACCOUNT_SID,
            twilio_auth_token=settings.TWILIO_AUTH_TOKEN,
            # No assistant_id here — will be linked at property group creation time
        )
    )
    print(f"VAPI registered: id={phone.id} number={phone.number}")

    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    db.table("twilio_number_pool").insert({
        "phone_number": phone.number,
        "vapi_phone_number_id": phone.id,
        "status": "available",
        "notes": args.notes,
    }).execute()

    print(f"Pool entry created. Number {phone.number} is now available for auto-assignment.")


if __name__ == "__main__":
    main()
```

---

## 4. Updated Provisioning Service

**File:** `backend/app/services/vapi_provisioning.py` — replace the existing implementation.

The new function `provision_twilio_pool_for_property_group` replaces `provision_vapi_for_property_group`. The signature and call site in `property_groups.py` remain unchanged — only the internals change.

```python
import os
from datetime import datetime, timezone
from supabase import Client
from app.config import settings
from app.services.vapi_agent_config import build_lease_config
from app.db.session import get_service_db

BACKEND_URL = os.environ.get("BACKEND_URL", "https://tenant-management-mvp.onrender.com")


def provision_vapi_for_property_group(
    property_group_id: str,
    pg_name: str,
    db: Client,
) -> None:
    """
    BackgroundTask triggered on new PropertyGroup creation.
    Picks an available Twilio number from the pool, creates a per-group lease
    assistant, and links them together in VAPI.

    Uses the service DB (not the user-scoped db arg) for pool operations
    because the authenticated db has RLS which blocks twilio_number_pool writes.
    """
    from vapi import Vapi
    from vapi.phone_numbers.types import UpdatePhoneNumberDto

    svc_db = get_service_db()
    client = Vapi(token=settings.PRIVATE_VAPI_API)

    try:
        # 1. Pick available number (service DB — bypasses RLS)
        pool_resp = (
            svc_db.table("twilio_number_pool")
            .select("id, phone_number, vapi_phone_number_id")
            .eq("status", "available")
            .order("created_at")
            .limit(1)
            .execute()
        )
        if not pool_resp.data:
            raise Exception(
                "No available numbers in twilio_number_pool. "
                "Run: python backend/scripts/add_twilio_number_to_vapi.py <E.164>"
            )

        pool_row = pool_resp.data[0]
        pool_id = pool_row["id"]
        vapi_phone_number_id = pool_row["vapi_phone_number_id"]
        phone_number = pool_row["phone_number"]

        # 2. Claim the slot immediately (prevents race if two groups are created simultaneously)
        svc_db.table("twilio_number_pool").update({
            "status": "assigned",
            "assigned_property_group_id": property_group_id,
            "assigned_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", pool_id).eq("status", "available").execute()

        # 3. Create the per-group lease assistant in VAPI
        lease_cfg = build_lease_config(BACKEND_URL, property_group_id, pg_name)
        lease = client.assistants.create(**lease_cfg)

        # 4. Link the assistant to the Twilio phone number in VAPI
        client.phone_numbers.update(
            vapi_phone_number_id,
            request=UpdatePhoneNumberDto(assistant_id=lease.id),
        )

        # 5. Store IDs + mark active on the property group
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
```

### Notes on VAPI SDK call for `UpdatePhoneNumberDto`

`UpdatePhoneNumberDto` is the request body type for `client.phone_numbers.update(id, request=...)`.
If the SDK exposes it as keyword args instead, use:

```python
client.phone_numbers.update(vapi_phone_number_id, assistant_id=lease.id)
```

Check the installed SDK version with `pip show vapi-server-sdk`. Import paths may be:
- `from vapi.types import UpdatePhoneNumberDto`
- `from vapi.phone_numbers.types import UpdatePhoneNumberDto`

---

## 5. Property Groups Route — No Change

`backend/app/routes/property_groups.py` does not change. It already calls:

```python
from app.services.vapi_provisioning import provision_vapi_for_property_group
background_tasks.add_task(provision_vapi_for_property_group, pg_id, pg_name, db)
```

Since we kept the function name the same, the call site is untouched.

The `/property-groups/{id}/provision-voice` retry endpoint also works unchanged.

---

## 6. Lead Notifications — Qualified Lead Bell Alert

The notification infrastructure is **already fully built**:
- `notifications` table (Migration 1 above creates it)
- `GET /notifications`, `PATCH /notifications/{id}/read`, `POST /notifications/read-all` in `routes/notifications.py`
- `NotificationPanel.jsx` with bell icon, unread badge, 30-second polling, mark-as-read
- `fetchNotifications`, `markNotificationRead`, `markAllNotificationsRead` in `apiService.js`

### 6a. Wire the webhook → notification insert

**File:** `backend/app/routes/voice.py`, inside `lease_lead_webhook` — after the `INSERT` into `lease_leads` succeeds.

Find the block that logs `[LEAD WEBHOOK] Saved lead` and add the notification insert immediately after:

```python
# After successful lead insert:
if result.data:
    saved_lead = result.data[0]
    if saved_lead.get("qualification_status") == "qualified" and manager_id:
        try:
            caller_name = lead_payload.get("caller_name") or "Unknown caller"
            svc_db.table("notifications").insert({
                "manager_id": manager_id,
                "title": "New Qualified Lead",
                "body": f"{caller_name} is interested in leasing — review their details.",
                "type": "lead",
                "entity_id": str(saved_lead["uuid"]),
                "is_read": False,
            }).execute()
        except Exception as notif_err:
            print(f"[LEAD NOTIFICATION] Failed (non-fatal): {notif_err}")
```

This is non-fatal: if the insert fails (e.g., notifications table not migrated yet), the lead is still saved and the webhook still returns 200.

### 6b. Add `lead` color to NotificationPanel

**File:** `frontend/src/components/NotificationPanel.jsx`, line 6 `TYPE_COLORS` map:

```js
const TYPE_COLORS = {
    appointment: 'bg-blue-500/15 text-blue-400',
    complaint:   'bg-red-500/15 text-red-500',
    rent:        'bg-emerald-500/15 text-emerald-500',
    lead:        'bg-violet-500/15 text-violet-500',   // ← add this line
    system:      'bg-secondary text-muted-foreground',
};
```

That's the entire frontend change. The bell badge, polling, and mark-as-read all work without any further modification.

---

## 7. Testing Plan

### 7a. Pool Registration Test

```bash
# Register a test number
python backend/scripts/add_twilio_number_to_vapi.py +15551234567 --notes "test pool entry"

# Verify in DB
# Expected: row in twilio_number_pool with status='available', vapi_phone_number_id set
```

### 7b. Auto-Assignment Integration Test

```bash
# Integration test file: backend/tests/test_twilio_provisioning.py

# Prerequisites:
# - At least one 'available' row in twilio_number_pool
# - Valid PRIVATE_VAPI_API key in .env

# Test 1: create property group → provisioning background task runs
# Expected: properties_list row has vapi_provisioning_status='active', vapi_phone_number set
# Expected: twilio_number_pool row transitions to status='assigned'
# Expected: VAPI phone number object has assistant_id set to the new lease assistant

# Test 2: pool exhaustion
# Remove all 'available' pool entries, create a new property group
# Expected: vapi_provisioning_status='failed' in DB
# Expected: error log "[TWILIO PROVISION] No available numbers in twilio_number_pool"

# Test 3: pool race condition
# Two property groups created simultaneously with one available number in pool
# Expected: exactly one group provisioned, one failed (not both assigned to same number)
# Note: the optimistic lock (.eq("status", "available") on update) handles this
```

### 7c. Lead Notification Test

```bash
# Simulate a qualified lead webhook call
POST /voice/lease-lead-webhook
Body: {
  "message": {
    "type": "tool-calls",
    "call": {
      "id": "test-call-id",
      "assistantId": "<active group's vapi_lease_assistant_id>"
    },
    "toolCallList": [{
      "type": "function",
      "function": {
        "name": "submit_lease_lead",
        "arguments": "{\"caller_name\": \"Test Lead\", \"qualification_status\": \"qualified\", ...}"
      }
    }]
  }
}

# Expected:
# - lease_leads row inserted with qualification_status='qualified'
# - notifications row inserted with type='lead', is_read=false
# - GET /notifications (authenticated) returns the new row
# - NotificationPanel bell badge shows unread count
```

### 7d. Notification Read/Clear Test

```bash
# GET /notifications — authenticated, should return the lead notification
# PATCH /notifications/{id}/read — mark as read
# GET /notifications again — is_read should be true
# POST /notifications/read-all — all notifications marked read
```

---

## 8. How to Add New Twilio Numbers to the Pool

### Step 1 — Buy the number in Twilio Console

1. Log into [console.twilio.com](https://console.twilio.com)
2. Go to **Phone Numbers → Manage → Buy a Number**
3. Filter by country and capabilities (Voice required)
4. Purchase the number — it will appear in E.164 format (e.g., `+15551234567`)
5. No webhook configuration needed in Twilio — VAPI handles all call routing

### Step 2 — Register in VAPI and add to pool

```bash
cd /path/to/Tenant_management_MVP
python backend/scripts/add_twilio_number_to_vapi.py +15551234567 --notes "US pool - May 2026"
```

The script will:
- Call VAPI's `CreatePhoneNumbersRequest_Twilio` to register the number
- Store the VAPI-assigned `phone_number_id` + E.164 number in `twilio_number_pool` with `status='available'`

### Step 3 — Verify

```bash
# Check the pool (Supabase dashboard or psql):
SELECT phone_number, vapi_phone_number_id, status, created_at
FROM twilio_number_pool
ORDER BY created_at DESC;
```

### Pool capacity rule of thumb

Keep at least **2 available** entries in the pool at all times so there's headroom if multiple managers sign up simultaneously. Add more before expected growth.

---

## 9. Implementation Checklist

Order matters — do migrations before code changes.

- [ ] **Migration 1** — create `notifications` table + RLS policy (Supabase dashboard SQL editor)
- [ ] **Migration 2** — create `twilio_number_pool` table + RLS policy
- [ ] **Config** — add `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` to `config.py` `Settings` class
- [ ] **Script** — create `backend/scripts/add_twilio_number_to_vapi.py`
- [ ] **Seed pool** — run the script for each Twilio number you want available (buy in Twilio console first)
- [ ] **Provisioning** — replace `vapi_provisioning.py` with the pool-based implementation
- [ ] **Webhook** — add notification insert in `voice.py` `lease_lead_webhook` after qualified lead save
- [ ] **Frontend** — add `lead` to `TYPE_COLORS` in `NotificationPanel.jsx`
- [ ] **Smoke test** — create a new property group → confirm `vapi_provisioning_status='active'` and a number assigned
- [ ] **Smoke test** — simulate qualified lead webhook → confirm bell badge appears in UI

---

## Files Changed Summary

| File | Change |
|---|---|
| `backend/scripts/add_twilio_number_to_vapi.py` | New — pool registration script |
| `backend/app/services/vapi_provisioning.py` | Replace VAPI-owned provisioning with pool-based |
| `backend/app/config.py` | Add `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` |
| `backend/app/routes/voice.py` | Add notification insert in `lease_lead_webhook` |
| `frontend/src/components/NotificationPanel.jsx` | Add `lead` color to `TYPE_COLORS` |
| Supabase DB | 2 new tables: `notifications` (if not exists), `twilio_number_pool` |
| `backend/app/routes/property_groups.py` | **No change** |
| `backend/app/services/vapi_agent_config.py` | **No change** |
