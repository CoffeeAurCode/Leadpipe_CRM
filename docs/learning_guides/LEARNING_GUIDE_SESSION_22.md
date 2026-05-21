# Learning Guide — Session 22
## Topic: Two Voice Agents (Complaint + Lease) + Image Upload + Testing

> **Continues from Session 21** (Feature Roadmap Execution + RLS Auditing + Google OAuth deployment debugging).  
> This session built a complete AI Leasing Voice Agent from spec to working backend, wired the Complaint Agent to support multi-manager deployments, created a production-grade image upload system, and ran a full automated test suite that caught 9 real bugs.

---

## What We Built This Session

| Feature | Files | Status |
|---------|-------|--------|
| Complaint Agent — multi-manager upgrade | `routes/flats.py`, `services/vapi_agent_config.py` | Code complete |
| Lease Agent — VAPI tool endpoints | `routes/leasing.py` | Code complete + tested |
| Lease Agent — Manager CRUD | `routes/leasing.py` | Code complete + tested |
| Lease Agent — auto-provisioning | `services/vapi_provisioning.py` | Code complete |
| New Pydantic schemas | `schemas/leasing.py` | Code complete |
| DB migration | `migrations/010_voice_agents.sql` | Written — run in Supabase |
| Image upload endpoint | `routes/upload.py` | Code complete |
| Image upload UI component | `components/ImageUploadField.jsx` | Code complete |
| RLS write policies fix | `migrations/011_properties_list_rls.sql` | Written — run in Supabase |
| Leasing dashboard tab | `components/LeasingTab.jsx` | Code complete |
| Leasing modals | `components/AddListingModal.jsx`, `components/LeadDetailModal.jsx` | Code complete |
| Automated test suite | `scripts/test_complaint_endpoints.sh`, `scripts/test_leasing_endpoints.sh` | 55/55 PASS |

---

## Part 1 — Reading a Product Spec and Turning It Into Code

### 1.1 The Spec-to-Code Translation Process

Before writing a single line of code, the product spec (`docs/feature_specs/Leadpipe_Leasing_Agent_Spec.md`) was read in full. The spec described what the product *does* — it doesn't care about FastAPI, Pydantic, or VAPI. Your job is to bridge them.

The translation process:

```
Spec says:               → Code means:
────────────────────────────────────────────────────────────────────
"Each unit is added      → lease_listings table with flat FK
  with custom rules"     → custom_rules JSONB column
                         → CustomRules Pydantic model

"Qualifying criteria     → VAPI tool: /leasing/find-listing
  per property"            returns custom_rules JSON to the agent

"Qualified leads are     → lease_leads table
  inserted into CRM"      POST /voice/lease-lead-webhook endpoint

"Filter by: property,    → GET /leasing/leads?listing_uuid=&qualification_status=
  date range, status"     GET /leasing/export (CSV)

"3.1 Metrics to display" → GET /leasing/metrics endpoint
```

**The key skill:** Read the spec with database normalization in mind. When you see "each property has custom rules", think: "Is this a column (JSONB), a separate table, or an enum?" When you see "leads pipeline: contacted, toured, converted", think: "This is a CHECK constraint on a text column, not a separate table."

### 1.2 The Architecture Decision: One Number vs Many

The spec says: "The same phone number can serve multiple properties."

This led to the **Hybrid Architecture** decision:

| Approach | Pros | Cons |
|----------|------|------|
| One VAPI assistant, one number for ALL groups | Simple, zero provisioning | Can't scope searches to one group without complex routing |
| One assistant per property group, provisioned on signup | Full isolation, pg_id baked in | Requires auto-provisioning infra, VAPI API costs |
| **Hybrid (what we built)** | Existing groups use shared; new groups get dedicated | Two code paths to maintain |

The Hybrid was chosen because:
1. Existing test groups don't have dedicated numbers yet — forcing a migration would break them
2. New signups should get the better experience (dedicated number)
3. Backwards compatibility is preserved without a big-bang migration

**Lesson:** Architecture decisions are not just about what's technically best. They're about what's best *given the current state of the system and who's already using it.*

---

## Part 2 — FastAPI: Advanced Patterns

### 2.1 UploadFile — Accepting Files in FastAPI

The image upload endpoint uses FastAPI's `UploadFile` type, not `BaseModel`. Files can't be sent as JSON — they must come as `multipart/form-data`.

```python
from fastapi import UploadFile, File, Form

@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),       # the actual file bytes
    entity_type: Optional[str] = Form("misc"),  # text fields alongside a file use Form()
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
    svc: Client = Depends(get_service_db),
):
    contents = await file.read()   # read all bytes into memory
    ...
```

**Why `Form()` instead of `Query()`?** When sending files, the browser/client uses `multipart/form-data` encoding. Text parameters sent alongside a file must be declared as `Form()`, not `Query()` or in a `BaseModel`. `Query()` only reads from the URL (`?entity_type=foo`); `Form()` reads from the multipart body.

**`await file.read()`** — FastAPI's `UploadFile` is an async object. The file bytes are not read until you call `.read()`. This is intentional — if you never read the file (e.g., validation fails early), you save memory.

**File validation before touching storage:**

```python
# Validate MIME type first
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
if file.content_type not in ALLOWED_IMAGE_TYPES:
    raise HTTPException(400, detail=f"Invalid file type.")

# Read bytes THEN check size
contents = await file.read()
if len(contents) > 5 * 1024 * 1024:  # 5 MB
    raise HTTPException(400, detail=f"File too large.")
```

**Why check MIME type AND size?** MIME type catches the wrong file kind early (before reading the bytes). Size check must come after reading since you need the bytes to know the size. This order is the most efficient — you fail fast on type errors without reading potentially large files.

**Why not trust `Content-Length` for size checking?** Because `Content-Length` is a header set by the client and can be faked. The only reliable way to check size is to read the bytes and measure them.

### 2.2 Supabase Storage — Uploading Files

Supabase Storage is an S3-compatible file store. Files are uploaded from Python using the service-role client (which bypasses Storage policies):

```python
storage_path = f"{entity_type}/{uuid4()}.{ext}"   # e.g. "property/abc-123.jpg"

svc.storage.from_("Property Pics").upload(
    storage_path,
    contents,
    {"content-type": file.content_type},
)

public_url = svc.storage.from_("Property Pics").get_public_url(storage_path)
return {"url": public_url, "path": storage_path}
```

**Why `uuid4()` in the filename?** If two users upload `photo.jpg`, without a UUID, the second upload would overwrite the first. A UUID in the path makes every upload unique.

**Why not use the original filename?** Filenames from users are untrusted: they can contain path traversal characters (`../../etc/passwd`), spaces, or Unicode. Using a generated UUID + extracted extension is safe.

**Extension extraction:**
```python
ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
```
`rsplit(".", 1)` splits from the right, taking the last segment. This handles `photo.vacation.jpg` correctly — it returns `jpg`, not `vacation`.

**Why service role for uploads?** The Storage bucket has policies that may restrict uploads from non-authenticated clients. The service role bypasses all policies — your backend acts as a trusted intermediary, validates the upload, then pushes to storage with elevated permissions.

### 2.3 BackgroundTasks — Non-blocking Async Work

When a manager creates a new Property Group, the server auto-provisions a VAPI assistant and phone number. VAPI API calls take 2–5 seconds. You can't make the manager wait 5 seconds for a `POST /property-groups` response.

**FastAPI's `BackgroundTasks` solves this:**

```python
from fastapi import BackgroundTasks

@router.post("")
async def create_property_group(
    body: PropertyGroupCreate,
    background_tasks: BackgroundTasks,   # inject the task queue
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    # Insert row synchronously
    payload = {
        "name": body.name,
        "manager_id": user["sub"],
        "vapi_provisioning_status": "pending",   # mark as in-progress immediately
    }
    resp = db.table("properties_list").insert(payload).execute()
    group_id = str(resp.data[0]["id"])

    # Schedule provisioning to run AFTER the response is sent
    from app.services.vapi_provisioning import provision_vapi_for_property_group
    from app.db.session import get_service_db_direct
    background_tasks.add_task(
        provision_vapi_for_property_group,
        group_id,
        body.name,
        get_service_db_direct(),   # pass the DB client (background tasks don't have request context)
    )

    return resp.data[0]  # Returns immediately with status="pending"
```

**How it works:**
1. The endpoint runs synchronously up to `return`
2. FastAPI sends the HTTP response to the client immediately
3. After the response is sent, FastAPI runs the background task
4. The task runs in the same event loop — it's not a separate thread or process

**The status pattern:** Setting `vapi_provisioning_status = "pending"` before returning means the UI can show a spinner on the property card while provisioning runs. The task updates it to `"active"` on success or `"failed"` on error. The frontend can poll and update.

**When to use BackgroundTasks vs Celery/Redis:**
- `BackgroundTasks` — lightweight, in-process, good for < 30 second tasks, acceptable if they fail silently on server restart
- Celery + Redis — distributed, survives restarts, retries, monitoring. Use for critical operations (sending emails, payments) or long jobs (video processing)

For VAPI provisioning at MVP scale, BackgroundTasks is sufficient. A lost provisioning on server restart is recoverable via the `/provision-voice` retry endpoint.

### 2.4 StreamingResponse — Returning Files (CSV Export)

The `/leasing/export` endpoint returns a CSV file for download, not a JSON response.

```python
import csv
import io
from fastapi.responses import StreamingResponse

@router.get("/export")
async def export_leads(...):
    output = io.StringIO()     # in-memory text buffer
    writer = csv.writer(output)
    
    writer.writerow(["Name", "Phone", "Email", ...])  # headers
    for lead in leads:
        writer.writerow([lead.get("caller_name", ""), ...])
    
    output.seek(0)   # rewind the buffer to the beginning before reading
    
    return StreamingResponse(
        iter([output.getvalue()]),           # iterable of string chunks
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
```

**`io.StringIO()`** is an in-memory file-like object for text. Think of it as a `file` object that lives in RAM, not on disk. You write to it with `csv.writer`, then read all content back with `.getvalue()`.

**Why `iter([output.getvalue()])`?** `StreamingResponse` expects an iterable. Wrapping one string in a list (`[output.getvalue()]`) and calling `iter()` on it creates a minimal one-chunk iterator.

**`Content-Disposition: attachment; filename=leads.csv`** tells the browser to download the response as a file with that name, instead of displaying it inline.

**When to use StreamingResponse for large files:** If you had millions of leads, building the whole CSV in memory would use too much RAM. You'd instead `yield` rows in chunks:
```python
def generate_csv():
    yield "Name,Phone\n"
    for lead in leads:
        yield f"{lead['name']},{lead['phone']}\n"

return StreamingResponse(generate_csv(), media_type="text/csv")
```
For MVP size datasets (thousands of rows), the in-memory approach is fine.

### 2.5 Dual DB Clients in One Endpoint

Some endpoints need both the user-scoped client (for ownership checks via RLS) and the service-role client (for writes where RLS INSERT policies don't exist yet).

```python
@router.post("/listings", status_code=201)
async def create_listing(
    body: ListingCreate,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),   # RLS-enforced — verify flat ownership
    svc_db: Client = Depends(get_service_db),     # bypass RLS — write the new row
):
    # Step 1: Verify the flat belongs to this manager (RLS does this implicitly)
    flat_resp = db.table("flats").select("flat_number, building_id").eq("uuid", str(body.flat_uuid)).limit(1).execute()
    if not flat_resp.data:
        raise HTTPException(404, "Flat not found")   # RLS returned empty — not their flat

    # Step 2: Write the listing (service client, no RLS restriction)
    resp = svc_db.table("lease_listings").insert(payload).execute()
```

**Why not just use `get_service_db` everywhere?** Because RLS is a security layer. When you use the service client, you're explicitly bypassing it — which means you're responsible for ownership checks in code. The authenticated client lets the database enforce ownership automatically. Using both together gives you the best of both worlds: automatic ownership verification (RLS) + unrestricted writes (service role for tables with missing policies).

**The explicit `manager_id` filter pattern** — when you use `get_service_db` on a table with no RLS policies, you must filter manually:
```python
# RLS-based: automatic
db.table("lease_listings").select("*").execute()  # RLS adds WHERE manager_id = auth.uid()

# Service-based: manual filter required
svc_db.table("lease_listings").select("*").eq("manager_id", user["sub"]).execute()
```

### 2.6 Decimal → float Conversion

Pydantic V2 uses Python's `Decimal` type for `Decimal` fields. Supabase's Python SDK doesn't serialize `Decimal` natively — it throws a type error on insert.

**The fix pattern:**
```python
from decimal import Decimal

payload = body.model_dump(exclude_none=True)
# Convert any Decimal values to float before passing to Supabase
payload = {k: float(v) if isinstance(v, Decimal) else v for k, v in payload.items()}

svc_db.table("lease_listings").insert(payload).execute()
```

**Why use `Decimal` at all if it causes this?** Decimal is more accurate than float for money. `float(1.5)` might be `1.4999999999999998` in binary IEEE 754. `Decimal("1.5")` is exactly 1.5. Pydantic uses Decimal for financial fields to prevent rounding errors in validation. The conversion to float only happens at the DB boundary — all Python-level math stays precise.

**Where this happens:** Any Pydantic model with `Decimal` fields (like `monthly_rent: Decimal`) will produce `Decimal` values in `model_dump()`. Always apply this pattern when inserting or updating such models.

---

## Part 3 — VAPI Architecture Deep Dive

### 3.1 The Two-Agent System

| Agent | Name | Number | Scope |
|-------|------|--------|-------|
| Complaint Agent (Alex) | Global | One number for ALL property groups | Existing tenants calling about issues |
| Lease Agent | Property-specific | Shared number OR dedicated per group | Prospective tenants inquiring about listings |

### 3.2 Building VAPI Configs in Python

Instead of clicking through the VAPI dashboard to configure agents, we define them as Python functions that return dicts. This is the "infrastructure as code" pattern for AI agents.

```python
# backend/app/services/vapi_agent_config.py

def build_complaint_config(backend_url=BACKEND_URL):
    return {
        "name": "Alex — Complaint Agent",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
        "voice": {
            "provider": "cartesia",
            "voiceId": "...",
        },
        "firstMessage": "Hello! You've reached the property management office. How can I help you today?",
        "systemPrompt": SYSTEM_PROMPT,
        "tools": build_complaint_tools(backend_url),
    }

def build_complaint_tools(backend_url):
    return [
        {
            "type": "apiRequest",
            "name": "Verify_phone_number",
            "method": "GET",
            "url": f"{backend_url}/flats/verify-phone",
            "query": {
                "flat_number": "{{flat_number}}",      # VAPI template syntax
                "phone_number": "{{customer.number}}", # automatically extracted from call
            },
        },
        {
            "type": "function",
            "name": "submit_complaint",
            "parameters": {
                "type": "object",
                "required": ["flat_number", "description", "property_group_id"],
                "properties": {
                    "property_group_id": {
                        "type": "string",
                        "description": "The property_group_id returned by Verify_phone_number. ALWAYS pass this to submit_complaint.",
                    },
                    ...
                }
            }
        }
    ]
```

**Why Python dicts instead of VAPI dashboard JSON?**
- The config is version-controlled (in git)
- Different environments get different `backend_url` values automatically
- You can programmatically bake in `property_group_id` for per-group agents
- If you need to update 100 agents, you run a script — you don't click 100 times

**`{{customer.number}}` in VAPI** — VAPI uses double-brace template syntax for dynamic values extracted from the call. `customer.number` is the caller's phone number, captured by VAPI's infrastructure before any conversation starts. This is how the complaint agent verifies the caller without asking "what's your phone number?" — that would be awkward and easily faked.

### 3.3 The property_group_id Resolution Chain

The Complaint Agent receives a call from a tenant. The tenant gives their flat number. The agent calls `verify-phone`. The backend must figure out which property group this flat belongs to, so it can scope subsequent tool calls correctly.

The chain: **flat → building → properties_list (property group)**

```python
@router.get("/flats/verify-phone")
async def verify_phone(
    flat_number: str,
    phone_number: str,
    db: Client = Depends(get_service_db),   # must be service role — VAPI has no JWT
):
    # Step 1: Find the flat
    flat = db.table("flats").select("uuid, building_id, tenant_uuid").ilike("flat_number", flat_number.strip().upper()).limit(1).execute()
    if not flat.data:
        return {"status": "invalid", "datetime": now_ist(), "property_group_id": None}

    flat_row = flat.data[0]

    # Step 2: Walk up to the building
    building = db.table("buildings").select("property_id").eq("id", flat_row["building_id"]).limit(1).execute()

    # Step 3: property_id IS the property_group UUID
    property_group_id = str(building.data[0]["property_id"]) if building.data else None

    # Step 4: Verify phone matches the tenant
    tenant_uuid = flat_row.get("tenant_uuid")
    if not tenant_uuid:
        return {"status": "invalid", "datetime": now_ist(), "property_group_id": property_group_id}

    tenant = db.table("tenants").select("phone").eq("uuid", tenant_uuid).limit(1).execute()
    registered_phone = tenant.data[0]["phone"] if tenant.data else None

    if registered_phone != phone_number:
        return {"status": "invalid", "datetime": now_ist(), "property_group_id": property_group_id}

    return {"status": "valid", "datetime": now_ist(), "property_group_id": property_group_id}
```

**Why does this endpoint return `property_group_id` on invalid responses too?** Because VAPI reads the response and passes it to the agent. On a valid response, the agent uses `property_group_id` for subsequent tool calls. On invalid, the agent ends the call. Since the agent template references `property_group_id` in its system prompt, having it null on invalid responses is fine — the agent never reaches the code that uses it.

### 3.4 VAPI Endpoints Must Use service_role

**Bug #1 in this session:** `verify_phone` was using `get_db` (anon client). VAPI calls this endpoint with no user JWT — it's a machine-to-machine call. The anon client with RLS enabled returns 0 rows for any query on `flats`, because RLS requires `auth.uid()` to be set (which it isn't).

```python
# WRONG — anon client, RLS blocks all queries when no JWT is present
async def verify_phone(..., db: Client = Depends(get_db)):

# CORRECT — service role bypasses RLS
async def verify_phone(..., db: Client = Depends(get_service_db)):
```

**The rule:** Any endpoint called by VAPI, Stripe, Twilio, or any other external service (not a logged-in user) must use `get_service_db`. These endpoints have no user JWT. The anon client with RLS is designed for browser-based access where a logged-in user's JWT is passed. Without a JWT, RLS blocks everything.

**Bug #2:** Same issue in `voice_webhook`. The webhook is called by VAPI after a call ends — no user JWT. The anon client couldn't INSERT into `call_logs` because the RLS policy on that table requires a valid user. Fixed with the same one-line change.

**The decision matrix:**

| Caller | Has JWT? | Use |
|--------|----------|-----|
| Logged-in manager (browser) | Yes | `get_authenticated_db` |
| VAPI webhook | No | `get_service_db` |
| Stripe webhook | No | `get_service_db` |
| Server-side background task | No | `get_service_db` |

### 3.5 The Lease Agent Tool Flow

When a prospective tenant calls the lease number:

```
Caller: "Hi, I'm calling about the 2BHK at 45 Park Street"
        ↓
VAPI calls GET /leasing/find-listing?query=45+Park+Street&property_group_id=<baked-in>
        ↓
Backend queries lease_listings WHERE flat_number ILIKE '%45 Park Street%'
  → fallback: WHERE title ILIKE '%45 Park Street%'
        ↓
Returns: { found: true, listing_uuid: "abc", bedrooms: 2, monthly_rent: 25000, custom_rules: "..." }
        ↓
Agent: "Great, I found the 2BHK at 45 Park Street, available at ₹25,000/month. Let me ask a few questions."
        ↓
[Agent asks qualifying questions based on custom_rules]
        ↓
VAPI calls POST /voice/lease-lead-webhook (submit_lease_lead function tool)
        ↓
Backend creates lease_leads row
```

**Why return `custom_rules` as a JSON string instead of a structured object?**

```python
return {
    ...
    "custom_rules": json.dumps(listing.get("custom_rules") or {}),
}
```

Because VAPI's `apiRequest` tool returns the response to the agent as a string it reads. JSON-embedded-in-a-string is harder for the agent to misparse than a nested object. The system prompt instructs the agent: "Parse the custom_rules JSON string to determine which qualifying questions to ask." This is a known VAPI pattern — the agent reads strings, not nested objects.

### 3.6 The Fallback Query Pattern

`find_listing` uses a two-phase query: first try the primary match, then fall back to a softer match.

```python
# Primary: match by flat_number
results = q.ilike("flat_number", f"%{query}%").limit(1).execute()

if not results.data:
    # Fallback: match by listing title
    fallback_q = (
        db.table("lease_listings")
        .select(...)
        .eq("is_active", True)
        .ilike("title", f"%{query}%")   # ← different column
        .limit(1)
    )
    if property_group_id:
        fallback_q = fallback_q.eq("property_group_id", property_group_id)  # ← must re-apply filter!
    results = fallback_q.execute()
```

**Bug #5 was found here:** The original fallback query forgot to re-apply `property_group_id`. A caller on Group A's dedicated line could match a listing from Group B via the title search — a data isolation bug. The fix: always re-apply the filter in the fallback branch.

**The general rule:** Every branch of a query that touches user data must apply the same ownership/scope filters. If your primary query has `.eq("property_group_id", pg_id)`, every fallback must also have it.

---

## Part 4 — Database Design

### 4.1 JSONB Columns for Variable-Length Data

The `custom_rules` column is JSONB:

```sql
custom_rules JSONB DEFAULT '{}'
```

With Pydantic:
```python
class CustomRules(BaseModel):
    max_occupants: Optional[int] = None
    income_required: Optional[bool] = False
    pets_allowed: Optional[str] = "no"       # "yes", "no", "cats_only", "dogs_only"
    vegetarian_only: Optional[bool] = False
    lease_term_months: Optional[int] = 11
    custom_question: Optional[str] = ""
```

**Why JSONB instead of separate columns for each rule?** Because rules evolve. Tomorrow, the product might add "parking_included" or "balcony_required". With JSONB, you add a field to the Pydantic model — no database migration needed. With separate columns, every new rule requires an `ALTER TABLE ADD COLUMN`.

**When NOT to use JSONB:** When you need to query or filter by the field. You can query JSONB in PostgreSQL (`custom_rules->>'pets_allowed' = 'yes'`), but it's slower and less readable than a plain column with an index. If you needed to find "all listings that allow pets", a dedicated `pets_allowed TEXT` column with an index would be better.

**The rule of thumb:** JSONB for config/settings/flexible data that you read but rarely filter by. Dedicated columns for data you filter, sort, or aggregate on.

### 4.2 CHECK Constraints on Status Fields

The `lease_leads.qualification_status` column uses a CHECK constraint to enforce valid values:

```sql
qualification_status TEXT NOT NULL DEFAULT 'unmatched'
  CHECK (qualification_status IN (
    'qualified','not_qualified','unmatched','contacted','toured','converted','lost'
  ))
```

**Why CHECK constraint instead of letting the application validate?** The database is the last line of defense. If there's a bug in the API that sends an invalid status (typo, missing validation), the CHECK constraint prevents garbage from entering the database. You'd get a PostgreSQL error rather than silently stored bad data.

**The two-tier validation pattern this project uses:**
1. **Pydantic** validates incoming API requests — gives a 422 error with a message to the client
2. **PostgreSQL CHECK** validates at the database level — catches anything that bypasses Pydantic

Additionally, the API enforces which values a *manager* is allowed to set:
```python
_MANAGER_EDITABLE_STATUSES = {"contacted", "toured", "converted", "lost"}

if "qualification_status" in payload and payload["qualification_status"] not in _MANAGER_EDITABLE_STATUSES:
    raise HTTPException(400, detail="Managers can only set status to: contacted, toured, converted, lost")
```

**Why this split?** Voice sets `qualified/not_qualified/unmatched` — those represent the outcome of the AI conversation. Managers drive the pipeline forward with `contacted/toured/converted/lost`. Managers should not be able to retroactively change what the AI determined. This is a business rule enforced in code, above the database layer.

### 4.3 Partial Indexes for Active-only Queries

```sql
CREATE INDEX IF NOT EXISTS idx_ll_active ON lease_listings(is_active) WHERE is_active = true;
```

**What is a partial index?** A normal index on `is_active` would index both `true` and `false` rows. A partial index only indexes rows where the condition is met. Since VAPI's listing search always queries `WHERE is_active = true`, the partial index is much smaller (only active listings) and faster to scan.

**When to use partial indexes:**
- When a query always filters by the same condition
- When the indexed subset is much smaller than the full table (e.g., 5% active listings, 95% archived)

If you had 10,000 listings but only 200 active ones, a partial index on active listings would be ~50x smaller than a full index on the column.

### 4.4 The RLS Gap for New Tables

When you create a new table, PostgreSQL enables RLS but creates no policies. The result: all access is blocked for non-service users, even authenticated ones.

**What we found after creating `lease_listings` and `lease_leads`:**
- The GET endpoints (using `get_authenticated_db`) returned 0 rows
- The POST endpoint threw `new row violates row-level security policy`
- The service client worked fine

**Fix (migration 011):**
```sql
CREATE POLICY "managers can insert own properties"
ON properties_list
FOR INSERT
TO authenticated
WITH CHECK (manager_id = auth.uid());

CREATE POLICY "managers can update own properties"
ON properties_list
FOR UPDATE
TO authenticated
USING (manager_id = auth.uid());

CREATE POLICY "managers can delete own properties"
ON properties_list
FOR DELETE
TO authenticated
USING (manager_id = auth.uid());
```

**`USING` vs `WITH CHECK`:**
- `USING` — applied to rows being read or modified (SELECT, UPDATE, DELETE). "Which rows can this user access?"
- `WITH CHECK` — applied to new row values (INSERT, UPDATE). "Can this user write this specific value?"

For INSERT: only `WITH CHECK` applies (there's no existing row to check).
For UPDATE: both apply — `USING` selects which rows can be updated, `WITH CHECK` validates the new values.
For SELECT/DELETE: only `USING` applies.

**A common mistake:** Writing a SELECT-only policy and wondering why INSERT fails. Always create separate policies for each operation (INSERT, UPDATE, DELETE, SELECT) unless you use `FOR ALL`.

**Workaround used for `lease_listings`/`lease_leads` (no RLS policies yet):**
Switch all manager operations to `get_service_db`, and manually filter by `manager_id = user["sub"]`. This is equivalent to what RLS would do, but done in application code. The goal is the same: managers only see and modify their own data.

---

## Part 5 — React: Building the Leasing Dashboard

### 5.1 The ImageUploadField Component Pattern

`ImageUploadField.jsx` is a reusable component for drag-and-drop image upload. It encapsulates:
1. Client-side validation (type + size)
2. Local preview (instant, before upload completes)
3. Network upload to backend
4. Error state and recovery
5. Upload-in-progress state (disables parent submit button)

**The `onUploadStart` prop pattern:**

```jsx
// Parent component
const [imageUploading, setImageUploading] = useState(false);
const [imageUrl, setImageUrl] = useState('');

<ImageUploadField
    onUploadStart={() => setImageUploading(true)}   // parent disables Submit
    onUploadComplete={(url) => {
        setImageUrl(url);
        setImageUploading(false);   // parent re-enables Submit
    }}
/>

<button disabled={loading || imageUploading}>  {/* ← gated on both */}
    Save
</button>
```

**Why two callbacks?** `onUploadComplete` fires when the upload finishes (success or error). But when the upload starts, the parent needs to know immediately so it can disable the Save button. If the user clicks Save while the image is still uploading, the form would submit with an empty URL. The `onUploadStart` callback closes this race condition.

**The blob URL pattern for instant preview:**
```jsx
const localUrl = URL.createObjectURL(file);  // creates a temporary browser URL
setPreview(localUrl);                         // show preview immediately

// ... async upload ...
const { url } = await uploadImage(file, entityType);
setPreview(url);   // replace blob URL with permanent Supabase URL
```

`URL.createObjectURL` creates a browser-local URL like `blob:http://localhost:5173/abc-123`. It only exists in the current browser tab's memory. The user sees the image immediately without waiting for the upload. Once the upload completes, the blob URL is replaced with the real Supabase URL.

**What happens on upload failure:**
```jsx
} catch (err) {
    setError(err.message || 'Upload failed. Please try again.');
    setPreview(currentImageUrl || null);   // revert to original
    onUploadComplete('');                  // clear URL in parent
}
```
The preview reverts to whatever was there before. The parent is told the URL is empty, so if the user submits now, no broken URL is saved.

### 5.2 Drag-and-Drop Implementation

```jsx
<div
    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
    onDragLeave={() => setIsDragging(false)}
    onDrop={handleDrop}
>
```

**`e.preventDefault()` on `dragover`** is mandatory. Without it, the browser interprets the drop as "open this file in a new tab" (default behavior for dropped files). Preventing the default makes the div a valid drop target.

**`onDragLeave`** — fires when the cursor leaves the drop zone. Reset `isDragging` to false to remove the visual highlight.

**The drop handler:**
```jsx
const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];   // files come from e.dataTransfer, not e.target
    if (file) processFile(file);
};
```

Files in a drop event are in `e.dataTransfer.files`, not `e.target.files` (which is for `<input type="file">`). This is the most common confusion with drag-and-drop.

### 5.3 Parallel Data Loading in useEffect

`LeasingTab.jsx` loads three endpoints in parallel:

```jsx
const load = useCallback(async () => {
    setLoading(true);
    try {
        const [listings, leads, metrics] = await Promise.all([
            getListings(),
            getLeaseLeads(),
            getLeasingMetrics(),
        ]);
        setListings(listings);
        setLeads(leads);
        setMetrics(metrics);
    } catch (e) {
        console.error('Leasing load error', e);
    } finally {
        setLoading(false);
    }
}, []);

useEffect(() => { load(); }, [load]);
```

**`Promise.all` vs sequential `await`:**
```js
// Sequential — 3 seconds (1 + 1 + 1)
const listings = await getListings();   // wait 1s
const leads = await getLeaseLeads();    // then wait 1s
const metrics = await getLeasingMetrics(); // then wait 1s

// Parallel — ~1 second (all start simultaneously)
const [listings, leads, metrics] = await Promise.all([...]);
```

`Promise.all` starts all three requests at the same time and waits for all to complete. If any one fails, the entire `Promise.all` rejects (caught by `try/catch`). Use this pattern whenever you have independent API calls that don't depend on each other's results.

**`useCallback` for the load function** — prevents the `useEffect` dependency array from triggering infinite re-renders. Without `useCallback`, a new `load` function is created on every render, which triggers the effect, which calls `setLoading`, which triggers a re-render, which creates a new `load`... infinite loop. `useCallback` memoizes the function so its reference is stable.

### 5.4 Status Badge Colors as a Constant Map

```jsx
const STATUS_BADGE = {
    qualified:     'bg-green-500/10 text-green-500',
    not_qualified: 'bg-red-500/10 text-red-500',
    unmatched:     'bg-yellow-500/10 text-yellow-600',
    contacted:     'bg-blue-500/10 text-blue-500',
    toured:        'bg-purple-500/10 text-purple-500',
    converted:     'bg-emerald-500/10 text-emerald-500',
    lost:          'bg-muted text-muted-foreground',
};

// Usage
<span className={`px-2 py-0.5 rounded-full text-xs ${STATUS_BADGE[lead.qualification_status] || 'bg-secondary'}`}>
    {lead.qualification_status}
</span>
```

**Why a constant map instead of a switch/if-else?** The map is a data structure — you can inspect it, iterate over it, and test it. An `if/else` chain is harder to maintain and harder to tell if all cases are covered. Adding a new status means adding one line to the map, not adding a new `else if` in multiple places.

**The fallback `|| 'bg-secondary'`** handles unknown statuses gracefully — if a new status arrives from the API that isn't in the map, it gets a neutral color instead of `className=undefined` (which renders no class, potentially breaking layout).

---

## Part 6 — Testing: How to Find Bugs Before Users Do

### 6.1 The Test Script Pattern

The voice agent tests are written as bash scripts (`test_complaint_endpoints.sh`, `test_leasing_endpoints.sh`). Each test:
1. Makes an HTTP request with `curl`
2. Parses the JSON response with `jq`
3. Asserts the expected value
4. Prints PASS or FAIL with the actual value

```bash
# Example test structure
echo "=== A1: verify-phone — valid phone ==="
RESPONSE=$(curl -s -X GET \
  "${BASE_URL}/flats/verify-phone?flat_number=${FLAT_NUMBER}&phone_number=${TENANT_PHONE}")

STATUS=$(echo "$RESPONSE" | jq -r '.status')
PG_ID=$(echo "$RESPONSE" | jq -r '.property_group_id')

assert_eq "A1 - status=valid"               "$STATUS"  "valid"
assert_ne "A1 - property_group_id non-null" "$PG_ID"   "null"
```

```bash
# The assert helper functions
assert_eq() {
    local label="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "[PASS] $label"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $label — expected '$expected', got '$actual'"
        FAIL=$((FAIL + 1))
    fi
}
```

**Why bash scripts instead of pytest or pytest-httpx?** Because these are integration tests against a live running server. pytest is great for unit tests. For "does this endpoint return the right shape when a real DB is behind it", bash + curl is faster to write and easier to share with non-Python teammates. The output is also very readable in logs.

### 6.2 The Four Types of Bugs Found

In the first run, 7 tests failed and 2 crashed. The bugs fell into four categories:

**Category 1 — Infrastructure bugs (the hardest to anticipate)**

Bug #1 and #2 — Using the wrong DB client on VAPI endpoints. The code was logically correct; the architecture assumption was wrong. VAPI makes unauthenticated requests. Anon client + RLS = 0 rows. Fix: service role for all machine-to-machine endpoints.

**Lesson:** When you write a new endpoint, ask: "Who calls this? Do they have a JWT?" If not: service role.

**Category 2 — Platform-specific bugs (Windows)**

Bug #3 — Unicode `✓` character crashed the server on Windows. The production Linux server would have been fine. This is a development environment bug.

```python
# Before (crashes on Windows terminals with cp1252 encoding)
print(f" ✓ User confirmed")

# After
print(f" [OK] User confirmed")
```

**Lesson:** Don't use Unicode characters in server-side `print()` statements. Logs should be ASCII-safe. The terminal that reads the logs might not be UTF-8. This is a common trap when developing on macOS (UTF-8 default) or Linux and deploying to Windows CI runners.

**Category 3 — Logic bugs in query scoping**

Bug #5 — Fallback query in `find_listing` didn't apply the `property_group_id` filter. Easy to miss because the primary query had it. The fallback was a copy-paste job without re-applying the filter.

**Lesson:** Every branch that touches user data needs the same scope filters. A good rule: after writing a query, ask "what happens if I'm a different manager?" Would this query return data belonging to someone else?

**Category 4 — Data type bugs**

Bugs #6 and #7 — Pydantic's `Decimal` type (used for `monthly_rent`) doesn't serialize to JSON automatically. Supabase SDK threw `TypeError: Object of type Decimal is not JSON serializable`.

**Lesson:** When Pydantic models contain `Decimal` fields, always convert to `float` before passing to Supabase. Make it a habit: after `body.model_dump()`, apply the Decimal-to-float conversion.

### 6.3 Reading a Test Report

The session produced a formal test report (`TEST_REPORT_VOICE_AGENTS.md`). Here's how to read it:

```
Phase | Total Assertions | Passed | Failed
──────────────────────────────────────────
A     | 18               | 18     | 0      ← All complaint endpoints pass
B     | 20               | 20     | 0      ← All lease VAPI tools pass  
C     | 17               | 17     | 0      ← All manager CRUD passes
Total | 55               | 55     | 0
```

A "SKIP" in a test report is not the same as "PASS". It means "this test was not run, usually because a dependency failed." In the first run, C4 through C10 were skipped because C3 failed (couldn't create a listing). When C3 was fixed, the cascade resolved and all tests ran.

**Data setup failures vs code bugs:** C3 originally failed not because the code was wrong, but because the test account (`testmanager1@gmail.com`) had no flats. The fix was to create test data (property group, building, flat, tenant, listing) under that account. When the code correctly raises a 404 for "flat not found", that's correct behavior — it means RLS is working.

### 6.4 The Re-run Checklist Pattern

After fixing bugs, a systematic re-run checklist ensures every fix was applied:

```markdown
## Re-run Checklist — COMPLETED

- [x] Bug #1 — flats.py: get_db → get_service_db in verify_phone
- [x] Bug #2 — voice.py: get_db → get_service_db in voice_webhook
- [x] Bug #3 — voice.py: Unicode → ASCII in all print statements
- [x] Bug #4 — test script: EXISTING_LISTING_UUID default added
- [x] Bug #5 — leasing.py find_listing: fallback applies property_group_id filter
- [x] Bug #6/7 — leasing.py: Decimal → float in INSERT and PATCH
- [x] Bug #8 — leasing.py: switched to get_service_db + manual manager_id filter
- [x] Bug #9 — property_groups.py: manager_id added to CREATE payload
- [x] Data setup — created test data under testmanager1@gmail.com
```

**Why write this down?** When you have 9 bugs to fix across multiple files, you will miss one. The checklist converts "I think I got everything" into "I have a written record that every item was addressed." It also serves as documentation for whoever runs the tests next.

---

## Part 7 — Full File Change Map

### New Backend Files

```
backend/app/routes/leasing.py
  GET  /leasing/find-listing        ← VAPI tool: find listing by query
  GET  /leasing/search              ← VAPI tool: search by bedrooms/budget
  GET  /leasing/listings            ← Manager: list all listings
  POST /leasing/listings            ← Manager: create listing
  PATCH /leasing/listings/{uuid}    ← Manager: update listing
  DELETE /leasing/listings/{uuid}   ← Manager: delete listing
  GET  /leasing/leads               ← Manager: list leads (filterable)
  PATCH /leasing/leads/{uuid}       ← Manager: update lead status/notes
  DELETE /leasing/leads/{uuid}      ← Manager: delete lead
  GET  /leasing/metrics             ← Manager: aggregated stats
  GET  /leasing/export              ← Manager: CSV export of leads

backend/app/schemas/leasing.py
  CustomRules, ListingCreate, ListingUpdate, ListingResponse
  LeadUpdate, LeadResponse

backend/app/services/vapi_provisioning.py
  provision_vapi_for_property_group() — BackgroundTask for new groups

backend/migrations/010_voice_agents.sql
  ALTER TABLE properties_list — adds 4 VAPI columns
  CREATE TABLE lease_listings
  CREATE TABLE lease_leads

backend/migrations/011_properties_list_rls.sql
  INSERT / UPDATE / DELETE policies for properties_list
```

### Modified Backend Files

```
backend/app/routes/flats.py
  verify_phone: get_db → get_service_db (Bug #1)
  verify_phone: now returns property_group_id (flat → building → properties_list chain)

backend/app/routes/voice.py
  voice_webhook: get_db → get_service_db (Bug #2)
  voice_webhook: Unicode → ASCII in all print statements (Bug #3)
  + POST /voice/lease-lead-webhook: creates lease_leads from VAPI function tool call

backend/app/services/vapi_agent_config.py
  + build_complaint_config() — new complaint agent (multi-manager, returns property_group_id)
  + build_complaint_tools() — complaint agent tool definitions
  + _build_lease_tools() — shared lease tool definitions
  + build_lease_config_shared() — shared lease assistant config
  + build_lease_config(pg_id, pg_name) — per-group lease assistant config
  Legacy build_assistant_config() / build_tools() kept untouched

backend/app/routes/property_groups.py
  create_property_group: vapi_provisioning_status = "pending" on creation
  create_property_group: fires provision_vapi_for_property_group as BackgroundTask
  create_property_group: manager_id added to payload (Bug #9)
  + POST /property-groups/{id}/provision-voice — manual retry endpoint
  PropertyGroupResponse: + vapi_provisioning_status, + vapi_phone_number

backend/app/schemas/flat.py
  FlatVerifyPhoneResponse: + property_group_id: Optional[str]

backend/app/config.py
  + VAPI_COMPLAINT_ASSISTANT_ID
  + VAPI_COMPLAINT_NUMBER_ID
  + VAPI_SHARED_LEASE_ASSISTANT_ID
  + VAPI_SHARED_LEASE_NUMBER_ID

backend/app/main.py
  + import leasing
  + app.include_router(leasing.router)

backend/app/routes/upload.py
  entity_type: changed from property-only to support 'tenant_document'
  Dual bucket routing: 'Property Pics' for images, 'Tenant_docs' for PDFs
  svc (service client) used for storage uploads
```

### New Frontend Files

```
frontend/src/components/LeasingTab.jsx
  Metrics cards (total calls, qualified, not qualified, qualification rate)
  Listings grid with edit/delete
  Leads table with status filters and status badge colors
  AddListingModal integration
  LeadDetailModal integration

frontend/src/components/AddListingModal.jsx
  Create/edit listing with collapsible custom qualifying rules section
  Flat selector, rent, available date, description

frontend/src/components/LeadDetailModal.jsx
  Lead contact info, preferences, qualifying answers
  Pipeline status management (contacted → toured → converted / lost)
  Manager notes field
```

### Modified Frontend Files

```
frontend/src/services/apiService.js
  + getListings, createListing, updateListing, deleteListing
  + getLeaseLeads, updateLead, deleteLead
  + getLeasingMetrics, exportLeads

frontend/src/components/Sidebar.jsx
  + { id: 'leasing', icon: KeyRound, label: 'Leasing' }

frontend/src/App.jsx
  + LeasingTab lazy import
  + currentView === 'leasing' → <LeasingTab />

frontend/src/components/ImageUploadField.jsx
  + onUploadStart prop (notify parent when upload begins)
  Simplified from previous version (removed unnecessary base64 logic)

frontend/src/components/TenantProfile.jsx
  Image upload for tenant documents (entity_type='tenant_document')
```

---

## Part 8 — DB Migrations to Run

### Migration 010 — Voice Agent Tables

Run in the **Supabase SQL editor** (`backend/migrations/010_voice_agents.sql`):

```sql
-- 1. Adds 4 columns to properties_list for VAPI provisioning state
ALTER TABLE properties_list
  ADD COLUMN IF NOT EXISTS vapi_lease_assistant_id  TEXT,
  ADD COLUMN IF NOT EXISTS vapi_phone_number_id     TEXT,
  ADD COLUMN IF NOT EXISTS vapi_phone_number        TEXT,
  ADD COLUMN IF NOT EXISTS vapi_provisioning_status TEXT DEFAULT 'not_applicable'
    CHECK (vapi_provisioning_status IN ('not_applicable','pending','active','failed'));

-- 2. lease_listings — one row per unit available for rent
CREATE TABLE IF NOT EXISTS lease_listings (
  id                SERIAL PRIMARY KEY,
  uuid              UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
  property_group_id UUID NOT NULL REFERENCES properties_list(id),
  flat_uuid         UUID NOT NULL REFERENCES flats(uuid),
  flat_number       TEXT NOT NULL,
  title             TEXT,
  monthly_rent      NUMERIC NOT NULL,
  description       TEXT,
  available_from    DATE,
  photo_urls        TEXT[]  DEFAULT '{}',
  is_active         BOOLEAN DEFAULT true,
  custom_rules      JSONB   DEFAULT '{}',
  manager_id        UUID,
  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now()
);

-- 3. lease_leads — one row per inbound call from a prospective tenant
CREATE TABLE IF NOT EXISTS lease_leads (
  id                    SERIAL PRIMARY KEY,
  uuid                  UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
  property_group_id     UUID REFERENCES properties_list(id),
  listing_uuid          UUID REFERENCES lease_listings(uuid),
  caller_name           TEXT NOT NULL,
  phone                 TEXT NOT NULL,
  email                 TEXT,
  bedrooms              INTEGER,
  budget_max            NUMERIC,
  move_in_timeline      TEXT,
  occupants             INTEGER,
  floor_preference      TEXT,
  qualification_status  TEXT NOT NULL DEFAULT 'unmatched'
    CHECK (qualification_status IN (
      'qualified','not_qualified','unmatched','contacted','toured','converted','lost'
    )),
  disqualifying_reason  TEXT,
  qualifying_answers    JSONB    DEFAULT '{}',
  notes                 TEXT,
  source                TEXT NOT NULL DEFAULT 'voice',
  call_id               TEXT,
  call_duration_seconds INTEGER,
  manager_notes         TEXT,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
);
```

### Migration 011 — RLS Write Policies for properties_list

Run after 010 (`backend/migrations/011_properties_list_rls.sql`):

```sql
CREATE POLICY "managers can insert own properties"
ON properties_list FOR INSERT TO authenticated
WITH CHECK (manager_id = auth.uid());

CREATE POLICY "managers can update own properties"
ON properties_list FOR UPDATE TO authenticated
USING (manager_id = auth.uid());

CREATE POLICY "managers can delete own properties"
ON properties_list FOR DELETE TO authenticated
USING (manager_id = auth.uid());
```

### Environment Variables to Add

```env
# In .env and in hosting platform (Render) environment variables
VAPI_COMPLAINT_ASSISTANT_ID=   # set after manual VAPI setup
VAPI_COMPLAINT_NUMBER_ID=      # set after manual VAPI setup
VAPI_SHARED_LEASE_ASSISTANT_ID=
VAPI_SHARED_LEASE_NUMBER_ID=
```

---

## Part 9 — Manual VAPI Setup Steps

After the code is deployed:

### 9.1 Generate and Deploy the Complaint Agent Config

```python
# Run in a Python shell from the backend directory
from app.services.vapi_agent_config import build_complaint_config
import json
print(json.dumps(build_complaint_config(), indent=2))
```

1. Copy the output
2. VAPI Dashboard → Assistants → Create → paste as JSON
3. Copy the assistant ID → add `VAPI_COMPLAINT_ASSISTANT_ID=<id>` to `.env` and Render
4. Phone Numbers → Buy a number → Link to this assistant
5. Add `VAPI_COMPLAINT_NUMBER_ID=<phone number id>` to `.env` and Render

### 9.2 Generate and Deploy the Shared Lease Agent Config

```python
from app.services.vapi_agent_config import build_lease_config_shared
import json
print(json.dumps(build_lease_config_shared(), indent=2))
```

1. Same process — create assistant, get ID
2. Import a Twilio number into VAPI (requires Twilio credentials in VAPI Settings)
3. Link the number to the shared lease assistant
4. Add `VAPI_SHARED_LEASE_ASSISTANT_ID` and `VAPI_SHARED_LEASE_NUMBER_ID` to `.env` and Render

### 9.3 New Property Groups Auto-Provisioned

After both env vars are set and the backend is restarted, any new `POST /property-groups` call will:
1. Set `vapi_provisioning_status = 'pending'` immediately
2. Trigger a BackgroundTask that calls the VAPI API
3. Create a lease assistant for the group, buy a phone number, link them
4. Update `vapi_provisioning_status = 'active'` and store the phone number in `properties_list`

The property card in the UI shows the phone number once provisioning completes.

---

## Part 10 — Key Concepts Summary

| Concept | One-line explanation |
|---------|---------------------|
| `UploadFile = File(...)` | FastAPI's way to receive multipart file uploads; read with `await file.read()` |
| `Form()` vs `Query()` | When sending files, text params must use `Form()` — they're in the multipart body, not the URL |
| `io.StringIO` | In-memory text buffer — write CSV rows to it, then read back as a string for `StreamingResponse` |
| `StreamingResponse` | Returns a file download; set `Content-Disposition: attachment` to trigger browser download |
| `BackgroundTasks` | FastAPI feature: schedule work to run after the HTTP response is sent — keeps API fast |
| VAPI `apiRequest` tool | VAPI calls your backend URL; use `{{variable}}` syntax for dynamic values in the request |
| `get_service_db` on VAPI routes | All machine-to-machine endpoints (VAPI, Stripe, Twilio) have no JWT — must use service role |
| property_group_id resolution | flat → building.property_id → properties_list — walk the FK chain to find the group |
| `Decimal` → `float` | Pydantic Decimal is not JSON-serializable; convert with `float(v) if isinstance(v, Decimal) else v` |
| JSONB for variable config | Use JSONB for settings/rules that evolve; use plain columns for data you filter/sort on |
| Partial index | Index only a subset of rows (e.g., `WHERE is_active = true`); faster and smaller than full index |
| `WITH CHECK` vs `USING` | RLS: `USING` gates row access; `WITH CHECK` gates new values being written |
| Fallback query scoping | Every branch of a multi-query fallback must re-apply the same ownership/scope filters |
| Status map as a constant | `{status: 'tailwind-class'}` dict is cleaner and more maintainable than if/else chains |
| `Promise.all` | Start multiple async calls simultaneously; waits for all — 3x faster than sequential `await` |
| `URL.createObjectURL` | Creates an in-browser blob URL for instant image preview before the upload completes |
| `onUploadStart` prop | Notify parent when upload begins so it can disable the Submit button (prevents race condition) |
| Test script bash pattern | `curl` + `jq` + `assert_eq` — lightweight integration tests against a live server |
| Four bug categories | Infrastructure (wrong client), platform (Windows encoding), logic (missing filter), type (Decimal) |

---

## Part 11 — Resources to Learn More

### FastAPI
- [FastAPI File Upload](https://fastapi.tiangolo.com/tutorial/request-files/) — `UploadFile`, `File()`, `Form()`
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) — how `BackgroundTasks` works
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse) — streaming large responses

### Supabase / PostgreSQL
- [Supabase Storage Python SDK](https://supabase.com/docs/reference/python/storage-from-upload) — `.upload()`, `.get_public_url()`
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html) — when to use JSONB vs TEXT
- [PostgreSQL Partial Indexes](https://www.postgresql.org/docs/current/indexes-partial.html) — indexes on subsets of rows
- [PostgreSQL RLS USING vs WITH CHECK](https://www.postgresql.org/docs/current/sql-createpolicy.html) — policy expression types
- [PostgreSQL CHECK Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-CHECK-CONSTRAINTS) — database-level validation

### Python
- [Python Decimal module](https://docs.python.org/3/library/decimal.html) — why Decimal is more precise than float for money
- [Python io.StringIO](https://docs.python.org/3/library/io.html#io.StringIO) — in-memory text buffers
- [Python csv module](https://docs.python.org/3/library/csv.html) — writing CSV files

### React
- [URL.createObjectURL (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/URL/createObjectURL) — local blob URL for file previews
- [HTML5 Drag and Drop API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API) — `dragover`, `drop`, `dataTransfer.files`
- [Promise.all (MDN)](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/all) — parallel async calls
- [useCallback (React docs)](https://react.dev/reference/react/useCallback) — memoizing functions to prevent infinite effect loops

### VAPI
- [VAPI apiRequest tool](https://docs.vapi.ai/tools/api-request) — how VAPI calls your backend during a call
- [VAPI function tools](https://docs.vapi.ai/tools/function-call) — define custom functions the LLM can call
- [VAPI system prompt variables](https://docs.vapi.ai/customization/custom-llm/system-prompt-and-tools) — `{{customer.number}}` and template syntax

### Testing
- [jq manual](https://jqlang.github.io/jq/manual/) — JSON parsing in shell scripts
- [curl reference](https://curl.se/docs/manpage.html) — making HTTP requests from the terminal
- [bash set -euo pipefail](https://www.gnu.org/software/bash/manual/bash.html#The-Set-Builtin) — why this is in every bash test script

---

## Appendix — Diagnosing Common Bugs in This Codebase

### "VAPI endpoint returns empty/invalid even when data exists"

**Almost always:** the endpoint uses `get_db` (anon client) instead of `get_service_db`. VAPI calls have no user JWT — the anon client returns 0 rows because RLS sees no authenticated user.

Check: find the endpoint in the router. Look at its `Depends()` for DB. If it says `get_db` or `get_authenticated_db`, change it to `get_service_db`.

### "Can't INSERT to a new table I just created"

RLS is enabled on all new tables by default, and no INSERT policy exists. All inserts are blocked.

Fix: either add an RLS INSERT policy (see migration 011 pattern), or switch to `get_service_db` with manual `manager_id` filtering in your endpoint.

### "Supabase insert fails with 'Object of type Decimal is not JSON serializable'"

A Pydantic model has a `Decimal` field. After `body.model_dump()`, the dict contains `Decimal` objects. Supabase SDK can't serialize them.

Fix: apply `{k: float(v) if isinstance(v, Decimal) else v for k, v in payload.items()}` before the `.insert()` call.

### "Fallback query returns data from the wrong property group"

The fallback branch forgot to re-apply `.eq("property_group_id", property_group_id)`. Every branch that queries user data must include all scope filters.

### "Image upload works but the URL saved in the DB is empty"

The parent component submits the form before the upload completes (race condition). Add `onUploadStart={() => setUploading(true)}` to `ImageUploadField` and gate the submit button on `uploading`.

### "Works on Mac/Linux, crashes on Windows with UnicodeEncodeError"

A `print()` statement contains non-ASCII characters (emoji, special symbols). Windows console defaults to cp1252 encoding. Fix: use ASCII-only characters in all server-side print/log statements.
