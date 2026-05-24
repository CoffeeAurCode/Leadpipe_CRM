# Lease Agent — Fix Plan & Test Checklist (updated 2026-05-24)

## Changes Made This Session (all VAPI-live)

| Change | File | Status |
|---|---|---|
| EOC fallback webhook endpoint | `voice.py` | Code done, needs deploy |
| Added `server.url` to lease assistant shell | `vapi_agent_config.py` | VAPI patched ✅ |
| Fixed `server_messages` — only `["end-of-call-report"]` | `vapi_agent_config.py` | VAPI patched ✅ |
| Fixed `find_listing` variableExtractionPlan | `vapi_agent_config.py` | VAPI patched ✅ |
| Fixed `search_available_listings` variableExtractionPlan | `vapi_agent_config.py` | VAPI patched ✅ |
| Added `[Error Handling]` section to lease agent prompt | `vapi_agent_config.py` | VAPI patched ✅ |

---

## Required: Deploy to Render

Push the current branch so Render deploys `voice.py` containing `POST /voice/lease-eoc-webhook`.
Until that endpoint is live on Render, VAPI gets a 404 for end-of-call events and the fallback
lead capture doesn't work.

**After pushing, wait 3 full minutes before placing a test call.**
(Render can do two restarts in quick succession; 3 minutes ensures the server is fully stable.)

---

## Test Checklist

### Before every test call
- [ ] Render logs show "Your service is live 🎉"
- [ ] Wait 3 minutes after the live signal
- [ ] No active deployments running

---

### Test 1 — Bedroom search (core path)
1. Place outbound **lease** call
2. Say: "I'm looking for a 2-bedroom unit"
3. **Expected in Render logs:** `GET /leasing/search?bedrooms=2&...` within 15s of call connecting
4. **Expected from agent:** reads back matching 2BHK units by flat number and rent
5. **Expected:** agent asks qualifying questions, then asks for your name
6. **Expected:** agent calls submit_lease_lead (you'll see `POST /voice/lease-lead-webhook` in logs)
7. **Expected:** lead appears in dashboard with bedrooms=2, caller_name = your name

### Test 2 — Building name search (5 units)
1. Place outbound **lease** call
2. Say: "I'm looking for something in Sunrise Heights"
3. **Expected in Render logs:** `GET /leasing/find-listing?query=Sunrise+Heights&...`
4. **Expected from agent:** presents ALL 5 units (A101 1BHK, B202 2BHK, C301 3BHK, D404 2BHK, E501 2BHK)
5. **Expected:** lead saved with `address_preference = "Sunrise Heights"`

### Test 3 — Unknown address → fallback search
1. Place outbound **lease** call
2. Say: "I'm looking for something in Green Valley"
3. **Expected in Render logs:** `GET /leasing/find-listing?query=Green+Valley&...`
4. **Expected from agent:** "no units at Green Valley", then offers to search all available units
5. **Expected in Render logs:** `GET /leasing/search?bedrooms=0&budget_max=0&...`
6. **Expected:** lead saved as `unmatched` or `qualified` depending on outcome

### Test 4 — Tool failure recovery (disconnect mid-search)
1. Start a lease call
2. The moment the agent says the greeting, immediately hang up
3. **Expected in Render logs after a few seconds:** `POST /voice/lease-eoc-webhook`
4. **Expected in logs:** `[LEASE EOC] Partial lead saved for call_id=...`
5. **Expected:** lead appears in dashboard with `caller_name = "Unknown"`, `qualification_status = "unmatched"`, transcript in notes

### Test 5 — Error handling (simulate tool failure)
1. Temporarily stop the Render service (or test during a deploy)
2. Place a lease call
3. **Expected from agent:** "Give me just one moment, I'm having a brief connection issue." (retry)
4. **Expected from agent:** after second failure: "I'm sorry, I'm unable to search our listings right now. Our team will follow up."
5. **Expected:** agent then asks for your name and calls submit_lease_lead with `qualification_status="unmatched"`

---

## Render Log Patterns to Confirm Everything is Working

```
GET  /leasing/find-listing?query=...        ← find_listing called ✓
GET  /leasing/search?bedrooms=...           ← search_available_listings called ✓
POST /voice/lease-lead-webhook              ← submit_lease_lead fired (happy path) ✓
POST /voice/lease-eoc-webhook               ← EOC fallback fired ✓
[LEASE EOC] Partial lead saved for call_id= ← fallback lead created ✓
```

If `GET /leasing/find-listing` or `GET /leasing/search` never appear after the call
connects → the VAPI tool config is still broken. In that case re-run:
```
cd backend && python scripts/update_lease_assistants.py
```

---

## Architecture Summary (post-fix)

```
Outbound call placed
        │
        ▼
VAPI lease agent speaks greeting
        │
        ▼
Caller states preference
        │
        ├─ apiRequest → GET /leasing/find-listing   (direct HTTP, no server URL)
        │              or
        └─ apiRequest → GET /leasing/search         (direct HTTP, no server URL)
                │
                ▼
        Results read by LLM → qualifying questions → asks caller name
                │
                ▼
        function tool → POST /voice/lease-lead-webhook   (tool's own server URL)
                │
                ▼
        Call ends → VAPI sends end-of-call-report
                │
                ▼
        POST /voice/lease-eoc-webhook   (assistant's server URL)
        If lead already exists → ignored
        If no lead → saves partial lead with transcript
```
