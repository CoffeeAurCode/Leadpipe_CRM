# Session Context — 2026-05-24

## Issues Fixed

### 1. Lease Agent Showing Only One Unit for a Building Name Query
**Symptom:** Caller asked for units in Sunrise Heights; agent said only one option exists. Five units are listed.

**Root cause:** `GET /leasing/find-listing` uses a 3-step fallback:
1. `ilike(flat_number, "%query%")` — misses because flat numbers are A101/B202 etc., not building names
2. `ilike(title, "%query%")` — misses because titles are empty
3. Address match on joined `flats.address` — correctly found all 5 units but did `matched[0]` (only returned the first)

**Fix (`backend/app/routes/leasing.py`):**
- Third fallback now returns **all** address-matched listings, not just `matched[0]`
- Normalised both the address-hit path and the flat_number/title-hit paths to return a consistent `{found, count, listings: [...]}` shape — same as `/leasing/search`

---

### 2. Address/Building Preference Not Captured on Lead Records
**Symptom:** Lead records showed `bedrooms=0, budget_max=0` with no trace of what building/location the caller asked about.

**Fix — three files:**

**`backend/app/services/vapi_agent_config.py`**
- Added `address_preference` field to `submit_lease_lead` tool schema — agent copies exactly what it passed as `query` to `find_listing` or `address` to `search_available_listings`
- Updated "Capture Lead" step in system prompt to explicitly instruct the agent to populate `address_preference`
- Updated `find_listing` tool description to explain the response is now a `listings` array and all results must be presented when `count > 1`
- Updated system prompt "Find a Listing" step to state both tools return `{found, count, listings}` and all listings must be presented

**`backend/app/routes/voice.py` (lease-lead-webhook)**
- After parsing `qualifying_answers`, extracts `address_preference` from lead payload and injects it into `qualifying_answers` as `{"address_preference": "Sunrise Heights"}` — no DB migration needed

**`frontend/src/components/LeadDetailModal.jsx`**
- Added `MapPin` icon import
- Strips `address_preference` from the Qualifying Answers section display
- Shows `address_preference` as a full-width row at the top of the Preferences section with a MapPin icon
- Fixed `bedrooms`, `budget_max`, `occupants` to not render when value is `0` (VAPI sends 0 as "not stated")
- Fixed currency symbol to `₹` with Indian locale formatting (`en-IN`)

---

## VAPI Assistant Update

**Script created:** `backend/scripts/update_lease_assistants.py`

One-shot script that reads all active `manager_vapi_config` rows from Supabase, rebuilds the lease agent config via `build_lease_config()`, and PATCHes each VAPI assistant via the REST API.

**Key detail:** VAPI's PATCH endpoint rejects `role` and `endCallAfterSpoken` fields inside tool `messages` blocks — script strips these down to `{type, content}` only before sending.

**Run with:**
```bash
cd backend
python scripts/update_lease_assistants.py
```

**Assistants updated this session:**
| Label | Manager ID | VAPI Assistant ID |
|---|---|---|
| Per-manager (you) | `28c43c77` | `c76a69ea-103d-4a24-b542-adda79957294` |
| Per-manager (other) | `7fb0c018` | `70a03059-1595-47d9-b94b-b41deaa49030` |
| Shared lease agent | — | `2dba3a50-6862-400c-861a-bfc0a45d4a95` |

VAPI changes are **live immediately** — no deploy needed for the assistant config.

---

## Still Needs Deploy (Render)

| File | Change |
|---|---|
| `backend/app/routes/leasing.py` | `find_listing` returns all address-matched listings |
| `backend/app/routes/voice.py` | Extracts `address_preference` from webhook payload |
| `frontend/src/components/LeadDetailModal.jsx` | Shows address preference + fixes zero-value display |

---

## Data Notes

- Sunrise Heights has 5 flats: A101 (1BHK), B202 (2BHK), C301 (3BHK), D404 (2BHK), E501 (2BHK)
- All 5 have active listings under `manager_id = 28c43c77-8c9c-496f-8d1e-39ffa9d619e3`
- `address_preference` is stored inside the `qualifying_answers` JSONB column — no new DB column required
