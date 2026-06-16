# Render Environment Variables — New Additions

These are the env vars you need to add (or verify) on Render.
Existing vars like `SUPABASE_URL`, `STRIPE_SECRET_KEY`, etc. are already set — only new ones are listed here.

---

## VAPI — New Agent IDs

| Variable | Where to find it | Required? |
|---|---|---|
| `VAPI_COMPLAINT_ASSISTANT_ID` | VAPI Dashboard → Assistants → your Complaint Agent → copy the ID | Yes |
| `VAPI_COMPLAINT_NUMBER_ID` | VAPI Dashboard → Phone Numbers → the number linked to the Complaint Agent → copy the ID | Yes |
| `VAPI_SHARED_LEASE_ASSISTANT_ID` | VAPI Dashboard → Assistants → your Lease Agent → copy the ID | Yes |
| `VAPI_SHARED_LEASE_NUMBER_ID` | VAPI Dashboard → Phone Numbers → the number linked to the Lease Agent → copy the ID | Optional — falls back to `VAPI_NUMBER_ID` if blank |

### What each one does

- **`VAPI_COMPLAINT_ASSISTANT_ID`** — the new global complaint agent (Option B, all property groups). Used by inbound calls.
- **`VAPI_COMPLAINT_NUMBER_ID`** — the Twilio/VAPI number that rings the complaint agent.
- **`VAPI_SHARED_LEASE_ASSISTANT_ID`** — the shared lease inquiry agent for existing property groups. Used by outbound calls when agent = "lease" is selected.
- **`VAPI_SHARED_LEASE_NUMBER_ID`** — the Twilio/VAPI number linked to the lease agent. If left blank, outbound lease calls fall back to `VAPI_NUMBER_ID`.

---

## Already on Render (verify these exist)

| Variable | Used for |
|---|---|
| `PRIVATE_VAPI_API` | VAPI server-side API key — required for all outbound calls |
| `VAPI_ASSISTANT_ID` | Legacy test-group complaint agent — still used for outbound "complaint" calls |
| `VAPI_NUMBER_ID` | Legacy phone number — fallback for outbound calls |

---

## How to add on Render

1. Go to your Render service → **Environment** tab
2. Click **Add Environment Variable** for each one above
3. **Save Changes** → Render will redeploy automatically

---

## Outbound call routing (for reference)

| Frontend selection | `assistant_id` used | `phone_number_id` used |
|---|---|---|
| Complaint agent | `VAPI_ASSISTANT_ID` | `VAPI_NUMBER_ID` |
| Lease agent | `VAPI_SHARED_LEASE_ASSISTANT_ID` | `VAPI_SHARED_LEASE_NUMBER_ID` → fallback `VAPI_NUMBER_ID` |
