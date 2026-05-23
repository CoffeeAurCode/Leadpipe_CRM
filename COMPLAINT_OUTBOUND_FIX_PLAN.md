# Complaint Agent Outbound Call — Fix Plan

**Date:** 2026-05-23  
**Status:** Not implemented  
**Symptom:** Clicking "Call" with agent = Complaint in the outbound button fails or connects to the wrong/legacy assistant.

---

## Root Cause

`backend/app/routes/voice.py`, function `make_outbound_call` (line ~712):

```python
else:  # agent == "complaint"
    assistant_id    = settings.VAPI_ASSISTANT_ID      # ← WRONG — this is the legacy assistant
    phone_number_id = settings.VAPI_NUMBER_ID          # ← WRONG — this is +19734904520 (not a Twilio number you own)
```

The complaint outbound path uses two legacy env vars:
- `VAPI_ASSISTANT_ID` — the old assistant ID (`2cbc056b-c8b6-4406-97dd-4173604b249d`), not the current complaint agent.
- `VAPI_NUMBER_ID` — points to `+1 (973) 490-4520` which is a number that was removed from use.

The **correct** env vars already exist in `.env`:
- `VAPI_COMPLAINT_ASSISTANT_ID=9e507761-7bf7-451a-9413-8ae62ec0176f` — the live complaint assistant (Alex).
- `VAPI_COMPLAINT_NUMBER_ID=e8367bd3-12c6-4423-aa93-27ee8b264f48` — the live complaint number (`+14382314283`).

This bug was also confirmed by `backend/scripts/vapi_inspect.py` which explicitly noted:
```
complaint asst : VAPI_COMPLAINT_ASSISTANT_ID (NOT used for outbound)
```

---

## Fix — Code Change (1 file, 3 lines)

**File:** `backend/app/routes/voice.py`  
**Location:** Inside `make_outbound_call`, the `else` branch (complaint path), around line 712.

**Before:**
```python
else:
    assistant_id = settings.VAPI_ASSISTANT_ID
    phone_number_id = settings.VAPI_NUMBER_ID
    if not assistant_id:
        raise HTTPException(status_code=500, detail="VAPI_ASSISTANT_ID env var is not configured on the server")
```

**After:**
```python
else:
    assistant_id    = settings.VAPI_COMPLAINT_ASSISTANT_ID
    phone_number_id = settings.VAPI_COMPLAINT_NUMBER_ID or settings.VAPI_NUMBER_ID
    if not assistant_id:
        raise HTTPException(status_code=500, detail="VAPI_COMPLAINT_ASSISTANT_ID env var is not configured on the server")
```

The `or settings.VAPI_NUMBER_ID` fallback can be dropped once the old number is fully decommissioned.

---

## Fix — Guard Condition Update (same file)

The existing guard at line ~692 checks `VAPI_NUMBER_ID`:
```python
if not settings.VAPI_NUMBER_ID:
    raise HTTPException(status_code=500, detail="VAPI_NUMBER_ID env var is not configured on the server")
```

After the fix, the complaint path no longer requires `VAPI_NUMBER_ID`. Update the guard to check the relevant var per agent:

```python
# Move number-ID validation inside each branch (already done for lease above, do same for complaint)
# Remove the global VAPI_NUMBER_ID guard entirely, or change to:
if req.agent == "complaint" and not settings.VAPI_COMPLAINT_NUMBER_ID:
    raise HTTPException(status_code=500, detail="VAPI_COMPLAINT_NUMBER_ID env var is not configured on the server")
```

---

## Fix — .env (no change needed for the fix itself)

Both correct vars are already set in `.env`:
```
VAPI_COMPLAINT_ASSISTANT_ID=9e507761-7bf7-451a-9413-8ae62ec0176f
VAPI_COMPLAINT_NUMBER_ID=e8367bd3-12c6-4423-aa93-27ee8b264f48
```

No new env vars are needed on Render — they should already be present. Verify in Render dashboard under Environment → confirm both are set.

---

## Verification Steps After Fix

1. Deploy the updated `voice.py` to Render.
2. Open the app → Outbound Call button → select **Complaint** agent.
3. Enter a phone number and click Call.
4. Confirm in VAPI dashboard: call initiated with assistant `9e507761-7bf7-451a-9413-8ae62ec0176f` (not the legacy `2cbc056b`).
5. Confirm the call shows caller ID as `+14382314283`.
6. Alex (the complaint agent) should greet the callee and ask for the flat number.

---

## Cleanup After Fix

Once the fix is live and tested:
- Remove `VAPI_ASSISTANT_ID` from `.env` and Render environment (it is no longer used anywhere).
- Remove `VAPI_NUMBER_ID` from `.env` and Render environment (no longer used after this fix).
- Remove the `VAPI_ASSISTANT_ID` and `VAPI_NUMBER_ID` entries from `config.py`.
