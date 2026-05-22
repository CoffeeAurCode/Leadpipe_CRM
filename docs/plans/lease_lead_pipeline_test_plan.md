# Lease Lead Pipeline — Pre-Deploy Test Plan

Tests the full path: VAPI call → webhook → DB → Leasing tab UI.
Run top-to-bottom. Each section must pass before moving to the next.

---

## 0. Pre-flight

- [ ] Backend is running locally (`uvicorn app.main:app --reload`)
- [ ] `.env` has `VAPI_SHARED_LEASE_ASSISTANT_ID` and `VAPI_SHARED_LEASE_NUMBER_ID` set
- [ ] At least one property group exists in Supabase (`properties_list`)
- [ ] At least one active listing exists in `lease_listings` (linked to the property group above)
- [ ] Frontend dev server is running

---

## 1. DB Baseline Check

Open Supabase → Table Editor.

- [ ] `lease_leads` table exists with columns: `id`, `uuid`, `property_group_id`, `listing_uuid`, `caller_name`, `phone`, `qualification_status`, `created_at`, `updated_at`
- [ ] `updated_at` column allows NULL (no NOT NULL constraint) — the insert never sets it
- [ ] Note the `id` of your test property group — you'll verify this appears in the captured lead

---

## 2. Webhook Endpoint — Unit Test (no VAPI needed)

Send a crafted POST directly to the webhook to verify property_group_id resolution.

### 2a. Path 4 — Shared agent fallback

```bash
curl -X POST http://localhost:8000/voice/lease-lead-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "tool-calls",
      "call": {
        "id": "test-call-001",
        "assistantId": "<VAPI_SHARED_LEASE_ASSISTANT_ID from .env>",
        "phoneNumberId": "<VAPI_SHARED_LEASE_NUMBER_ID from .env>",
        "customer": { "number": "+919999999999" }
      },
      "toolCalls": [{
        "function": {
          "name": "submit_lease_lead",
          "arguments": "{\"caller_name\":\"Test User\",\"bedrooms\":2,\"budget_max\":15000,\"move_in_timeline\":\"Next month\",\"occupants\":2,\"floor_preference\":\"\",\"listing_uuid\":\"\",\"qualifying_answers\":{\"stable_income\":\"yes\"},\"disqualifying_reason\":\"\",\"qualification_status\":\"qualified\"}"
        }
      }]
    }
  }'
```

**Expected response:** `{"status": "processed"}`

**Expected backend log:**
```
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.assistantId: <your shared assistant ID>
  [submit_lease_lead args]
    caller_name: Test User
    qualification_status: qualified
  [pg resolution] path=shared_agent_fallback property_group_id=<uuid>
  [SAVED] phone=+919999999999 status=qualified property_group_id=<uuid>
```

- [ ] Response is `{"status": "processed"}`
- [ ] Log shows `path=shared_agent_fallback`
- [ ] Log shows a non-null `property_group_id`
- [ ] Supabase `lease_leads` has a new row with that `property_group_id`
- [ ] `updated_at` on the new row is NULL (expected — no default set)

### 2b. Path 1 — listing_uuid resolution

```bash
curl -X POST http://localhost:8000/voice/lease-lead-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "tool-calls",
      "call": {
        "id": "test-call-002",
        "assistantId": "some-other-assistant-id",
        "phoneNumberId": "some-other-number-id",
        "customer": { "number": "+919999999998" }
      },
      "toolCalls": [{
        "function": {
          "name": "submit_lease_lead",
          "arguments": "{\"caller_name\":\"Listing Test\",\"listing_uuid\":\"<a real listing UUID from lease_listings>\",\"qualification_status\":\"qualified\",\"bedrooms\":2,\"budget_max\":10000,\"move_in_timeline\":\"Immediate\",\"occupants\":1,\"floor_preference\":\"\",\"qualifying_answers\":{},\"disqualifying_reason\":\"\"}"
        }
      }]
    }
  }'
```

- [ ] Log shows `path=listing_uuid`
- [ ] `property_group_id` in DB matches the listing's property group

### 2c. No tool call — should be ignored

```bash
curl -X POST http://localhost:8000/voice/lease-lead-webhook \
  -H "Content-Type: application/json" \
  -d '{"message": {"type": "tool-calls", "call": {}, "toolCalls": []}}'
```

- [ ] Response is `{"status": "ignored"}`
- [ ] No new row inserted in `lease_leads`

---

## 3. API Endpoint — GET /leasing/leads

Open browser → DevTools → Network tab.
Navigate to the Leasing tab.

- [ ] `GET /leasing/leads` returns HTTP 200 (not 500)
- [ ] Response body is a JSON array (not an error object)
- [ ] The test leads from Section 2a and 2b appear in the array
- [ ] Each lead has `uuid`, `caller_name`, `phone`, `qualification_status`, `property_group_id`

**If you get HTTP 500:** Open the backend log — look for `ResponseValidationError`. Most likely cause is a non-nullable field in `LeadResponse` that has NULL in the DB. Check `updated_at`.

---

## 4. API Endpoint — GET /leasing/metrics

- [ ] `GET /leasing/metrics` returns HTTP 200
- [ ] `total_calls` equals the number of rows inserted during Section 2
- [ ] `qualified` count is correct
- [ ] `qualification_rate` is a number (not NaN or null)

---

## 5. Frontend — Leasing Tab UI

- [ ] Leasing tab loads without console errors
- [ ] Listings are visible (S-106, S-104, etc.)
- [ ] Metrics cards show non-zero values matching Section 4
- [ ] Leads table shows rows matching the curl inserts from Section 2
- [ ] Each lead row shows: Name, Phone, Budget, Beds, Move-in, Status
- [ ] Status badge colour is correct (green for qualified, etc.)
- [ ] **Refresh button** is visible top-right of the page header
- [ ] Clicking Refresh reloads data without a full page reload

---

## 6. Lead Detail Modal

- [ ] Click "View" on a lead row
- [ ] Modal opens showing all lead fields
- [ ] Change qualification status to "contacted" → Save
- [ ] Lead row in table updates to "contacted"
- [ ] Trying to set status back to "qualified" → should be blocked (manager cannot set back to agent statuses)

---

## 7. Live VAPI Call Test (end-to-end)

Prerequisite: the shared lease phone number is linked to the VAPI shared assistant.

1. Call the lease agent phone number from your test phone
2. Complete the conversation; let the agent qualify you
3. Agent calls `submit_lease_lead` (watch backend log for the webhook block)
4. Verify log shows:
   - [ ] `path=shared_agent_fallback` (or `phone_number_id` if the number is stored in DB)
   - [ ] `property_group_id` is non-null
5. Go to Leasing tab → click **Refresh**
6. Verify:
   - [ ] New lead appears with your phone number
   - [ ] `qualification_status` matches what the agent determined
   - [ ] Metrics counters incremented by 1

---

## 8. Edge Cases

### 8a. Hallucinated listing_uuid

Send a webhook with a non-UUID `listing_uuid` (e.g. `"S-106"`):

- [ ] Log shows `listing_uuid` set to `None` (UUID regex rejected it)
- [ ] Falls through to path 4
- [ ] Lead is still saved

### 8b. Empty property_group resolution

Send a webhook with an `assistantId` and `phoneNumberId` that don't match any env var or DB row:

- [ ] Log shows `path=None property_group_id=None`
- [ ] Lead is saved with `property_group_id = NULL`
- [ ] Lead does NOT appear in manager's lead list (expected — unclaimable orphan)

---

## 9. Cleanup

- [ ] Delete test leads inserted during Section 2 from Supabase (or via the Delete button in UI)
- [ ] Confirm `lease_leads` table is back to baseline

---

## Sign-off

| Check | Result |
|---|---|
| Webhook processes shared agent call correctly | |
| property_group_id resolved via correct path | |
| Leads visible in UI after Refresh | |
| Metrics match actual lead count | |
| Lead detail + status update works | |
| Live call end-to-end passes | |
