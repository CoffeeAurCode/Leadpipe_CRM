## How to Add New Twilio Numbers to the Pool

### Step 1 — Buy the number in Twilio Console

1. Log into [console.twilio.com](https://console.twilio.com)
2. Go to **Phone Numbers → Manage → Buy a Number**
3. Filter by country and capabilities (Voice required)
4. Purchase the number — it will appear in E.164 format (e.g., `+15551234567`)
5. No webhook configuration needed in Twilio — VAPI handles all call routing

### Step 2 — Register in VAPI and add to pool

```bash
cd /path/to/Tenant_management_MVP
python backend/scripts/add_twilio_number_to_vapi.py +15551234567 --notes "US pool - May 2026"
```

The script will:
- Call VAPI's `CreatePhoneNumbersRequest_Twilio` to register the number
- Store the VAPI-assigned `phone_number_id` + E.164 number in `twilio_number_pool` with `status='available'`

### Step 3 — Verify

```bash
# Check the pool (Supabase dashboard or psql):
SELECT phone_number, vapi_phone_number_id, status, created_at
FROM twilio_number_pool
ORDER BY created_at DESC;
```

### Pool capacity rule of thumb

Keep at least **2 available** entries in the pool at all times so there's headroom if multiple managers sign up simultaneously. Add more before expected growth.

---

## Adding +1 249 402 8641 (Canada — already purchased)

This number has already been purchased in Twilio. E.164 format: `+12494028641`

### Step 1 — Confirm the number is active in Twilio

1. Log into [console.twilio.com](https://console.twilio.com)
2. Go to **Phone Numbers → Manage → Active Numbers**
3. Confirm `+1 (249) 402-8641` appears and has **Voice** capability enabled

### Step 2 — Run the admin script

From the project root:

```bash
python backend/scripts/add_twilio_number_to_vapi.py +12494028641 --notes "Canada CA — May 2026"
```

Expected output:
```
Registering +12494028641 into VAPI as a Twilio-owned number...
VAPI registered: id=<some-vapi-id>  number=+12494028641

Done. +12494028641 is available in the pool for auto-assignment.
  VAPI phone number ID : <some-vapi-id>
  Pool status          : available
```

### Step 3 — Verify the pool entry

In the Supabase dashboard → SQL Editor:

```sql
SELECT phone_number, vapi_phone_number_id, status, created_at
FROM twilio_number_pool
ORDER BY created_at DESC
LIMIT 5;
```

You should see `+12494028641` with `status = available`.

### What happens next

The next time any manager creates a new property group, this number will be automatically claimed from the pool, a per-group lease assistant will be created in VAPI, and the assistant will be linked to `+12494028641`. The manager will be able to receive inbound leasing calls on this number.

---

## What happens if you try to add an already-in-use number

### The protected numbers

These two numbers are already live and must never be re-registered:

| Number | E.164 | Role | Env var |
|---|---|---|---|
| +1 (438) 231-4283 | `+14382314283` | Complaint agent inbound + outbound | `VAPI_COMPLAINT_NUMBER_ID` |
| +1 (431) 341-5768 | `+14313415768` | Shared lease agent | `VAPI_SHARED_LEASE_NUMBER_ID` |

### Failure scenario A — number already registered in VAPI

Both `+14313415768` and `+14382314283` are already registered as VAPI phone number objects (they are the live shared agents). Running the script on either will fail at the VAPI API call, before anything touches the database:

```
$ python backend/scripts/add_twilio_number_to_vapi.py +14313415768

Registering +14313415768 into VAPI as a Twilio-owned number...
ERROR: VAPI registration failed: <VAPI error — number already exists or is already in use>
```

The script exits with code 1. The `twilio_number_pool` table is untouched. The existing VAPI phone number object and its linked assistant are completely unaffected — VAPI rejects the duplicate registration before any state changes.

### Failure scenario B — number already in the pool DB

If a number somehow passed the VAPI step but already exists in `twilio_number_pool` (e.g. you ran the script twice for the same number), the DB insert would fail on the `UNIQUE` constraint on `phone_number`:

```
Registering +12494028641 into VAPI as a Twilio-owned number...
VAPI registered: id=<new-vapi-id>  number=+12494028641
ERROR: DB insert failed: duplicate key value violates unique constraint "twilio_number_pool_phone_number_key"
NOTE: The number was registered in VAPI with id=<new-vapi-id>. Delete it manually if you need to retry.
```

In this case a duplicate VAPI phone number object was created. Clean it up via the VAPI dashboard or `backend/scripts/vapi_cleanup.py` before retrying.

### Summary — the script is safe to run on protected numbers

| What you run | VAPI step | DB step | Net effect |
|---|---|---|---|
| Fresh Twilio number (correct) | Succeeds | Succeeds | Number added to pool |
| Number already in VAPI (e.g. `+14313415768`) | **Fails** — VAPI rejects it | Never reached | Nothing changes |
| Number already in pool DB | Succeeds (duplicate VAPI object created) | **Fails** — UNIQUE violation | Need to delete orphaned VAPI object |

The dangerous case is B (rare in practice). The most likely mistake — running the script on a protected number like `+14313415768` — fails safely at VAPI with no side effects.
