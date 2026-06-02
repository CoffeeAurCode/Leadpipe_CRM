# Diagnosis: Voice Complaint Creation Failing with 401

**Date:** 2026-06-02  
**Observed in:** Manual test call, call_id `019e8923-e768-7000-b8ed-cd3f01ace8c4`  
**Symptom:** Complaint never created. CallLog ID 57 left with `Status: failed`.

---

## What the Logs Show

```
[COMPLAINT CREATION]
INFO: 74.220.49.249:0 - "POST /complaints HTTP/1.1" 401 Unauthorized
  [X] API returned 401
[AUTOMATION]
  Complaint Created: No (API 401)
  Triggering Notification: No
[FINAL STATE]
  CallLog: 57
  Complaint: None
  Status: failed
```

The voice webhook processed the call correctly up to this point:
- Flat `C301` was found
- Voice calls feature was enabled (fixed in this session)
- Complaint data was valid and complete
- Call log was created successfully (ID 57)

Everything worked — then complaint creation failed with 401.

---

## Root Cause

### The HTTP Round-Trip Design

`voice.py` (lines 337–343) creates complaints by making an **outbound HTTP POST** back to its own `/complaints` endpoint:

```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://tenant-management-mvp.onrender.com/complaints",
        json=complaint_payload,
        timeout=10.0
    )
```

No `Authorization` header is attached to this request.

### Why That Causes 401

`complaints.py` (lines 19–20) guards `POST /complaints` with two FastAPI dependencies:

```python
user: dict = Depends(require_active_subscription),
db: Client = Depends(get_authenticated_db)
```

Both dependencies extract and validate a **Supabase JWT** from the `Authorization: Bearer <token>` header. When the header is absent, FastAPI rejects the request immediately with `401 Unauthorized` — before any route logic runs.

The voice webhook has **no user JWT to provide**. It is a server-side VAPI callback, not a browser session. There is no logged-in user in this flow, so a user JWT cannot be obtained.

### Why This Was Not Caught Earlier

The voice calls feature was previously disabled for all units (`voice_calls` defaulted to `False`). Every call hit the `[BLOCKED] Voice calls feature is disabled` branch and returned early before reaching the HTTP call. The 401 was never triggered because the code path was unreachable.

After enabling voice calls for all units (done in this session), the code path became reachable and the latent 401 bug surfaced immediately.

---

## Contributing Factor: The TODO Comment

The code itself acknowledged this design was flawed:

```python
# TODO: Future improvement - call service function directly instead of HTTP
# This HTTP approach will break with gunicorn/multiple workers/Docker
# For Day-3 MVP, this is acceptable
```

The 401 is one of several reasons this approach fails. The others (multi-worker breakage, unnecessary network latency on a call that is already time-sensitive) remain even if the 401 were patched.

---

## Impact

| What works | What breaks |
|---|---|
| Call transcription | Complaint row never inserted |
| Flat + phone verification | Appointment never created |
| CallLog creation (ID recorded) | Manager notification never sent |
| Feature flag check | CallLog left with `status: failed` |

The user hears the AI confirm the complaint was submitted, but nothing is recorded.

---

## Possible Fixes

### Fix 1 — Direct DB Insert (Recommended)

Remove the HTTP call entirely. The webhook handler already holds a `db` service client (`get_service_db`). Use it to replicate what `create_complaint` does:

```python
# Resolve flat_uuid from flat_number
flat_uuid = flat_response.data[0]['uuid']

# Auto-assign tenant
tenant_resp = db.table("tenants").select("uuid").eq("flat_uuid", flat_uuid).execute()
tenant_uuid = tenant_resp.data[0]['uuid'] if tenant_resp.data else None

complaint_row = {
    "flat_number": flat_no.strip().upper(),
    "flat_uuid": flat_uuid,
    "tenant_uuid": tenant_uuid,
    "category": complaint_data.get("category"),
    "priority": "medium",
    "description": description[:1000],
    "status": "pending",
    "source": "voice",
}
result = db.table("complaints").insert(complaint_row).execute()
```

Appointments and notifications follow using the same `db` client.

**Pros:** No network hop, no auth problem, works under gunicorn/Docker, eliminates the TODO.  
**Cons:** Duplicates the logic in `create_complaint` — if the complaints schema changes, both places need updating.

---

### Fix 2 — Pass Supabase Service Key as Bearer Token

Keep the HTTP call but attach the service role key as the Authorization header:

```python
headers = {"Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"}
async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://tenant-management-mvp.onrender.com/complaints",
        json=complaint_payload,
        headers=headers,
        timeout=10.0
    )
```

`get_authenticated_db` would accept a service key JWT and bypass RLS.

**Pros:** Minimal code change, reuses existing `create_complaint` logic.  
**Cons:** Does not fix the multi-worker reliability problem. The service key is a high-privilege credential being sent over the network on every voice call. Still a network hop with latency on a time-sensitive webhook path.

---

### Fix 3 — Add an Internal Unauthenticated Complaints Endpoint

Add a second route, e.g. `POST /internal/complaints`, that uses `get_service_db` and no subscription check, exclusively for server-side callers:

```python
@router.post("/internal/complaints", include_in_schema=False)
async def create_complaint_internal(
    complaint_data: ComplaintCreate,
    db: Client = Depends(get_service_db),
):
    ...
```

Protect it with a shared secret header instead of a user JWT.

**Pros:** Clean separation between user-facing and internal routes.  
**Cons:** Most work. Adds a route that must be kept in sync with the user-facing one. Still a network hop.

---

## Recommendation

**Fix 1** (direct DB insert). It eliminates the network hop, the auth problem, and the multi-worker deployment risk in one change. The logic duplication is acceptable since complaint creation from voice is a distinct flow with different field sourcing (no `tenant_id`, source always `"voice"`, description comes from transcript).
