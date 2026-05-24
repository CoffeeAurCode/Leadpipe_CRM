# Lease Agent — Fix Plan & Test Checklist (2026-05-24)

## Changes Made This Session

### 1. EOC fallback webhook (voice.py + vapi_agent_config.py)
- Added `POST /voice/lease-eoc-webhook` endpoint
- If `submit_lease_lead` was never called, a partial `unmatched` lead is saved
  with the full transcript in `notes`
- `server.url` added to all three lease assistant shells so VAPI routes
  `end-of-call-report` events to the new endpoint
- `_last_call_ended_at` is now stamped by lease calls too (frontend refreshes)

### 2. `find_listing` variableExtractionPlan fixed
- Previous shape: flat top-level fields (`listing_uuid`, `address`, etc.)
- New shape: `{ found, count, listings: [...] }`
- Extraction plan updated to match the array response

### 3. `search_available_listings` variableExtractionPlan fixed
- Added `items` schema so VAPI can extract individual listing objects from
  the array, including `listing_uuid` for the LLM to reference

All three VAPI assistants were re-patched after each fix via
`python scripts/update_lease_assistants.py`.

---

## Deploy Required (Render)

| File | Change |
|---|---|
| `backend/app/routes/voice.py` | New `POST /voice/lease-eoc-webhook` endpoint |
| `backend/app/services/vapi_agent_config.py` | Fixed extraction plans + server URL |

The VAPI assistant configs are already live. The backend endpoint needs a deploy.

---

## Test Checklist

### Before testing
- [ ] Render service shows "Your service is live" in logs
- [ ] Wait **2 full minutes** after the deploy before placing a call
  (Render sometimes does a second restart after initial live signal)
- [ ] Confirm no active deployments are running while the call is live

### Test 1 — Search by bedrooms (no address)
1. Place outbound lease call
2. Say: "I'm looking for a 2-bedroom unit"
3. **Expected:** Agent calls `search_available_listings` (you'll see
   `GET /leasing/search?bedrooms=2&...` in Render logs)
4. **Expected:** Agent reads back all 2BHK units (flat number, rent, availability)
5. **Expected:** Agent asks qualifying questions from the listing's custom_rules
6. **Expected:** Agent asks for your name before ending
7. **Expected:** Lead appears in `/leasing/leads` after call

### Test 2 — Search by building name (5 units)
1. Place outbound lease call
2. Say: "I'm looking for something in Sunrise Heights"
3. **Expected:** Agent calls `find_listing?query=Sunrise+Heights`
   (`GET /leasing/find-listing?query=...` in Render logs)
4. **Expected:** Agent presents ALL 5 units (A101, B202, C301, D404, E501)
5. **Expected:** Lead captured with `address_preference = "Sunrise Heights"`

### Test 3 — Unknown address fallback
1. Place outbound lease call
2. Say: "I'm looking for something in Green Valley"
3. **Expected:** `find_listing` returns `{"found": false, "count": 0}`
4. **Expected:** Agent says no units found at that address
5. **Expected:** Agent offers to search all available units (calls
   `search_available_listings` with no filters)
6. **Expected:** Lead captured as `unmatched` or `qualified` depending on outcome

### Test 4 — EOC fallback (incomplete call)
1. Place outbound lease call
2. Say one or two things, then hang up immediately (before agent asks your name)
3. **Expected:** `POST /voice/lease-eoc-webhook` appears in Render logs after call ends
4. **Expected:** Lead appears in dashboard with `caller_name = "Unknown"`,
   `qualification_status = "unmatched"`, transcript in notes field

### Render log patterns to verify
```
GET /leasing/find-listing?query=...           ← find_listing called
GET /leasing/search?bedrooms=...              ← search called
POST /voice/lease-lead-webhook                ← submit_lease_lead fired (happy path)
POST /voice/lease-eoc-webhook                 ← EOC fallback fired
[LEASE EOC] Partial lead saved for call_id=... ← fallback lead created
```

---

## Known Limitations

- **Render cold restarts:** If Render restarts during an active call, the
  `apiRequest` tools will fail. VAPI does not retry. Test on a stable server.
- **EOC webhook timing:** If the call ends during a Render restart window,
  the EOC webhook is lost and no fallback lead is created. This is unavoidable
  with a single-server setup; frequency is low in practice.
- **LLM reliability:** The LLM may occasionally skip `submit_lease_lead` even
  with clear instructions. The EOC fallback covers this case. The partial lead
  has the full transcript so the manager can manually review.
