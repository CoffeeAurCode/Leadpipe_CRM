# Lease Agent Phone-Scoping Plan
## Requirement
One VAPI phone number is assigned to exactly one property group (one manager). When a prospective tenant calls that number, the lease agent must ONLY search and present listings belonging to that manager's property group.

---

## Current Status

### What IS implemented (new property groups)

| Component | Status | Where |
|---|---|---|
| 1 phone number provisioned per new property group | ✅ Done | `vapi_provisioning.py` |
| Per-group lease assistant with `property_group_id` hardcoded in tool URLs | ✅ Done | `build_lease_config()` in `vapi_agent_config.py` |
| `find_listing` and `search_available_listings` filter by `property_group_id` param | ✅ Done | `routes/leasing.py` |
| Webhook resolves `property_group_id` + `manager_id` from VAPI call metadata | ✅ Done | `/voice/lease-lead-webhook` |
| Leads stored with correct `manager_id` and `property_group_id` | ✅ Done | `lease_lead_webhook` |
| Manager-scoped GET on leads, listings, metrics, export | ✅ Done | `routes/leasing.py` |

### What is NOT implemented / has gaps

#### Gap 1 — Legacy (existing) property groups use the shared unscoped agent
- `build_lease_config_shared()` does NOT append `?property_group_id=` to tool URLs
- Any call to the shared VAPI number queries ALL listings across ALL managers
- The shared agent fallback in the webhook (path 4) picks the **first** property group in the DB — wrong in multi-tenant
- **Affected:** property groups created before the per-group provisioning system was built

#### Gap 2 — `update_lead` and `delete_lead` do not enforce `manager_id` ownership
```python
# current (leasing.py:265)
resp = db.table("lease_leads").update(payload).eq("uuid", lead_uuid).execute()

# current (leasing.py:277)
db.table("lease_leads").delete().eq("uuid", lead_uuid).execute()
```
Any authenticated manager who knows a `lead_uuid` can modify or delete another manager's lead.

#### Gap 3 — Outbound lease calls use the shared agent, not the per-group one
- `POST /voice/call/outbound` with `agent="lease"` always uses `VAPI_SHARED_LEASE_ASSISTANT_ID`
- There is no way for the manager to trigger an outbound call from their per-group scoped agent

#### Gap 4 — No re-provisioning path for existing property groups
- Property groups that exist today have `vapi_provisioning_status = "not_applicable"` or `"failed"`
- There is no admin script or UI trigger to provision a per-group assistant for them

---

## Implementation Plan

### Fix 1 — Re-provision existing property groups (admin script)

**File:** `backend/scripts/reprovision_existing_groups.py` (new script)

```
For each row in properties_list where vapi_provisioning_status != "active":
    Call provision_vapi_for_property_group(property_group_id, pg_name, service_db)
    This creates a new per-group assistant + phone number and stores the IDs

After running, each property group will have its own phone number and scoped agent.
```

Steps:
1. Create `backend/scripts/reprovision_existing_groups.py` that:
   - Connects to Supabase with the service key
   - Selects all `properties_list` rows where `vapi_provisioning_status != "active"`
   - Calls `provision_vapi_for_property_group()` for each
2. Run this once on production

**This is the critical fix** — once all groups have per-group agents, the shared agent path becomes irrelevant.

---

### Fix 2 — Add `manager_id` ownership check to `update_lead` and `delete_lead`

**File:** `backend/app/routes/leasing.py`

Change `update_lead` (line ~265):
```python
# Before
resp = db.table("lease_leads").update(payload).eq("uuid", lead_uuid).execute()

# After
resp = (
    db.table("lease_leads")
    .update(payload)
    .eq("uuid", lead_uuid)
    .eq("manager_id", user["sub"])
    .execute()
)
```

Change `delete_lead` (line ~277):
```python
# Before
db.table("lease_leads").delete().eq("uuid", lead_uuid).execute()

# After
db.table("lease_leads").delete().eq("uuid", lead_uuid).eq("manager_id", user["sub"]).execute()
```

---

### Fix 3 — Outbound lease call should use the per-group agent

**File:** `backend/app/routes/voice.py` — `make_outbound_call` endpoint

The outbound call endpoint needs to know which property group the manager calling is associated with. When `agent="lease"`, look up the manager's property group(s), pick the first one with `vapi_provisioning_status = "active"`, and use its `vapi_lease_assistant_id` and `vapi_phone_number_id`.

Change `make_outbound_call`:
```python
if req.agent == "lease":
    # Look up manager's per-group provisioned agent
    pg_row = (
        svc_db.table("properties_list")
        .select("vapi_lease_assistant_id, vapi_phone_number_id")
        .eq("manager_id", current_user["sub"])
        .eq("vapi_provisioning_status", "active")
        .limit(1)
        .execute()
    )
    if pg_row.data:
        assistant_id = pg_row.data[0]["vapi_lease_assistant_id"]
        phone_number_id = pg_row.data[0]["vapi_phone_number_id"]
    else:
        # Fall back to shared agent for managers without a provisioned group
        assistant_id = settings.VAPI_SHARED_LEASE_ASSISTANT_ID
        phone_number_id = settings.VAPI_SHARED_LEASE_NUMBER_ID or settings.VAPI_NUMBER_ID
```

This requires adding `current_user: dict = Depends(get_current_user)` and `svc_db: Client = Depends(get_service_db)` to `make_outbound_call`.

---

### Fix 4 — Remove the "first property group" shared agent fallback in the webhook

**File:** `backend/app/routes/voice.py` — `lease_lead_webhook`

Path 4 (the shared agent fallback) picks the first property group in the DB. In multi-tenant this is wrong. After Fix 1 re-provisions all groups, path 2 (assistant_id lookup) and path 3 (phoneNumberId lookup) will always resolve correctly — the fallback becomes dead code.

Change path 4 to log a warning and set `property_group_id = None` instead of guessing:
```python
# Path 4: log unknown agent, do not guess
if not property_group_id:
    print(f"  [WARN] Could not resolve property_group_id for assistant={assistant_id} phone={phone_number_id}")
    resolution_path = "unresolved"
```

The lead will still be saved with `property_group_id = None` rather than assigned to the wrong manager.

---

## Priority Order

| # | Fix | Impact | Effort |
|---|---|---|---|
| 1 | Re-provision existing property groups | High — unscopes shared agent | Low (run script once) |
| 2 | `update_lead` / `delete_lead` `manager_id` filter | Medium — data ownership | Very low (2 lines) |
| 3 | Remove wrong "first PG" fallback in webhook | Medium — data correctness | Very low (3 lines) |
| 4 | Outbound call uses per-group agent | Low — convenience | Medium |

**Do Fix 1 + Fix 2 + Fix 3 first.** Fix 4 is an enhancement.

---

## What does NOT need to change

- `vapi_provisioning.py` — correct as-is; already provisions per-group assistant + number
- `build_lease_config()` — correct; hardcodes `property_group_id` in tool URLs at creation time  
- `/leasing/find-listing` and `/leasing/search` — correct; already filter by `property_group_id` when provided
- `GET /leasing/leads`, metrics, export — correct; already scoped by `manager_id`
- The 3-path resolution in the webhook (paths 1–3) — correct
