# How a Pool Number Gets Assigned to a New User

## The Core Question

The complaint agent number and shared lease number live in `.env` as `VAPI_COMPLAINT_NUMBER_ID` and `VAPI_SHARED_LEASE_NUMBER_ID`. So why don't the pool numbers live there too?

**Because those env var numbers are static — the same for every user, forever. Pool numbers are dynamic — one unique number per property group, growing as new managers sign up.**

If pool numbers were in `.env`, you'd need to restart the server every time you added a number, pre-assign numbers to specific managers before they sign up, and hard-code which manager gets which number. None of that is practical. Instead, pool numbers live in the database and are claimed on demand.

---

## Two Types of Numbers in This System

| Type | Where stored | How many | Who uses it | Example |
|---|---|---|---|---|
| **Static / shared** | `.env` + server memory | 3 total, fixed | Every user shares them | Complaint agent line, shared lease agent |
| **Pool / per-group** | `twilio_number_pool` table | One per property group, grows over time | One specific manager's property group | +12494028641 |

The static numbers never change. The pool numbers are pre-registered Twilio numbers sitting in the database waiting to be claimed.

---

## Full Flow: Sign-Up to Number Assignment

### Step 1 — User signs up (Google OAuth)

The user clicks "Sign in with Google" on the login page.

**Code:** `frontend/src/context/AuthContext.jsx`

```js
supabase.auth.onAuthStateChange((event, session) => {
    if (session?.user && !profileChecked.current) {
        profileChecked.current = true;
        ensureManagerProfile(session.user);  // ← runs on first sign-in
    }
})
```

`ensureManagerProfile()` checks if a `manager_profiles` row exists for this Supabase user ID. If not, it creates one:

```js
await supabase.from('manager_profiles').insert({
    user_id: user.id,
    name: user.user_metadata?.full_name || ...,
    phone: ...,
});
```

At this point: the user exists in `auth.users` (Supabase managed) and has a row in `manager_profiles`. They have **no property groups yet**, so **no phone number is assigned yet**.

---

### Step 2 — User creates their first property group

The user clicks "Add Property" in the UI, fills in the name and details, and submits.

**Frontend:** `AddPropertyGroupModal.jsx` → calls `POST /property-groups`

**Backend:** `backend/app/routes/property_groups.py` — `create_property_group()`

```python
@router.post("", status_code=201)
async def create_property_group(
    request: PropertyGroupCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    payload = request.model_dump(exclude_none=True)
    payload["vapi_provisioning_status"] = "pending"   # ← starts as pending
    payload["manager_id"] = user["sub"]

    response = db.table("properties_list").insert(payload).execute()
    g = response.data[0]

    # Kick off provisioning in the background — does NOT block the HTTP response
    background_tasks.add_task(provision_vapi_for_property_group, g["id"], g["name"], db)

    return { ...g, "building_count": 0 }   # ← returns immediately to frontend
```

Two things happen here:

1. A row is inserted into `properties_list` with `vapi_provisioning_status = "pending"`. The frontend gets this back immediately (HTTP 201) — the user can see their new property group right away.
2. `provision_vapi_for_property_group()` is registered as a **BackgroundTask** — FastAPI runs it after the response is sent, without making the user wait.

---

### Step 3 — BackgroundTask: claim a number from the pool

**Code:** `backend/app/services/vapi_provisioning.py`

This is where the pool number actually gets assigned. It runs asynchronously after the HTTP response.

#### 3a. Connect to the database with service role

```python
svc_db = get_service_db()   # bypasses RLS
```

The `db` argument passed from the route is RLS-enforced (the manager can only see their own rows). The `twilio_number_pool` table is `service_role` only — the manager's RLS token cannot read or write it. So the function opens a second connection using the service key.

#### 3b. Pick the oldest available number

```python
pool_resp = (
    svc_db.table("twilio_number_pool")
    .select("id, phone_number, vapi_phone_number_id")
    .eq("status", "available")
    .order("created_at")       # oldest first — FIFO
    .limit(1)
    .execute()
)
```

If two managers sign up at exactly the same time, the `.eq("status", "available")` on the update below acts as an optimistic lock — only one task will successfully claim any given row.

#### 3c. Mark it as assigned immediately

```python
svc_db.table("twilio_number_pool").update({
    "status": "assigned",
    "assigned_property_group_id": property_group_id,
    "assigned_at": datetime.now(timezone.utc).isoformat(),
}).eq("id", pool_id).eq("status", "available").execute()
```

The `.eq("status", "available")` on the update is critical. If two background tasks tried to claim the same row simultaneously, only one update would match (because after the first update, `status` is no longer `"available"`). The second task would get 0 rows updated and proceed to fail or pick the next available number.

#### 3d. Create a per-group VAPI assistant

```python
lease_cfg = build_lease_config(BACKEND_URL, property_group_id, pg_name)
lease = client.assistants.create(**lease_cfg)
```

`build_lease_config()` in `vapi_agent_config.py` builds an assistant config that **hard-codes this specific `property_group_id` into every tool URL**:

```python
# Inside build_lease_config():
pg_qs = f"&property_group_id={property_group_id}"
"url": f"{backend_url}/leasing/find-listing?query={{{{query}}}}{pg_qs}",
"url": f"{backend_url}/leasing/search?bedrooms=...{pg_qs}",
```

This means the assistant can only search listings that belong to this property group. A caller can never be shown listings from another manager's portfolio.

#### 3e. Link the assistant to the Twilio phone number in VAPI

```python
client.phone_numbers.update(
    vapi_phone_number_id,         # the VAPI ID stored when the number was added to the pool
    request=UpdatePhoneNumberDto(assistant_id=lease.id),
)
```

The `vapi_phone_number_id` was stored in `twilio_number_pool` when you ran `add_twilio_number_to_vapi.py`. That script registered the Twilio number with VAPI and got back a VAPI-internal ID like `pn_abc123`. This update call tells VAPI: "when someone calls this number, use this assistant."

Before this step: the number was registered in VAPI but had no assistant — calls to it would have gone unanswered.
After this step: the number is fully live and routes to the new per-group lease assistant.

#### 3f. Write the IDs back to the property group

```python
db.table("properties_list").update({
    "vapi_lease_assistant_id":  lease.id,          # VAPI assistant ID
    "vapi_phone_number_id":     vapi_phone_number_id,  # VAPI phone number object ID
    "vapi_phone_number":        phone_number,       # E.164 e.g. +12494028641
    "vapi_provisioning_status": "active",
}).eq("id", property_group_id).execute()
```

The manager's `properties_list` row now has the phone number and both VAPI IDs. `vapi_provisioning_status` changes from `"pending"` to `"active"`.

---

### Step 4 — Frontend displays the number

`GET /property-groups` returns all property groups including `vapi_phone_number` and `vapi_provisioning_status`. The frontend (via `PropertyGroupCard`) can show the manager their lease line number directly.

The manager did nothing special to get this number — it was claimed automatically when they created their property group.

---

## State of the Database After Assignment

### `twilio_number_pool` row (before → after)

| Column | Before | After |
|---|---|---|
| `status` | `available` | `assigned` |
| `assigned_property_group_id` | `null` | `<pg uuid>` |
| `assigned_at` | `null` | `2026-05-23T...` |

### `properties_list` row (before → after)

| Column | After `POST /property-groups` | After background task |
|---|---|---|
| `vapi_provisioning_status` | `pending` | `active` |
| `vapi_lease_assistant_id` | `null` | `asst_abc123` |
| `vapi_phone_number_id` | `null` | `pn_abc123` |
| `vapi_phone_number` | `null` | `+12494028641` |

---

## How an Inbound Call Reaches the Right Manager

When a prospect calls `+12494028641`:

1. Twilio receives the call and forwards it to VAPI (because the number is registered in VAPI via `CreatePhoneNumbersRequest_Twilio`)
2. VAPI looks at its phone number object (`pn_abc123`) and sees `assistant_id = asst_abc123`
3. VAPI starts a call session with that specific assistant
4. The assistant's tool URLs already have `&property_group_id=<pg_uuid>` baked in — every listing search is automatically scoped to the right manager
5. When the call ends, `submit_lease_lead` fires to `/voice/lease-lead-webhook`
6. The webhook resolves the manager via `call.phoneNumberId → properties_list.vapi_phone_number_id` (path 3 in the resolution chain)

No env var lookup happens anywhere in this inbound call chain. The entire routing is driven by what's stored in `properties_list`.

---

## What Happens If the Pool Is Empty

If there are no `available` rows in `twilio_number_pool` when a property group is created:

```
[TWILIO PROVISION] Failed for group <uuid>:
No available numbers in twilio_number_pool.
Add numbers via: python backend/scripts/add_twilio_number_to_vapi.py <E.164>
```

The property group is created successfully and the manager can use it. Only the VAPI lease agent provisioning fails. The `properties_list` row gets `vapi_provisioning_status = "failed"`.

To recover: add a number to the pool, then use the retry endpoint:

```
POST /property-groups/<id>/provision-voice
```

This resets the status to `"pending"` and kicks off `provision_vapi_for_property_group()` again as a background task.

---

## Why the Pool Doesn't Use Env Vars — Summary

| Reason | Explanation |
|---|---|
| **Numbers grow over time** | Every new manager needs a unique number. You can't know in advance how many you'll need. |
| **No restart required** | Adding a number to the pool (run the script, insert a DB row) takes effect immediately. No server restart, no redeployment. |
| **Numbers are interchangeable** | The system picks the oldest available number — it doesn't matter which specific number a manager gets. |
| **Routing is stored in VAPI + DB** | Once assigned, VAPI routes calls using the `assistant_id` on the phone number object. The backend routes webhook calls using `vapi_phone_number_id` on `properties_list`. Neither of these requires an env var lookup. |
| **Env vars are for fixed shared resources** | `VAPI_COMPLAINT_NUMBER_ID`, `VAPI_SHARED_LEASE_NUMBER_ID`, and `VAPI_NUMBER_ID` are global — used across all managers, never change. That's exactly what env vars are for. |
