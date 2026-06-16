# Bug Diagnosis — Lease Agent: Dehradun Listing Not Found + Lead Not Visible
**Date:** 2026-06-07  
**Test call:** `call_id=019ea216-3dd9-7001-960d-8c854d9a62d0`, phone `+919998064026`, caller "Pronov"

---

## Two Independent Bugs

---

## Bug 1 — Agent Says No Listing Found (Dehradun)

### What happened
Caller asked about a unit in Dehradun. The listing **does exist** (id=71, unit 101, `lease_listings.uuid = 16181a8d-5cdb-489a-8951-cae1c17aae26`). The agent called `find-units` and got zero results, then told the caller no matching listing was found.

### Evidence from logs
```
GET /leasing/find-units?manager_id=28c43c77...&query=Dehradun%20Uttarakhand → 200 OK
[LEASE LEAD DIRECT] ... 'notes': 'Caller asked about a unit in Dehradun, Uttarakhand but no matching listing was found.'
'qualification_status': 'unmatched', 'interested_listing_ids': []
```

### Root cause: verbatim substring match + spelling mismatch

`find_units` in `backend/app/routes/leasing.py:199–208` builds a haystack by joining all fields and checks:

```python
if query_lower in haystack:
```

The query sent was: `"dehradun uttarakhand"` (correct spelling).

The listing in the DB has `city = "Dehradun"` and `state = "Uttrakhand"` — note the typo: **missing the first 'a'** (`Uttrakhand` vs `Uttarakhand`).

Joined haystack: `"101  dehradun uttrakhand india   "`

The string `"dehradun uttarakhand"` is NOT a substring of `"... dehradun uttrakhand ..."` — the verbatim check fails.

### Two contributing factors

**Factor A — Data typo:** The listing was created with `state = "Uttrakhand"` instead of `"Uttarakhand"`. This is visible in `LEASING_LIST.csv` row for id=71.

**Factor B — Fragile search algorithm:** `find_units` does a single verbatim `query_lower in haystack` check — the entire multi-word query must appear as a contiguous substring. Even a minor spelling difference (user DB typo vs. what the AI infers from speech-to-text) breaks the match.

If the search instead tokenized the query and checked each token independently:
```python
# Token-based: any token must appear anywhere in haystack
tokens = query_lower.split()
if any(tok in haystack for tok in tokens):
```
…then `"dehradun"` would still match even if `"uttarakhand"` didn't, because "dehradun" IS in the haystack.

### Fix required
Two changes are needed:

1. **Fix the data typo:** Update `state` from `"Uttrakhand"` to `"Uttarakhand"` on listing id=71 (uuid `16181a8d-...`).

2. **Fix the search algorithm** in `find_units` (leasing.py:191): change the single-string `in` check to token-based matching so that if any significant token matches, the listing is returned:
   ```python
   tokens = [t for t in query_lower.split() if len(t) > 2]
   if any(tok in haystack for tok in tokens):
   ```
   This makes the search resilient to partial queries, extra words, and minor spelling divergence.

---

## Bug 2 — Lead Not Visible on Leasing AI Tab

### What happened
The lead was saved (`[SAVED] phone=919998064026 status=unmatched`) but the manager cannot see it on the Leasing AI tab under the Leads section.

### Root cause: `manager_id = NULL` on unmatched leads in `lease-lead-direct`

#### How manager_id is resolved in `POST /voice/lease-lead-direct` (voice.py:814–821):

```python
manager_id = None
property_group_id = None

if listing_uuid:                   # ← only resolves when a listing was matched
    row = db.table("lease_listings").select("property_group_id, manager_id")...
    if row.data:
        manager_id = row.data[0].get("manager_id")
```

For an **unmatched call**, `listing_uuid` is `""` → fails UUID regex → becomes `None` → the `if listing_uuid:` block is **skipped entirely**. `manager_id` stays `None`.

The lead is inserted with `"manager_id": None`.

#### Why that makes the lead invisible

`GET /leasing/leads` (leasing.py:573) queries:
```python
q = db.table("lease_leads").select("*").eq("manager_id", user["sub"])
```

`eq("manager_id", user["sub"])` will never match a row where `manager_id IS NULL`. The lead exists in the DB but is invisible to the manager.

#### Why the VAPI config doesn't help

In `vapi_agent_config.py:1228`, the `submit_lease_lead` URL is:
```python
f"{backend_url}/voice/lease-lead-direct?call_id={{{{call.id}}}}&phone={{{{customer.number}}}}"
```

`manager_id` is **not** passed as a query param to `lease-lead-direct`. Compare with `find_units` which correctly injects it:
```python
f"{backend_url}/leasing/find-units?manager_id={manager_id or ''}&query={{{{query}}}}"
```

The deprecated `lease_lead_webhook` had a 3-path fallback (listing_uuid → assistant_id → phone_number_id) to resolve manager_id even when no listing was matched. That fallback was never ported to `lease-lead-direct`.

### Fix required
Two changes are needed:

1. **Inject `manager_id` into `submit_lease_lead` URL** in `vapi_agent_config.py:1228`:
   ```python
   "url": f"{backend_url}/voice/lease-lead-direct?call_id={{{{call.id}}}}&phone={{{{customer.number}}}}&manager_id={manager_id or ''}",
   ```

2. **Accept `manager_id` as a query param in `lease-lead-direct`** (voice.py:788–884) and use it as fallback when `listing_uuid` is absent:
   ```python
   async def lease_lead_direct(
       request: Request,
       call_id: str | None = None,
       phone: str | None = None,
       manager_id: str | None = None,   # ← add this
       db: Client = Depends(get_service_db),
   ):
       ...
       # after listing_uuid resolution block fails:
       if not manager_id:
           # existing listing_uuid path sets manager_id
           pass
       # manager_id from query param is the fallback for unmatched calls
   ```
   Then in `lead_payload`:
   ```python
   "manager_id": str(manager_id) if manager_id else None,
   ```
   *(already there — just needs manager_id to be non-None for unmatched calls)*

   After the fix, also run `update_lease_agents.py` to push the new URL to all active VAPI assistants.

---

## Summary Table

| # | Bug | File | Line | Root Cause | Impact |
|---|-----|------|------|------------|--------|
| 1a | Listing not found | `lease_listings` DB row | id=71 | `state = "Uttrakhand"` (typo) | Agent reports "no match" |
| 1b | Listing not found | `backend/app/routes/leasing.py` | 208 | Verbatim `query in haystack` — no tokenization | Any spelling divergence breaks search |
| 2a | Lead invisible | `backend/app/services/vapi_agent_config.py` | 1228 | `manager_id` not in `submit_lease_lead` URL | `manager_id=NULL` saved on unmatched leads |
| 2b | Lead invisible | `backend/app/routes/voice.py` | 814 | No fallback when `listing_uuid` is empty | Unmatched leads always have `manager_id=NULL` |

---

## Quick Verification Queries (Supabase SQL)

```sql
-- Confirm the lead exists with NULL manager_id
SELECT uuid, caller_name, phone, qualification_status, manager_id, created_at
FROM lease_leads
WHERE call_id = '019ea216-3dd9-7001-960d-8c854d9a62d0';

-- Fix the data typo on the Dehradun listing
UPDATE lease_listings
SET state = 'Uttarakhand'
WHERE uuid = '16181a8d-5cdb-489a-8951-cae1c17aae26';

-- Manually patch the orphaned lead's manager_id
UPDATE lease_leads
SET manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3'
WHERE call_id = '019ea216-3dd9-7001-960d-8c854d9a62d0';
```
