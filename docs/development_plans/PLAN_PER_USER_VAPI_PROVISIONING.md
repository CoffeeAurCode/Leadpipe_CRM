# Plan: Per-User VAPI Provisioning (One Number Per Manager)

**Date:** 2026-05-23  
**Goal:** Redesign VAPI provisioning from per-property-group to per-manager. Every user gets exactly ONE Twilio number + ONE VAPI lease assistant. That assistant handles leads for ALL of the user's property groups. Adding more property groups to an account never triggers new provisioning.

---

## Architecture

### Current (per-group — being replaced)
```
User creates Property Group A  →  provision assistant A, claim number X
User creates Property Group B  →  provision assistant B, claim number Y
User creates Property Group C  →  provision assistant C, claim number Z
→ 3 groups = 3 numbers = 3 assistants (expensive, doesn't scale)
```

### Target (per-user)
```
User creates Property Group A (first group)  →  provision assistant, claim number X
User creates Property Group B (second group) →  manager already has a number, skip
User creates Property Group C (third group)  →  manager already has a number, skip
→ 10 groups = 1 number = 1 assistant (correct)

Inbound call to number X:
  → VAPI routes to that manager's assistant
  → Agent searches listings across ALL the manager's groups
  → Lead is captured with listing_uuid → resolves to the right property_group_id automatically
```

---

## What Changes

| Layer | Change |
|---|---|
| Supabase DB | New `manager_vapi_config` table (one row per manager); modify `twilio_number_pool` to track `assigned_manager_id` |
| `vapi_provisioning.py` | Replace `provision_vapi_for_property_group` with `provision_vapi_for_manager` |
| `vapi_agent_config.py` | `build_lease_config` takes `manager_id` instead of `property_group_id`/`pg_name`; tool URLs use `?manager_id=` |
| `property_groups.py` | Provisioning trigger: only fires when manager has NO existing `manager_vapi_config` row |
| `voice.py` (webhook) | Paths 2 & 3 resolve `manager_id` via `manager_vapi_config`, not `properties_list` |
| `voice.py` (outbound) | Look up active config from `manager_vapi_config`, not `properties_list` |
| Leasing routes | `/leasing/find-listing` and `/leasing/search` accept `manager_id` query param |
| `property_groups.py` | Remove `POST /{property_id}/provision-voice`; add `POST /users/me/provision-voice` |
| `LeasingTab.jsx` | Provisioning status comes from `manager_vapi_config`, not per-group fields |
| `apiService.js` | New `getUserVapiConfig()` and `retryUserProvisioning()` functions |

---

## Phase 1 — Supabase DB Migration

### Step 1.1 — Create `manager_vapi_config` table

```sql
CREATE TABLE manager_vapi_config (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id              UUID NOT NULL UNIQUE,
    vapi_lease_assistant_id TEXT,
    vapi_phone_number_id    TEXT,
    vapi_phone_number       TEXT,
    vapi_provisioning_status TEXT NOT NULL DEFAULT 'pending',
    pool_row_id             UUID,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: managers can only read their own row
ALTER TABLE manager_vapi_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager reads own vapi config"
ON manager_vapi_config FOR SELECT
USING (manager_id = auth.uid());
```

### Step 1.2 — Add `assigned_manager_id` to `twilio_number_pool`

```sql
ALTER TABLE twilio_number_pool
    ADD COLUMN assigned_manager_id UUID,
    DROP COLUMN IF EXISTS assigned_property_group_id;
```

> If `assigned_property_group_id` has existing data you want to preserve for reference, rename instead:
> `ALTER TABLE twilio_number_pool RENAME COLUMN assigned_property_group_id TO _legacy_assigned_property_group_id;`

### Step 1.3 — Migrate `leadpipecrm@gmail.com` existing data

```sql
-- Check if they have any per-group active data to migrate
SELECT id, name, vapi_lease_assistant_id, vapi_phone_number_id, vapi_phone_number, vapi_provisioning_status
FROM properties_list
WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3'
  AND vapi_provisioning_status = 'active';
```

If any rows come back, migrate the first one to `manager_vapi_config`:

```sql
-- Insert the manager-level config using data from the first active group
INSERT INTO manager_vapi_config (manager_id, vapi_lease_assistant_id, vapi_phone_number_id, vapi_phone_number, vapi_provisioning_status)
SELECT
    manager_id,
    vapi_lease_assistant_id,
    vapi_phone_number_id,
    vapi_phone_number,
    'active'
FROM properties_list
WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3'
  AND vapi_provisioning_status = 'active'
LIMIT 1;
```

If no active rows (all `not_applicable` — our current state), insert a pending row so provisioning can be triggered:

```sql
-- No active data to migrate; insert pending so provision-voice can run
INSERT INTO manager_vapi_config (manager_id, vapi_provisioning_status)
VALUES ('28c43c77-8c9c-496f-8d1e-39ffa9d619e3', 'pending')
ON CONFLICT (manager_id) DO NOTHING;
```

### Step 1.4 — Null out per-group VAPI columns (they're now irrelevant)

```sql
UPDATE properties_list
SET
    vapi_lease_assistant_id  = NULL,
    vapi_phone_number_id     = NULL,
    vapi_phone_number        = NULL,
    vapi_provisioning_status = 'not_applicable'
WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3';
```

> Leave the columns in `properties_list` for now (removing them is a separate migration). They will simply be unused going forward.

### Step 1.5 — Update pool row for `+14313415768`

```sql
UPDATE twilio_number_pool
SET
    assigned_manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3',
    status = 'available'
WHERE phone_number = '+14313415768';
```

(Set to `available` now; provisioning will flip it to `assigned` when it runs.)

---

## Phase 2 — Backend Code Changes

### 2.1 `backend/app/services/vapi_provisioning.py` — Rewrite for per-manager

Replace the entire file with a `provision_vapi_for_manager` function:

```python
import os
from datetime import datetime, timezone
from supabase import Client
from app.services.vapi_agent_config import build_lease_config

BACKEND_URL = os.environ.get("BACKEND_URL", "https://tenant-management-mvp.onrender.com")


def provision_vapi_for_manager(manager_id: str, db: Client) -> None:
    """
    Provision ONE VAPI lease assistant for this manager account.
    Claims one number from twilio_number_pool, creates the assistant,
    links them, and writes to manager_vapi_config.

    Uses service DB for pool + manager_vapi_config writes (RLS blocks user-scoped db).
    Idempotent: if manager already has status='active', exits immediately.
    """
    from vapi import Vapi
    from app.db.session import get_service_db
    from app.config import settings

    svc_db = get_service_db()
    client = Vapi(token=settings.PRIVATE_VAPI_API)

    try:
        # Guard: already provisioned?
        existing = (
            svc_db.table("manager_vapi_config")
            .select("id, vapi_provisioning_status")
            .eq("manager_id", manager_id)
            .limit(1)
            .execute()
        )
        if existing.data and existing.data[0].get("vapi_provisioning_status") == "active":
            print(f"[VAPI PROVISION] Manager {manager_id} already active, skipping")
            return

        # 1. Claim first available pool number (FIFO)
        pool_resp = (
            svc_db.table("twilio_number_pool")
            .select("id, phone_number, vapi_phone_number_id")
            .eq("status", "available")
            .order("created_at")
            .limit(1)
            .execute()
        )
        if not pool_resp.data:
            print(f"[VAPI PROVISION] Pool empty — marking manager {manager_id} as failed")
            svc_db.table("manager_vapi_config").upsert({
                "manager_id": manager_id,
                "vapi_provisioning_status": "failed",
            }, on_conflict="manager_id").execute()
            return

        pool_row = pool_resp.data[0]
        pool_id = pool_row["id"]
        vapi_phone_number_id = pool_row["vapi_phone_number_id"]
        phone_number = pool_row["phone_number"]

        # 2. Optimistic lock — mark assigned before creating assistant
        svc_db.table("twilio_number_pool").update({
            "status": "assigned",
            "assigned_manager_id": manager_id,
            "assigned_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", pool_id).eq("status", "available").execute()

        # 3. Create the per-manager VAPI lease assistant
        lease_cfg = build_lease_config(BACKEND_URL, manager_id)
        lease = client.assistants.create(**lease_cfg)

        # 4. Link assistant to the Twilio number in VAPI
        try:
            from vapi.types import UpdatePhoneNumberDto
            client.phone_numbers.update(
                vapi_phone_number_id,
                request=UpdatePhoneNumberDto(assistant_id=lease.id),
            )
        except ImportError:
            client.phone_numbers.update(vapi_phone_number_id, assistant_id=lease.id)

        # 5. Write to manager_vapi_config
        svc_db.table("manager_vapi_config").upsert({
            "manager_id": manager_id,
            "vapi_lease_assistant_id": lease.id,
            "vapi_phone_number_id": vapi_phone_number_id,
            "vapi_phone_number": phone_number,
            "vapi_provisioning_status": "active",
            "pool_row_id": pool_id,
        }, on_conflict="manager_id").execute()

        print(
            f"[VAPI PROVISION] Success for manager {manager_id}: "
            f"assistant={lease.id} phone={phone_number}"
        )

    except Exception as e:
        print(f"[VAPI PROVISION] Failed for manager {manager_id}: {e}")
        svc_db.table("manager_vapi_config").upsert({
            "manager_id": manager_id,
            "vapi_provisioning_status": "failed",
        }, on_conflict="manager_id").execute()
        raise
```

---

### 2.2 `backend/app/services/vapi_agent_config.py` — Build config for manager (not group)

**Change `_build_lease_tools`:**

```python
def _build_lease_tools(backend_url: str, manager_id: str) -> list:
    mgr_qs = f"&manager_id={manager_id}"
    # Replace all occurrences of pg_qs / property_group_id= with mgr_qs / manager_id=
    # URLs become:
    #   find_listing?query=...&manager_id=<UUID>
    #   search?bedrooms=...&budget_max=...&manager_id=<UUID>
    #   submit_lease_lead uses POST body — no URL change needed
```

**Change `_LEASE_CONTEXT_BLOCK`:**

```python
_LEASE_CONTEXT_BLOCK = """\

[Context — Do Not Expose]
Manager ID: {manager_id}
All searches are scoped to all properties managed by this account.
"""
```

**Change `build_lease_config` signature:**

```python
def build_lease_config(backend_url: str, manager_id: str) -> dict:
    tools = _build_lease_tools(backend_url, manager_id)
    context_block = _LEASE_CONTEXT_BLOCK.format(manager_id=manager_id)
    system_prompt = _LEASE_SYSTEM_PROMPT_BASE + context_block
    return _lease_assistant_shell(
        name=f"Lease Agent [{manager_id[:8]}]",
        system_prompt=system_prompt,
        tools=tools,
    )
```

Remove the `pg_name` parameter entirely. The agent no longer presents a property group name — it handles all listings for the account.

---

### 2.3 `backend/app/routes/property_groups.py` — Trigger provisioning only on first group

**In `create_property_group`**, replace the unconditional provisioning trigger:

```python
# Before (triggers every time):
background_tasks.add_task(provision_vapi_for_property_group, pg_id, pg_name, db)

# After (only triggers if this manager has no existing config):
from app.db.session import get_service_db
svc_db = get_service_db()
existing_config = (
    svc_db.table("manager_vapi_config")
    .select("id, vapi_provisioning_status")
    .eq("manager_id", user["sub"])
    .limit(1)
    .execute()
)
if not existing_config.data:
    # First property group for this manager — provision their number
    svc_db.table("manager_vapi_config").insert({
        "manager_id": user["sub"],
        "vapi_provisioning_status": "pending",
    }).execute()
    from app.services.vapi_provisioning import provision_vapi_for_manager
    background_tasks.add_task(provision_vapi_for_manager, user["sub"], db)
# else: manager already has (or is getting) a number — no action needed
```

**Remove** `POST /{property_id}/provision-voice` route entirely.

**Add** a new user-level retry endpoint:

```python
@router.post("/users/me/provision-voice", status_code=202)
async def retry_user_voice_provisioning(
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Retry VAPI lease provisioning for this manager account."""
    from app.db.session import get_service_db
    from app.services.vapi_provisioning import provision_vapi_for_manager

    svc_db = get_service_db()
    svc_db.table("manager_vapi_config").upsert({
        "manager_id": user["sub"],
        "vapi_provisioning_status": "pending",
    }, on_conflict="manager_id").execute()

    background_tasks.add_task(provision_vapi_for_manager, user["sub"], db)
    return {"status": "provisioning_started"}
```

---

### 2.4 `backend/app/routes/voice.py` — Webhook: resolve manager via `manager_vapi_config`

**Replace Paths 2 & 3** of the property_group resolution block:

```python
# Path 2: assistant_id → manager_vapi_config (per-user assistant)
if not property_group_id and assistant_id:
    mvc_row = (
        db.table("manager_vapi_config")
        .select("manager_id")
        .eq("vapi_lease_assistant_id", assistant_id)
        .limit(1)
        .execute()
    )
    if mvc_row.data:
        manager_id = mvc_row.data[0].get("manager_id")
        resolution_path = "assistant_id→manager_vapi_config"
        # property_group_id remains None — will be resolved via listing_uuid (Path 1) if present

# Path 3: phoneNumberId → manager_vapi_config (per-user number)
if not manager_id and phone_number_id:
    mvc_row = (
        db.table("manager_vapi_config")
        .select("manager_id")
        .eq("vapi_phone_number_id", phone_number_id)
        .limit(1)
        .execute()
    )
    if mvc_row.data:
        manager_id = mvc_row.data[0].get("manager_id")
        resolution_path = "phone_number_id→manager_vapi_config"
```

**After resolution**, `property_group_id` is resolved from `listing_uuid` (Path 1) as before. If no listing_uuid was provided, the lead is stored with `manager_id` only and `property_group_id = NULL`.

**Update outbound call** (`make_outbound_call`) to look up from `manager_vapi_config`:

```python
# Before (looked at properties_list):
pg_row = svc_db.table("properties_list")
    .select("vapi_lease_assistant_id, vapi_phone_number_id")
    .eq("manager_id", user["sub"])
    .eq("vapi_provisioning_status", "active")
    .limit(1).execute()

# After:
mvc_row = svc_db.table("manager_vapi_config")
    .select("vapi_lease_assistant_id, vapi_phone_number_id")
    .eq("manager_id", user["sub"])
    .eq("vapi_provisioning_status", "active")
    .limit(1).execute()
if mvc_row.data and mvc_row.data[0].get("vapi_lease_assistant_id"):
    assistant_id = mvc_row.data[0]["vapi_lease_assistant_id"]
    phone_number_id = mvc_row.data[0]["vapi_phone_number_id"]
else:
    raise HTTPException(
        status_code=500,
        detail="No active lease agent found for this account. Check VAPI provisioning status."
    )
```

---

### 2.5 `backend/app/routes/leasing.py` (or wherever `/leasing/find-listing` and `/leasing/search` live) — Accept `manager_id`

Add `manager_id: str | None = None` query param to both endpoints. When `manager_id` is provided, filter across all property groups owned by that manager:

```python
# find-listing
@router.get("/find-listing")
async def find_listing(
    query: str,
    property_group_id: str | None = None,
    manager_id: str | None = None,
    db: Client = Depends(get_service_db),  # service DB — called by VAPI, no user token
):
    q = db.table("lease_listings").select("...")
    if property_group_id:
        q = q.eq("property_group_id", property_group_id)
    elif manager_id:
        # Get all group IDs for this manager
        groups = db.table("properties_list").select("id").eq("manager_id", manager_id).execute()
        group_ids = [g["id"] for g in groups.data]
        q = q.in_("property_group_id", group_ids)
    # ... rest of search logic
```

Apply the same pattern to `/leasing/search`.

---

## Phase 3 — Frontend Changes

### 3.1 `frontend/src/services/apiService.js` — New functions

```js
/** Fetch the VAPI provisioning status for the current manager. */
export async function getUserVapiConfig() {
    const response = await authFetch(`${API_BASE_URL}/property-groups/users/me/vapi-config`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

/** Retry VAPI provisioning for the current manager account. */
export async function retryUserProvisioning() {
    const response = await authFetch(`${API_BASE_URL}/property-groups/users/me/provision-voice`, {
        method: 'POST',
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
}
```

### 3.2 Add `GET /users/me/vapi-config` backend endpoint

```python
@router.get("/users/me/vapi-config")
async def get_user_vapi_config(
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    from app.db.session import get_service_db
    svc_db = get_service_db()
    row = (
        svc_db.table("manager_vapi_config")
        .select("vapi_provisioning_status, vapi_phone_number")
        .eq("manager_id", user["sub"])
        .limit(1)
        .execute()
    )
    if not row.data:
        return {"vapi_provisioning_status": "not_set_up", "vapi_phone_number": None}
    return row.data[0]
```

### 3.3 `frontend/src/components/LeasingTab.jsx` — Account-level provisioning banner

Replace the per-group provisioning status cards with one account-level status banner:

- Load `getUserVapiConfig()` on mount
- If `status = 'active'`: show the phone number once at the top (e.g. "Your lease line: +14313415768")
- If `status = 'pending'`: show "Setting up your lease line…" spinner
- If `status = 'failed'`: show "Setup failed — [Retry]" button that calls `retryUserProvisioning()`
- If `status = 'not_set_up'`: show "Create your first property group to activate your lease line"

Individual property group cards no longer show `vapi_phone_number` or `vapi_provisioning_status` columns — those fields can be hidden from the card UI.

---

## Phase 4 — Execution Order

```
1. Run Phase 1 SQL (create table, modify pool, migrate leadpipecrm data)
2. Make Phase 2 + 3 code changes locally
3. Commit and push → Render auto-deploys
4. After deploy, trigger provisioning for leadpipecrm via API:
   POST /property-groups/users/me/provision-voice
   (with leadpipecrm bearer token)
5. Verify manager_vapi_config row: status=active, phone=+14313415768
6. Verify pool row: status=assigned, assigned_manager_id=28c43c77-...
7. Make test inbound call to +14313415768
   → should reach the new per-manager lease assistant
   → agent's find_listing/search tools should show ALL leadpipecrm listings
8. Make test outbound call from app → uses per-manager assistant
```

---

## Verification Checklist

- [ ] `manager_vapi_config` for `leadpipecrm@gmail.com`: `status=active`, `vapi_phone_number=+14313415768`
- [ ] `twilio_number_pool`: `+14313415768` row has `status=assigned`, `assigned_manager_id=28c43c77-...`
- [ ] `properties_list` for all 10 leadpipecrm groups: VAPI columns nulled out, `vapi_provisioning_status=not_applicable`
- [ ] Inbound call to `+14313415768` → VAPI routes to the manager's assistant → agent can see listings from ALL 10 property groups
- [ ] Lead captured on that call → `manager_id=28c43c77-...`, `property_group_id` populated from listing_uuid
- [ ] New user signs up, creates first property group → `manager_vapi_config` row created with `status=pending` → provisioning runs → `status=active`
- [ ] Same user creates second property group → NO new provisioning triggered → same number shown
- [ ] Outbound lease call from app → uses per-manager assistant from `manager_vapi_config`
- [ ] Pool empty scenario: new user with pool empty → `manager_vapi_config` gets `status=failed` (no silent fallback)

---

## Notes

- **Lead `property_group_id`**: When the agent identifies a listing, `listing_uuid` in the lead payload resolves to the right `property_group_id` automatically via Path 1 (existing logic). No code change needed there.
- **Old `properties_list` VAPI columns**: Leave them in the DB for now. They are no longer written to. A future cleanup migration can drop them.
- **Existing users with per-group active data**: Run Step 1.3 for each one — migrate their first active group's data to `manager_vapi_config`, null out `properties_list` VAPI columns.
- **VAPI assistant naming**: New assistants are named `Lease Agent [<first 8 chars of manager_id>]` for easy identification in the VAPI dashboard.
