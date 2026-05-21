# Outbound Call Failure — Diagnosis & Fix

## Root Cause

**VAPI rejects the call with HTTP 400:**
```
"Couldn't start call. Free Vapi numbers do not support international calls."
```

The `VAPI_NUMBER_ID` (and/or `VAPI_SHARED_LEASE_NUMBER_ID`) points to a **free VAPI-provisioned number**. Free numbers only support US/Canada destinations. Your tenant phone numbers are Indian (+91), which VAPI classifies as international — so every call attempt is rejected at source.

The rejection comes as a `vapi.core.api_error.ApiError` at `voice.py:605`. Because this exception is **not caught**, FastAPI propagates it as an unhandled 500. The frontend sees a 500 body it can't parse → displays "Failed to fetch".

---

## Two Separate Problems

| # | Problem | Impact |
|---|---|---|
| 1 | Unhandled `ApiError` in `make_outbound_call` | 500 instead of a descriptive error; "Failed to fetch" on frontend |
| 2 | Free VAPI number can't call international numbers | Call never dials regardless of error handling |

---

## Fix 1 — Catch the ApiError (code change, immediate)

In `backend/app/routes/voice.py`, wrap the `client.calls.create(...)` call to catch VAPI errors and surface them as a proper HTTP response:

```python
from vapi.core.api_error import ApiError

try:
    call = client.calls.create(
        assistant_id=assistant_id,
        phone_number_id=phone_number_id,
        customer=CreateCustomerDto(number=req.customer_number),
        assistant_overrides=overrides,
    )
except ApiError as e:
    raise HTTPException(
        status_code=e.status_code or 502,
        detail=e.body.get("message", str(e)) if isinstance(e.body, dict) else str(e),
    )
```

This makes the frontend receive a 400 with the real message instead of a 500, so the UI can show "Free Vapi numbers do not support international calls" rather than "Failed to fetch".

---

## Fix 2 — Use a number that supports international calls (VAPI account change)

You have three options, in order of ease:

### Option A — Upgrade VAPI plan
Paid VAPI plans allow international outbound calls. After upgrading, your existing `VAPI_NUMBER_ID` will work for Indian numbers.

### Option B — Import a Twilio number into VAPI (recommended for production)
1. Buy an Indian or international-capable number from Twilio.
2. In the VAPI dashboard → **Phone Numbers → Import** → connect your Twilio account.
3. Update `VAPI_NUMBER_ID` (and `VAPI_SHARED_LEASE_NUMBER_ID`) in your Render env vars to the imported number's ID.

This gives you full control over the originating number and supports any destination.

### Option C — Use a Twilio number with a `+1` trunk for outbound
If cost is a concern, keep VAPI for inbound and trigger outbound calls directly via Twilio's API (bypassing VAPI's number restriction), then connect them to a VAPI session via SIP. This is more complex and only worth it at scale.

---

## What to Do Right Now

1. Apply **Fix 1** to stop the 500 and show users a real error message.
2. Decide on **Fix 2** based on your VAPI plan / budget — Option B (Twilio import) is the cleanest path for an India-based deployment.
3. After importing a number, test with one call before updating both number IDs.

---

## Verification Checklist

- [ ] `client.calls.create` is wrapped in `try/except ApiError`
- [ ] Frontend shows a human-readable error (not "Failed to fetch")
- [ ] `VAPI_NUMBER_ID` updated to an international-capable number
- [ ] Test call to a `+91` number succeeds end-to-end
