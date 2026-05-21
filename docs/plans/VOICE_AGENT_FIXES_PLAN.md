# Voice Agent Fixes Plan

## Issues

### Issue 1 — UUID validation error in lease_lead_webhook
**Error:** `invalid input syntax for type uuid: "S-106"`  
**Cause:** The lease agent's LLM is hallucinating a flat number (e.g. "S-106") into the `listing_uuid` field when submitting the lead. The webhook passes this string directly to a Supabase `.eq("uuid", listing_uuid)` query, which expects a proper UUID and throws a Postgres error.  
**Impact:** The lead is NOT saved. The entire webhook crashes before the `db.table("lease_leads").insert(...)` call.

### Issue 2 — Agent does not end the call when conversation is complete
**Cause:** The VAPI lease assistant does not have `endCallFunctionEnabled` set to `true`. Without it, the assistant has no mechanism to hang up — it waits indefinitely for the caller to disconnect.  
**Impact:** Awkward dead air after the agent finishes its script. Caller must hang up manually.

---

## Fix 1 — Validate listing_uuid before querying Supabase

**File:** `backend/app/routes/voice.py`  
**Function:** `lease_lead_webhook` (line ~501)

**Change:** Before using `listing_uuid` in a Supabase UUID column query, validate it is a proper UUID. If not, discard it and let the fallback `assistant_id` lookup run.

```python
import re

UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

# In lease_lead_webhook, replace:
listing_uuid = lead_data.get("listing_uuid") or None

# With:
raw_uuid = lead_data.get("listing_uuid") or ""
listing_uuid = raw_uuid if UUID_RE.match(raw_uuid.strip()) else None
```

Also set `listing_uuid = None` in `lead_payload` when the value is invalid, so no junk gets stored.

---

## Fix 2 — Enable endCallFunctionEnabled on the VAPI lease assistant

VAPI provides a built-in `endCallFunctionEnabled` flag on assistants. When `true`, the model automatically gets access to an `endCall()` function it can invoke when it decides the conversation is complete (e.g. after saying goodbye).

**Option A — VAPI Dashboard (manual, no code)**  
1. Go to VAPI Dashboard → Assistants → select the lease assistant (`2dba3a50-6862-400c-861a-bfc0a45d4a95`)  
2. Under Settings → Advanced → toggle **End Call Function** ON  
3. Save

**Option B — One-time Python script (recommended for repeatability)**  
Create `backend/scripts/enable_end_call.py`:

```python
from vapi import Vapi
import os
from dotenv import load_dotenv

load_dotenv()

client = Vapi(token=os.getenv("PRIVATE_VAPI_API"))

LEASE_ASSISTANT_ID = os.getenv("VAPI_SHARED_LEASE_ASSISTANT_ID")

result = client.assistants.update(
    LEASE_ASSISTANT_ID,
    end_call_function_enabled=True,
)
print(f"Updated assistant {result.id}: endCallFunctionEnabled={result.end_call_function_enabled}")
```

Run once: `python backend/scripts/enable_end_call.py`

**Note:** The complaint agent (`VAPI_ASSISTANT_ID` / `VAPI_COMPLAINT_ASSISTANT_ID`) may have the same issue. Run the same update for both assistant IDs if needed.

---

## Implementation Steps

- [ ] 1. Add UUID_RE regex and validation guard in `lease_lead_webhook` (`voice.py`)
- [ ] 2. Ensure `listing_uuid` stored in `lead_payload` is also set to `None` when invalid
- [ ] 3. Apply Fix 2 Option A (dashboard) OR create and run the script (Option B)
- [ ] 4. Test: trigger a lease call from VAPI dashboard, verify lead saves correctly and call ends automatically

---

## Files Changed

| File | Change |
|---|---|
| `backend/app/routes/voice.py` | UUID validation guard in `lease_lead_webhook` |
| `backend/scripts/enable_end_call.py` | (new, optional) one-time script to patch VAPI assistant |
