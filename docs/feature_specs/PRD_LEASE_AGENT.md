# PRD: Lease Agent — AI Voice Leasing + Leasing Dashboard Tab

**Date:** 2026-05-20
**Author:** Pranav Raj
**Status:** Draft v3 — Hybrid Architecture (Shared Number for Existing Groups + Auto-Provisioned for New)  

---

## 1. Overview

### 1.1 Problem

Property managers have vacant units but no automated way to handle inbound leasing inquiries over the phone. Currently, when someone calls asking about available properties, the voice agent has no tools to help — it can only handle existing-tenant complaints. Managers lose potential leads because there's no system to capture caller info, qualify them against property-specific criteria, match them to available units, or follow up.

### 1.2 Vision

**Two connected pieces:**

1. **Voice Lease Agent** — Anyone (not a tenant) can call and inquire about properties for rent. The agent identifies which listing they want, runs property-specific qualifying questions, determines QUALIFIED or NOT QUALIFIED, and captures the caller as a lead. If the caller doesn't pass for one unit, the agent checks alternatives within the same PropertyGroup.

2. **Leasing Dashboard Tab** — A new tab in the sidebar where managers:
   - Configure available listings with photos, rent, and per-listing qualifying rules
   - See all captured leads with qualification status, answers, and pipeline tracking
   - View aggregate metrics: call volume, qualification rate, estimated time saved
   - Export leads to CSV

### 1.3 Goals

| Goal | Metric |
|------|--------|
| Capture 100% of leasing inquiry calls as leads | Every leasing call creates a lead record |
| Qualify callers automatically against per-listing rules | Agent runs only rules enabled for that specific listing |
| Offer cross-listing fallback when caller fails or no match | Unmatched/disqualified callers are offered alternatives |
| Manager can manage listings + leads in one tab | Full CRUD on listings; lead status tracking with export |

### 1.4 Non-Goals (v1)

- Online application or lease signing via voice
- Scheduling property tours via voice (future v2)
- Email/SMS notifications to manager on new lead (dashboard-only in v1)
- Integration with external listing platforms (99acres, MagicBricks, etc.)
- AI-generated tenant risk assessment or credit scoring
- Multi-language support (English only in v1)

---

## 2. Architecture: Hybrid (Shared for Existing Groups, Per-Group for New)

The Lease Agent is a **dedicated leasing-only VAPI assistant**. It never handles complaints. It does not call `Verify_phone_number`. The caller is always a prospective tenant — a stranger with no tenant account.

### 2.1 Existing Property Groups — Shared Number

All existing (test) property groups share **one Twilio number** and **one shared VAPI lease assistant**. The shared assistant has no hardcoded `property_group_id` in its system prompt or tool URLs. The backend's leasing endpoints search listings across **all** property groups when no `property_group_id` is provided.

```
Caller dials shared lease number (user-provided Twilio number)
        ↓
Shared VAPI lease assistant (no hardcoded pg_id)
        ↓
find_listing / search → backend searches ALL property groups
        ↓
submit_lease_lead → property_group_id resolved from matched listing_uuid
                    (null if no listing was identified)
```

The shared number is set up once manually. Its assistant ID is stored in the environment as `VAPI_SHARED_LEASE_ASSISTANT_ID`.

### 2.2 New Property Groups — Auto-Provisioned Dedicated Number

From the **next signup onward**, each new PropertyGroup gets its own dedicated VAPI lease assistant and phone number, automatically provisioned when the PropertyGroup is created:

```
New PropertyGroup created (post-payment signup)
        ↓
Background task: provision_vapi_for_property_group()
        ↓
1. Call VAPI POST /assistant
   • System prompt with property_group_id embedded
   • All 3 lease tool URLs include property_group_id as hardcoded query param
   → Returns: vapi_lease_assistant_id

        ↓
2. Call VAPI POST /phone-number
   • Purchase an available Indian (+91) number
   → Returns: vapi_phone_number_id, phone_number

        ↓
3. Call VAPI PATCH /phone-number/{id}
   • Link the purchased number to the lease assistant
   → number.assistantId = vapi_lease_assistant_id

        ↓
4. Save to properties_list table:
   • vapi_lease_assistant_id
   • vapi_phone_number_id
   • vapi_phone_number (display)
   • vapi_provisioning_status = "active"
```

Callers dialing a group's dedicated number reach that group's listings only — no cross-group leakage.

**Service file:** `backend/app/services/vapi_provisioning.py`
**Trigger:** Called as a background task from `POST /property-groups`.
**Re-provisioning:** If provisioning fails, manager sees a "Lease Agent Not Active" badge in Settings and can retry via `POST /property-groups/{uuid}/provision-voice`.

### 2.3 Architecture Comparison

| | Existing Groups | New Groups (from next signup) |
|---|---|---|
| **Phone number** | Shared Twilio number (user-provided) | Dedicated per-group +91 number (auto-purchased) |
| **VAPI assistant** | One shared assistant (`VAPI_SHARED_LEASE_ASSISTANT_ID`) | One per group (`vapi_lease_assistant_id` in DB) |
| **property_group_id in tools** | Not hardcoded — backend searches all groups | Hardcoded in all tool URLs at provisioning time |
| **Lead pg_id** | Derived from matched listing, or null | From assistant lookup in DB |
| **Setup** | Manual one-time setup | Automatic on PropertyGroup creation |

---

## 3. How It Differs From Complaint Agent

| Aspect | Complaint Agent | Lease Agent |
|--------|----------------|-------------|
| **Who calls** | Existing verified tenants only | Anyone — no tenant account needed |
| **Identity gate** | `Verify_phone_number` required before any action | No verification — caller is a stranger |
| **Phone number** | One global shared number (Option B) | Shared for existing groups; dedicated per new group |
| **property_group_id source** | From `Verify_phone_number` response | Hardcoded in tool URLs (new groups) or from matched listing (shared) |
| **Data captured** | Complaint + appointment | Lead contact info + qualifying answers + outcome |
| **Tools** | Verify, submit_complaint, appointments × 4 | find_listing, search_available_listings, submit_lease_lead |
| **Outcome** | Complaint in DB + appointment | Lead record (QUALIFIED / NOT_QUALIFIED / UNMATCHED) |

**Critical rule:** The Lease Agent **never calls** `Verify_phone_number`. The caller is a prospective tenant — there is no tenant record to verify against.

---

## 4. Voice Agent — Lease Inquiry Flows

### 4.1 Intent Detection

The agent detects leasing intent from natural speech. Trigger phrases include:
- "I'm looking for a place to rent"
- "Do you have any flats available?"
- "I saw your number on the listing"
- "I need a 2-bedroom apartment"
- "How much is the rent for the unit on MG Road?"
- Any mention of "available", "vacancy", "move in", "looking for a flat"

Once detected, the agent routes to **Flow A** (specific property) or **Flow B** (browsing), determined by whether the caller mentions a specific address or unit.

### 4.2 Flow A — Caller Has a Specific Listing in Mind

```
1. LEASE GREETING
   "Thanks for your interest in our properties! Which property 
   are you calling about?"
   <wait>

2. PROPERTY LOOKUP
   Call: find_listing with the caller's stated address/unit
   
   If found:
     Confirm details back:
     "I found it — that's a {bedrooms}-bedroom flat at {address}, 
     {floor_number} floor, available from {available_from}, 
     at ₹{monthly_rent} per month. Does that sound right?"
     <wait for confirmation>
     → Proceed to Step 3 (qualifying questions)
   
   If NOT found (first attempt):
     "Could you repeat the address or spell out the street name?"
     <wait>
     Call: find_listing again
   
   If still NOT found:
     "I don't have an active listing at that address right now. 
     Let me check if we have something similar."
     → Jump to CROSS-LISTING SEARCH (Section 4.6)

3. QUALIFYING QUESTIONS
   Ask only questions enabled for this specific listing's custom_rules.
   Ask ONE question at a time. Wait for response before continuing.
   
   Standard questions (always asked):
   ├── "When are you looking to move in?"
   │   → Extract: move_in_date
   │
   └── "How many people will be living in the unit?"
       → Extract: occupants (integer)
   
   Conditional questions (only if rule is enabled for this listing):
   ├── [if income_required = true]
   │   "Are you currently employed or do you have a stable source of income?"
   │   → Extract: has_income (boolean)
   │
   ├── [if pets_allowed = false OR pets_allowed = "restricted"]
   │   "Do you have any pets?"
   │   → Extract: has_pets (boolean), pet_type (string)
   │
   ├── [if vegetarian_only = true]
   │   "This building follows a vegetarian-only policy. Would that 
   │   work for you?"
   │   → Extract: is_vegetarian (boolean)
   │
   └── [if lease_term_required = true]
       "Are you comfortable with an 11-month lease term?"
       → Extract: agrees_lease_term (boolean)

4. QUALIFICATION CHECK
   (Internal — never verbalise the logic)
   
   DISQUALIFYING conditions (hard fails):
   • has_pets = true AND listing.pets_allowed = false
   • is_vegetarian = false AND listing.vegetarian_only = true
   • occupants > listing.max_occupants (if set)
   • has_income = false AND listing.income_required = true
   
   If QUALIFIED:
     → Proceed to Step 5 (capture contact details)
   
   If NOT QUALIFIED:
     Note the disqualifying_reason.
     Say (gracefully, never blunt):
     "Thank you for that information. Unfortunately, this particular 
     property may not be the best fit based on our requirements. 
     Let me check if we have any other units that might suit you better."
     → Call: search_available_listings with their criteria + pg_id
     → If alternatives exist: present them, ask if interested, 
       resume qualifying for the new listing (loop back to Step 3)
     → If no alternatives: jump to Step 5 with status = not_qualified
       (still capture contact for manager to decide)

5. CAPTURE CONTACT DETAILS
   "Let me take down your details so our manager can follow up."
   
   Q1: "Could I get your full name?"
       → Extract: caller_name (required)
   
   Q2: "What's the best number to reach you on?"
       → Extract: phone (default to caller's number from metadata, confirm verbally)
   
   Q3: "Do you have an email address you'd like to share?" (optional)
       → Extract: email

6. VERBAL CONFIRMATION
   "Just to confirm — you're interested in the {bedrooms}-bedroom flat 
   at {address}. Your name is {name} and best contact is {phone}. 
   Is that all correct?"
   <wait>

7. SUBMIT LEAD
   Call: submit_lease_lead with all collected data
   
8. CLOSE
   If QUALIFIED:
     "Your details have been recorded as a qualified inquiry. 
     Our property manager will contact you within 24 hours 
     to discuss next steps. Thank you for calling!"
   
   If NOT QUALIFIED:
     "I've noted your details and preferences. Our manager will 
     review and reach out if something suitable becomes available. 
     Thank you for calling!"
```

### 4.3 Flow B — Caller Is Browsing (No Specific Property)

```
1. LEASE GREETING
   "Thanks for your interest in our properties! I'd love to help 
   you find the right place. Let me ask a few quick questions."

2. QUALIFYING QUESTIONS (preference-based, not criteria-based)
   Q1: "How many bedrooms are you looking for?"
       → Extract: bedrooms (integer)
   
   Q2: "What's your monthly budget for rent?"
       → Extract: budget_max (number, INR)
   
   Q3: "When are you looking to move in?"
       → Extract: move_in_timeline (text)
   
   Q4: "How many people will be living in the unit?"
       → Extract: occupants (integer)
   
   Q5 (optional): "Any floor preference — lower, upper, or no preference?"
       → Extract: floor_preference (text)

3. SEARCH LISTINGS
   Call: search_available_listings with bedrooms + budget_max + pg_id
   
   If matches found (present top 3):
     "I have a few options for you:
     Option 1: A {bedrooms}-bedroom flat at {address}, {floor}, 
     ₹{monthly_rent}/month, available from {available_from}.
     Option 2: ..."
     Ask: "Would any of these interest you?"
     <wait>
     → If yes: note which listing, run per-listing qualifying questions 
       (same as Flow A Step 3), then capture contact (Flow A Steps 5–8)
     → If no: ask what they're looking for differently, refine search
   
   If no matches:
     "I don't have any units matching your exact criteria right now, 
     but I'd love to take your details so we can reach out when 
     something opens up."
     → Capture contact (Flow A Steps 5–8) with status = unmatched

4. Continue with Flow A Steps 5–8
```

### 4.4 Property-Specific Qualifying Rules

Each listing has a `custom_rules` JSONB field. Managers configure these per unit in the Add/Edit Listing modal.

| Rule Key | Type | Default | Qualifying Question Triggered |
|----------|------|---------|------------------------------|
| `max_occupants` | integer | null (no limit) | "How many people will be living in the unit?" |
| `income_required` | boolean | true | "Are you employed or have a stable income?" |
| `pets_allowed` | enum: `"yes"`, `"no"`, `"cats_only"`, `"small_only"` | `"yes"` | "Do you have any pets?" (if not `"yes"`) |
| `vegetarian_only` | boolean | false | "This building is vegetarian-only. Does that work?" |
| `lease_term_months` | integer | 11 | "Are you comfortable with an 11-month lease?" |
| `custom_question` | string | null | Asked verbatim if non-null |

**Agent rule:** Only ask questions for rules that are non-default or explicitly enabled. If `pets_allowed = "yes"`, skip the pet question entirely.

### 4.5 Qualification Outcome

After all qualifying questions, the agent internally computes the outcome. This is never spoken aloud — the agent transitions naturally.

```
QUALIFIED  → lead.qualification_status = "qualified"
           → lead.disqualifying_reason = null

NOT_QUALIFIED → lead.qualification_status = "not_qualified"
              → lead.disqualifying_reason = "has_pets" | "non_vegetarian" 
                | "max_occupants_exceeded" | "no_income"

UNMATCHED  → lead.qualification_status = "unmatched"
           → No specific listing — no criteria could be applied
```

Disqualified leads are **always logged** — managers see them marked NOT QUALIFIED and decide follow-up. The agent offers cross-listing alternatives before closing.

### 4.6 Cross-Listing Flow (Fallback)

Triggered when:
- Caller's specific property is not found in DB after two attempts
- Caller fails qualification for their chosen listing
- Caller explicitly asks: "Do you have anything else available?"
- Caller changes criteria mid-call ("Actually, I'd prefer 3 bedrooms")

```
Agent calls: search_available_listings with updated/original criteria

If alternatives found:
  "We have a few other units that might work:
   {present up to 3 alternatives}
  Would any of these interest you?"
  <wait>
  → If yes: treat as new Flow A from Step 3 (qualifying for the new listing)
  → If no: capture contact as unmatched inquiry

If no alternatives:
  "We don't have anything else matching right now, but I've noted 
   your preferences and our team will reach out if something 
   becomes available."
  → Capture contact, submit as unmatched lead
```

Ranking of search results returned to the agent:
1. Exact bedroom match first
2. Within budget (rent ≤ budget_max)
3. Earliest `available_from`
4. Max 3 results presented on voice

### 4.7 VAPI Tools — Lease Agent Tools (3)

The Lease Agent has 3 tools only. Built via `build_lease_config_shared(backend_url)` (shared assistant) or `build_lease_config(backend_url, property_group_id, pg_name)` (per-group assistant) in `backend/app/services/vapi_agent_config.py`.

**Tool URL variants:**

| Tool | Shared Assistant | Per-Group Assistant |
|------|-----------------|---------------------|
| `find_listing` | `...?query={{query}}` | `...?property_group_id={PG_ID}&query={{query}}` |
| `search_available_listings` | `...?bedrooms={{bedrooms}}&budget_max={{budget_max}}` | `...?property_group_id={PG_ID}&bedrooms={{bedrooms}}&budget_max={{budget_max}}` |
| `submit_lease_lead` | `.../voice/lease-lead-webhook` | `.../voice/lease-lead-webhook` |

#### Tool 7: `find_listing` (apiRequest)

```json
{
  "type": "apiRequest",
  "name": "find_listing",
  "async": false,
  "function": {
    "name": "api_request_tool",
    "description": "Search for a specific active listing by partial address or unit name within this property group."
  },
  "url": "{BACKEND_URL}/leasing/find-listing?property_group_id={HARDCODED_PG_ID}&query={{query}}",
  "method": "GET",
  "body": {
    "type": "object",
    "required": ["query"],
    "properties": {
      "query": {
        "type": "string",
        "description": "Partial address, street name, or building name the caller mentioned",
        "default": ""
      }
    }
  },
  "variableExtractionPlan": {
    "schema": {
      "type": "object",
      "required": ["found"],
      "properties": {
        "found": { "type": "boolean" },
        "listing_uuid": { "type": "string" },
        "address": { "type": "string" },
        "bedrooms": { "type": "integer" },
        "monthly_rent": { "type": "number" },
        "floor_number": { "type": "string" },
        "available_from": { "type": "string" },
        "custom_rules": { "type": "string", "description": "JSON string of qualifying rules for this listing" }
      }
    }
  }
}
```

#### Tool 8: `search_available_listings` (apiRequest)

```json
{
  "type": "apiRequest",
  "name": "search_available_listings",
  "async": false,
  "function": {
    "name": "api_request_tool",
    "description": "Search available units listed for lease based on caller preferences within this property group."
  },
  "url": "{BACKEND_URL}/leasing/search?property_group_id={HARDCODED_PG_ID}&bedrooms={{bedrooms}}&budget_max={{budget_max}}",
  "method": "GET",
  "body": {
    "type": "object",
    "required": [],
    "properties": {
      "bedrooms": {
        "type": "integer",
        "description": "Number of bedrooms the caller wants",
        "default": ""
      },
      "budget_max": {
        "type": "number",
        "description": "Maximum monthly rent budget in INR",
        "default": ""
      }
    }
  },
  "variableExtractionPlan": {
    "schema": {
      "type": "object",
      "required": ["listings_found"],
      "properties": {
        "listings_found": { "type": "integer" },
        "listings": { "type": "string", "description": "Formatted voice-friendly text of top 3 matching units" },
        "listing_uuids": { "type": "string", "description": "Comma-separated UUIDs of returned listings" }
      }
    }
  }
}
```

#### Tool 9: `submit_lease_lead` (function/webhook)

```json
{
  "type": "function",
  "async": true,
  "function": {
    "name": "submit_lease_lead",
    "strict": true,
    "description": "Capture a prospective tenant's details as a lead record. Call this after confirming all details verbally.",
    "parameters": {
      "type": "object",
      "required": ["caller_name", "phone", "qualification_status"],
      "properties": {
        "caller_name": { "type": "string", "description": "Full name of the caller" },
        "phone": { "type": "string", "description": "Contact phone number" },
        "email": { "type": "string", "description": "Email address (optional)", "default": "" },
        "listing_uuid": { "type": "string", "description": "UUID of the specific listing they were interested in (if identified)", "default": "" },
        "bedrooms": { "type": "integer", "description": "Desired number of bedrooms", "default": 0 },
        "budget_max": { "type": "number", "description": "Max monthly rent budget in INR", "default": 0 },
        "move_in_timeline": { "type": "string", "description": "When they want to move in", "default": "" },
        "occupants": { "type": "integer", "description": "Number of people who will live in the unit", "default": 0 },
        "floor_preference": { "type": "string", "description": "Floor preference if any", "default": "" },
        "qualification_status": {
          "type": "string",
          "description": "Outcome of qualification check",
          "enum": ["qualified", "not_qualified", "unmatched"],
          "default": "unmatched"
        },
        "disqualifying_reason": { "type": "string", "description": "Reason for disqualification (if not_qualified)", "default": "" },
        "qualifying_answers": { "type": "string", "description": "JSON string of all qualifying question answers", "default": "" },
        "interested_listing_ids": { "type": "string", "description": "Comma-separated UUIDs of all listings they expressed interest in", "default": "" },
        "notes": { "type": "string", "description": "Any other preferences or notes captured", "default": "" }
      }
    }
  },
  "server": {
    "url": "{BACKEND_URL}/voice/lease-lead-webhook",
    "timeoutSeconds": 20
  },
  "messages": [{"type": "request-start", "blocking": false}]
}
```

### 4.8 System Prompt Variants

**File:** `backend/app/services/vapi_agent_config.py`

Two system prompts are built by two separate functions.

**Shared assistant (`build_lease_config_shared`) — no property_group_id block:**
```
[Identity]
You are Alex, a professional leasing assistant.
You handle inquiries about properties available for rent.
The caller is a prospective tenant — they have no tenant account.
Do NOT call Verify_phone_number under any circumstances.

[IMPORTANT]
This assistant handles multiple property groups.
Do NOT attempt to filter by a specific property group.
The backend handles cross-group search automatically.

[Leasing Flows]
(Flow A, Flow B, Cross-listing — same as §4.2, §4.3, §4.6 above)

[Rules]
- Do NOT call Verify_phone_number.
- Capture caller phone from VAPI metadata as default; confirm verbally.
- Always call submit_lease_lead regardless of qualification outcome.
- Never ask for or expose any property group ID.
```

**Per-group assistant (`build_lease_config`) — with property_group_id context block:**
```
[Identity]
You are Alex, a professional leasing assistant for {pg_name} properties.
The caller is a prospective tenant — they have no tenant account.
Do NOT call Verify_phone_number under any circumstances.

[Context — Do Not Expose]
You serve property group ID: {property_group_id}
This ID is embedded in all your tool calls automatically. Never reveal it to callers.

[Leasing Flows]
(Flow A, Flow B, Cross-listing — same as §4.2, §4.3, §4.6 above)

[Rules]
- Do NOT call Verify_phone_number.
- Capture caller phone from VAPI metadata as default; confirm verbally.
- Always call submit_lease_lead regardless of qualification outcome.
- Never expose property_group_id to the caller.
```

**Build function signatures:**
```python
def build_lease_config_shared(backend_url: str) -> dict:
    """Shared lease assistant — no pg_id in URLs or system prompt."""

def build_lease_config(backend_url: str, property_group_id: str, pg_name: str) -> dict:
    """Per-group lease assistant — pg_id hardcoded in URLs and system prompt."""
```

---

## 5. Leasing Dashboard Tab

### 5.1 Tab Location

In the sidebar, add **"Leasing"** below "Voice Stats":

```
Dashboard
Tenants
Properties
Rent
Calendar
Complaints
Voice Stats
Leasing        ← NEW (KeyRound icon from Lucide)
SMS Workflow
Settings
```

### 5.2 Metrics Bar (Top of Tab)

A summary metrics row displayed above the listings section, populated from call logs and lead records:

```
┌──────────┬──────────────┬───────────────┬────────────────┬──────────────┐
│  Total   │  Qualified   │ Not Qualified │  Qualification │  Avg Call    │
│  Calls   │    Leads     │    Leads      │    Rate        │  Duration    │
│  142     │    98        │    44         │   69%          │  3m 12s      │
└──────────┴──────────────┴───────────────┴────────────────┴──────────────┘
```

Additional metrics below the row:
- **Unmatched inquiries** (calls where no listing was identified)
- **Calls by property** — a mini breakdown per listing
- **Estimated time saved** — calculated as `total_calls × avg_manual_leasing_call_duration (fixed: 8 min)` minus `total_call_duration`

All metrics are filterable by date range (last 7 days default, with 30-day and custom range options).

### 5.3 Listings Grid

Below the metrics bar, a card grid of all active and inactive listings:

```
┌─────────────────────────────────────────────────────────────┐
│  Available Listings                             [+ Add Unit]│
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                    │
│  │  Photo  │  │  Photo  │  │  Photo  │                    │
│  │         │  │         │  │         │                    │
│  │ A-101   │  │ B-204   │  │ C-301   │                    │
│  │ 2 BHK   │  │ 3 BHK   │  │ 1 BHK   │                    │
│  │₹15,000  │  │₹22,000  │  │₹10,000  │                    │
│  │ 2nd Flr │  │ 1st Flr │  │ 3rd Flr │                    │
│  │ Active  │  │ Active  │  │Inactive │                    │
│  │[Edit][×]│  │[Edit][×]│  │[Edit][×]│                    │
│  │ 3 leads │  │ 1 lead  │  │ 0 leads │                    │
│  └─────────┘  └─────────┘  └─────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

Clicking a listing card filters the leads table below to show only that listing's leads.

### 5.4 Add/Edit Listing Modal

Triggered by **"+ Add Unit"** or the Edit button on a card.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Unit | Dropdown | Yes | Select from vacant flats (`flats` table where `tenant_uuid IS NULL` AND same `property_group_id`) |
| Listing Title | Text | No | Auto-generated if blank: "{bedrooms}BHK in {building}" |
| Monthly Rent | Number (INR) | Yes | Listed rent — shown to callers |
| Available From | Date | No | When the unit is available |
| Description | Textarea | No | Amenities, highlights, etc. |
| Photos | Image upload (multi) | No | Supabase Storage; up to 10 images |
| Is Active | Toggle | Yes | Default ON — inactive listings hidden from voice agent |

**Custom Qualifying Rules section (collapsible, within same modal):**

| Rule | Control | Default |
|------|---------|---------|
| Max occupants | Number input | Empty (no limit) |
| Income proof required | Toggle | ON |
| Pets allowed | Select: Yes / No / Cats only / Small pets only | Yes |
| Vegetarian-only building | Toggle | OFF |
| Lease term (months) | Number input | 11 |
| Custom qualifying question | Text input | Empty |

**Key:** Listing records are thin — they store rent, photos, description, custom_rules, and `flat_uuid` as FK. All unit details (bedrooms, floor, address) come from the `flats` table via join.

### 5.5 Leads Table

Shown below the listings grid. Filterable by: listing (click card), date range, qualification status.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Leads                    [All Listings ▼] [Last 7 days ▼] [All Status ▼]   │
│                                                              [Export CSV]     │
├──────┬──────────┬─────────┬──────┬───────────┬──────────────┬──────────────┤
│ Name │ Phone    │ Budget  │ Beds │ Move-in   │ Status       │ Actions      │
├──────┼──────────┼─────────┼──────┼───────────┼──────────────┼──────────────┤
│Rahul │+91-98...│₹15,000  │ 2    │ Jun 2026  │● Qualified   │[View][✏️][×]│
│Sneha │+91-87...│₹18,000  │ 2    │ Jul 2026  │● Contacted   │[View][✏️][×]│
│Amit  │+91-76...│₹14,000  │ 2    │ Immediate │○ Not Qualif. │[View][✏️][×]│
│Priya │+91-65...│—        │ 1    │ Aug 2026  │▢ Unmatched   │[View][✏️][×]│
└──────┴──────────┴─────────┴──────┴───────────┴──────────────┴──────────────┘
```

The **[View]** button opens `LeadDetailModal` which shows:
- All qualifying answers
- Disqualifying reason (if not_qualified)
- Call duration and call ID (for playback if recording enabled)
- Manager notes field
- Status change dropdown

### 5.6 Lead Status Pipeline

| Status | Meaning | Color | Who Sets It |
|--------|---------|-------|-------------|
| `qualified` | VAPI agent determined qualified | 🔵 Blue | Auto (voice) |
| `not_qualified` | Failed one or more hard criteria | 🔴 Red | Auto (voice) |
| `unmatched` | No listing identified during call | ⬜ Grey | Auto (voice) |
| `contacted` | Manager has followed up | 🟡 Yellow | Manager |
| `toured` | Lead visited the property | 🟠 Orange | Manager |
| `converted` | Signed lease / became tenant | 🟢 Green | Manager |
| `lost` | Lead is no longer interested | 🔴 Red (darker) | Manager |

Managers manually advance leads from `qualified` → `contacted` → `toured` → `converted` or `lost`. The three auto-set statuses (`qualified`, `not_qualified`, `unmatched`) are set by the webhook only — managers cannot revert to them.

### 5.7 Export & Filters

- **Filter by:** listing (dropdown), date range (preset: 7d, 30d, custom), status (multi-select)
- **Export:** "Export CSV" button downloads all filtered leads as CSV with columns: Name, Phone, Email, Listing, Budget, Bedrooms, Move-in, Occupants, Status, Disqualifying Reason, Qualifying Answers (JSON), Call Duration, Date Captured

---

## 6. Backend Implementation

### 6.1 New Database Tables

#### `lease_listings`

```sql
CREATE TABLE lease_listings (
  id            SERIAL PRIMARY KEY,
  uuid          UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
  property_group_id UUID NOT NULL REFERENCES property_groups(uuid),
  flat_uuid     UUID NOT NULL REFERENCES flats(uuid),
  flat_number   TEXT NOT NULL,
  title         TEXT,
  monthly_rent  NUMERIC NOT NULL,
  description   TEXT,
  available_from DATE,
  photo_urls    TEXT[] DEFAULT '{}',
  is_active     BOOLEAN DEFAULT true,
  custom_rules  JSONB DEFAULT '{}',
  manager_id    UUID,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ll_active ON lease_listings(is_active) WHERE is_active = true;
CREATE INDEX idx_ll_flat ON lease_listings(flat_uuid);
CREATE INDEX idx_ll_pg ON lease_listings(property_group_id);
```

`custom_rules` JSONB structure:
```json
{
  "max_occupants": 4,
  "income_required": true,
  "pets_allowed": "no",
  "vegetarian_only": false,
  "lease_term_months": 11,
  "custom_question": ""
}
```

#### `lease_leads`

```sql
CREATE TABLE lease_leads (
  id                    SERIAL PRIMARY KEY,
  uuid                  UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
  property_group_id     UUID NOT NULL REFERENCES property_groups(uuid),
  listing_uuid          UUID REFERENCES lease_listings(uuid),
  interested_listing_ids UUID[] DEFAULT '{}',
  caller_name           TEXT NOT NULL,
  phone                 TEXT NOT NULL,
  email                 TEXT,
  bedrooms              INTEGER,
  budget_max            NUMERIC,
  move_in_timeline      TEXT,
  occupants             INTEGER,
  floor_preference      TEXT,
  qualification_status  TEXT NOT NULL DEFAULT 'unmatched'
                        CHECK (qualification_status IN ('qualified','not_qualified','unmatched',
                               'contacted','toured','converted','lost')),
  disqualifying_reason  TEXT,
  qualifying_answers    JSONB DEFAULT '{}',
  notes                 TEXT,
  source                TEXT NOT NULL DEFAULT 'voice',
  call_id               TEXT,
  call_duration_seconds INTEGER,
  manager_notes         TEXT,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_leads_status ON lease_leads(qualification_status);
CREATE INDEX idx_leads_listing ON lease_leads(listing_uuid);
CREATE INDEX idx_leads_pg ON lease_leads(property_group_id);
CREATE INDEX idx_leads_created ON lease_leads(created_at DESC);
```

### 6.2 PropertyGroup Table Changes

Add lease agent provisioning columns. These are used only for new property groups (existing rows get `not_applicable`):

```sql
ALTER TABLE properties_list
  ADD COLUMN IF NOT EXISTS vapi_lease_assistant_id    TEXT,
  ADD COLUMN IF NOT EXISTS vapi_phone_number_id       TEXT,
  ADD COLUMN IF NOT EXISTS vapi_phone_number          TEXT,
  ADD COLUMN IF NOT EXISTS vapi_provisioning_status   TEXT DEFAULT 'not_applicable'
    CHECK (vapi_provisioning_status IN (
      'not_applicable', 'pending', 'active', 'failed'
    ));
```

`not_applicable` = existing/test groups using the shared lease number.
`pending` / `active` / `failed` = lifecycle for new groups being auto-provisioned.

### 6.3 New API Endpoints

#### Leasing Routes — `backend/app/routes/leasing.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/leasing/find-listing` | None (VAPI) | Find specific listing by address query + pg_id |
| `GET` | `/leasing/search` | None (VAPI) | Search active listings by criteria + pg_id |
| `GET` | `/leasing/listings` | Manager | List all listings for dashboard |
| `POST` | `/leasing/listings` | Manager | Create a new listing |
| `PATCH` | `/leasing/listings/{uuid}` | Manager | Update listing (including custom_rules) |
| `DELETE` | `/leasing/listings/{uuid}` | Manager | Remove listing |
| `GET` | `/leasing/leads` | Manager | List leads (filters: listing_uuid, status, date_from, date_to) |
| `PATCH` | `/leasing/leads/{uuid}` | Manager | Update lead status / manager notes |
| `DELETE` | `/leasing/leads/{uuid}` | Manager | Delete a lead |
| `GET` | `/leasing/metrics` | Manager | Aggregate stats for the metrics bar |
| `GET` | `/leasing/export` | Manager | Download filtered leads as CSV |

#### Voice Webhook — `backend/app/routes/voice.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/voice/lease-lead-webhook` | None (VAPI) | Webhook for `submit_lease_lead` tool |

#### Provisioning — `backend/app/routes/property_groups.py` (or admin routes)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/property-groups/{uuid}/provision-voice` | Admin | Retry VAPI provisioning if it failed during signup |

### 6.4 Key Endpoint Details

**`GET /leasing/find-listing`** (VAPI tool — always HTTP 200):

```python
@router.get("/find-listing")
async def find_listing(
    query: str = Query(...),
    property_group_id: str = Query(...),
    db: Client = Depends(get_db),
):
    try:
        results = (
            db.table("lease_listings")
            .select("uuid, flat_number, title, monthly_rent, available_from, custom_rules, flats!inner(bedrooms, floor_number, address)")
            .eq("is_active", True)
            .eq("property_group_id", property_group_id)
            .ilike("flats.address", f"%{query}%")
            .limit(1)
            .execute()
        )
        if not results.data:
            return {"found": False}
        listing = results.data[0]
        flat = listing.get("flats", {})
        return {
            "found": True,
            "listing_uuid": listing["uuid"],
            "address": flat.get("address"),
            "bedrooms": flat.get("bedrooms"),
            "monthly_rent": listing["monthly_rent"],
            "floor_number": flat.get("floor_number"),
            "available_from": str(listing.get("available_from") or ""),
            "custom_rules": json.dumps(listing.get("custom_rules") or {}),
        }
    except Exception:
        return {"found": False}
```

**`GET /leasing/search`** (VAPI tool — always HTTP 200):

```python
@router.get("/search")
async def search_listings(
    property_group_id: str = Query(...),
    bedrooms: Optional[int] = Query(None),
    budget_max: Optional[float] = Query(None),
    db: Client = Depends(get_db),
):
    try:
        query = (
            db.table("lease_listings")
            .select("uuid, flat_number, monthly_rent, custom_rules, flats!inner(bedrooms, floor_number, address, available_from)")
            .eq("is_active", True)
            .eq("property_group_id", property_group_id)
        )
        results = query.execute()
        matched = []
        for r in (results.data or []):
            flat = r.get("flats", {})
            if bedrooms and flat.get("bedrooms") != bedrooms:
                continue
            if budget_max and r.get("monthly_rent", 0) > budget_max:
                continue
            matched.append(r)
        # Sort: exact bedrooms match first, then by rent ascending
        matched.sort(key=lambda x: (
            0 if bedrooms and x.get("flats", {}).get("bedrooms") == bedrooms else 1,
            x.get("monthly_rent", 0)
        ))
        top3 = matched[:3]
        listings_text = format_listings_for_voice(top3)
        listing_uuids = ",".join(r["uuid"] for r in top3)
        return {
            "listings_found": len(matched),
            "listings": listings_text,
            "listing_uuids": listing_uuids,
        }
    except Exception:
        return {"listings_found": 0, "listings": "No listings available right now.", "listing_uuids": ""}
```

**`POST /voice/lease-lead-webhook`** (VAPI webhook — always HTTP 200):

```python
@router.post("/lease-lead-webhook")
async def lease_lead_webhook(request: Request, db: Client = Depends(get_service_db)):
    try:
        payload = await request.json()
        message = payload.get("message", {})
        tool_calls = message.get("toolCalls", [])
        lead_data = extract_tool_args(tool_calls, "submit_lease_lead")
        if not lead_data:
            return {"result": "ignored"}

        call = message.get("call", {})

        # Resolve property_group_id — priority order:
        # 1. From matched listing (works for both shared and per-group assistants)
        property_group_id = None
        if listing_uuid := lead_data.get("listing_uuid"):
            row = (
                db.table("lease_listings")
                .select("property_group_id")
                .eq("uuid", listing_uuid)
                .maybe_single()
                .execute()
            )
            property_group_id = (row.data or {}).get("property_group_id")

        # 2. From per-group assistant_id in DB (new property groups only)
        if not property_group_id:
            assistant_id = call.get("assistantId")
            pg_row = (
                db.table("properties_list")
                .select("id")
                .eq("vapi_lease_assistant_id", assistant_id)
                .maybe_single()
                .execute()
            )
            property_group_id = (pg_row.data or {}).get("id")
        # 3. If still None: shared assistant + unmatched call → pg_id remains null (acceptable)

        interested_ids = [
            x.strip()
            for x in lead_data.get("interested_listing_ids", "").split(",")
            if x.strip()
        ]
        qualifying_answers = {}
        try:
            qualifying_answers = json.loads(lead_data.get("qualifying_answers", "{}"))
        except Exception:
            pass

        db.table("lease_leads").insert({
            "property_group_id": property_group_id,
            "listing_uuid": lead_data.get("listing_uuid") or None,
            "caller_name": lead_data.get("caller_name"),
            "phone": lead_data.get("phone"),
            "email": lead_data.get("email") or None,
            "bedrooms": lead_data.get("bedrooms") or None,
            "budget_max": lead_data.get("budget_max") or None,
            "move_in_timeline": lead_data.get("move_in_timeline") or None,
            "occupants": lead_data.get("occupants") or None,
            "floor_preference": lead_data.get("floor_preference") or None,
            "qualification_status": lead_data.get("qualification_status", "unmatched"),
            "disqualifying_reason": lead_data.get("disqualifying_reason") or None,
            "qualifying_answers": qualifying_answers,
            "notes": lead_data.get("notes") or None,
            "interested_listing_ids": interested_ids,
            "source": "voice",
            "call_id": call.get("id"),
            "call_duration_seconds": message.get("call", {}).get("duration"),
        }).execute()

        return {"result": "processed"}
    except Exception as e:
        return {"result": "error", "message": str(e)}
```

**`GET /leasing/metrics`**:

```python
@router.get("/metrics")
async def get_leasing_metrics(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Client = Depends(get_authenticated_db),
):
    # Aggregate from lease_leads scoped to manager's property_group_id (via RLS)
    # Returns: total_calls, qualified, not_qualified, unmatched, avg_duration_seconds,
    #          estimated_time_saved_minutes, calls_by_listing []
```

### 6.5 Auto-Provisioning Flow (New Property Groups Only)

**File:** `backend/app/services/vapi_provisioning.py`

This runs **only for new property groups** created from the next signup onward. Existing (test) property groups use the shared lease number and are never auto-provisioned.

```python
async def provision_vapi_for_property_group(
    property_group_id: str,
    pg_name: str,
    db: Client,
):
    """
    BackgroundTask triggered on new PropertyGroup creation.
    Provisions a dedicated VAPI lease assistant + phone number.
    Complaint calls are handled by the global complaint assistant (Option B) — no provisioning needed.
    """
    from vapi import AsyncVapi
    client = AsyncVapi(token=settings.PRIVATE_VAPI_API)
    try:
        # 1. Build per-group lease assistant (property_group_id hardcoded in URLs + system prompt)
        lease_cfg = build_lease_config(BACKEND_URL, property_group_id, pg_name)
        lease = await client.assistants.create(**lease_cfg)

        # 2. Buy +91 phone number
        phone = await client.phone_numbers.create(fallback_destination=None)

        # 3. Link phone → lease assistant
        await client.phone_numbers.update(id=phone.id, assistant_id=lease.id)

        # 4. Save to DB
        db.table("properties_list").update({
            "vapi_lease_assistant_id":  lease.id,
            "vapi_phone_number_id":     phone.id,
            "vapi_phone_number":        phone.number,
            "vapi_provisioning_status": "active",
        }).eq("id", property_group_id).execute()

    except Exception:
        db.table("properties_list").update({
            "vapi_provisioning_status": "failed",
        }).eq("id", property_group_id).execute()
        raise
```

**Error handling:** If any step fails, `vapi_provisioning_status = "failed"`. The Settings tab shows a "Lease Agent Setup Failed — Retry" button that calls `POST /property-groups/{uuid}/provision-voice`.

**Existing groups:** The SQL migration sets `vapi_provisioning_status = 'not_applicable'` for all existing rows — no auto-provisioning is attempted.

### 6.6 VAPI Agent Config Changes

**File:** `backend/app/services/vapi_agent_config.py`

Add two new lease assistant builders (leave legacy `build_assistant_config()` intact):

1. **`build_lease_config_shared(backend_url)`** — shared lease assistant; no `property_group_id` in tool URLs or system prompt
2. **`build_lease_config(backend_url, property_group_id, pg_name)`** — per-group lease assistant; `property_group_id` hardcoded in all 3 tool URLs and injected into system prompt context block

---

## 7. Frontend Implementation

### 7.1 New Files

| File | Purpose |
|------|---------|
| `frontend/src/components/LeasingTab.jsx` | Main tab — metrics bar + listings grid + leads table |
| `frontend/src/components/AddListingModal.jsx` | Create/edit listing modal with custom rules section |
| `frontend/src/components/LeadDetailModal.jsx` | View/edit lead: qualifying answers, status update, manager notes |

### 7.2 Modified Files

| File | Change |
|------|--------|
| `Sidebar.jsx` | Add `{ id: 'leasing', icon: KeyRound, label: 'Leasing' }` after voice-stats |
| `App.jsx` | Add `case 'leasing': return <LeasingTab />` in view router |
| `apiService.js` | Add all `/leasing/*` API methods |

### 7.3 `apiService.js` Additions

```js
// Listings
getListings: () => apiFetch('/leasing/listings'),
createListing: (data) => apiFetch('/leasing/listings', { method: 'POST', body: data }),
updateListing: (uuid, data) => apiFetch(`/leasing/listings/${uuid}`, { method: 'PATCH', body: data }),
deleteListing: (uuid) => apiFetch(`/leasing/listings/${uuid}`, { method: 'DELETE' }),

// Leads
getLeaseLeads: (params) => apiFetch(`/leasing/leads?${new URLSearchParams(params)}`),
updateLead: (uuid, data) => apiFetch(`/leasing/leads/${uuid}`, { method: 'PATCH', body: data }),
deleteLead: (uuid) => apiFetch(`/leasing/leads/${uuid}`, { method: 'DELETE' }),

// Metrics & Export
getLeasingMetrics: (params) => apiFetch(`/leasing/metrics?${new URLSearchParams(params)}`),
exportLeads: (params) => apiFetch(`/leasing/export?${new URLSearchParams(params)}`),
```

---

## 8. Files Summary

### New Files (9)

| File | Purpose |
|------|---------|
| `backend/app/routes/leasing.py` | All listing + lead CRUD + VAPI tool endpoints |
| `backend/app/schemas/leasing.py` | Pydantic V2 models for listings, leads, metrics |
| `backend/app/services/vapi_provisioning.py` | Auto-provisioning: lease assistant + phone number for new groups |
| `backend/migrations/0XX_voice_agents.sql` | DDL for `lease_listings`, `lease_leads`, `properties_list` lease columns |
| `frontend/src/components/LeasingTab.jsx` | Dashboard tab |
| `frontend/src/components/AddListingModal.jsx` | Listing create/edit modal with custom rules |
| `frontend/src/components/LeadDetailModal.jsx` | Lead view/edit modal |

### Modified Files (6)

| File | Change |
|------|--------|
| `backend/app/services/vapi_agent_config.py` | Add `build_lease_config_shared` + `build_lease_config`; keep legacy |
| `backend/app/routes/voice.py` | Add `POST /voice/lease-lead-webhook` with new pg_id resolution |
| `backend/app/main.py` | Register `leasing` router |
| `frontend/src/components/Sidebar.jsx` | Add "Leasing" nav item |
| `frontend/src/App.jsx` | Route to LeasingTab |
| `frontend/src/services/apiService.js` | Add leasing API methods |

---

## 9. Implementation Order

| Phase | Task | Effort |
|-------|------|--------|
| 1 | DB migration: `lease_listings`, `lease_leads`, `properties_list` columns | Low |
| 2 | `GET /leasing/find-listing` + `GET /leasing/search` with optional `property_group_id` | Low |
| 3 | `POST /voice/lease-lead-webhook` (new pg_id resolution logic) | Medium |
| 4 | `GET/POST/PATCH/DELETE /leasing/listings` CRUD | Medium |
| 5 | `GET/PATCH/DELETE /leasing/leads` CRUD + filters | Medium |
| 6 | `GET /leasing/metrics` + `GET /leasing/export` | Medium |
| 7 | Add `build_lease_config_shared` + `build_lease_config` to `vapi_agent_config.py` | Medium |
| 8 | `vapi_provisioning.py` service + wire to PropertyGroup creation (new groups only) | Medium |
| 9 | One-time manual setup: shared lease assistant + complaint assistant | Low |
| 10 | `LeasingTab.jsx` — metrics bar + listings grid + leads table | Medium |
| 11 | `AddListingModal.jsx` — form + custom rules | Medium |
| 12 | `LeadDetailModal.jsx` — full lead view + status update | Medium |
| 13 | Wire Sidebar + App.jsx routing | Low |
| 14 | End-to-end voice testing (shared + per-group + cross-listing) | High |

**Estimated total: 6–8 days**

---

## 10. Testing Plan

### Backend Tests

| Test | Endpoint | Scenario |
|------|----------|----------|
| Find listing — match | `GET /leasing/find-listing?query=sunshine&property_group_id=X` | Returns matching listing with custom_rules |
| Find listing — no match | `GET /leasing/find-listing?query=doesnotexist&property_group_id=X` | Returns `found: false`, HTTP 200 |
| Search — matches | `GET /leasing/search?bedrooms=2&budget_max=20000&property_group_id=X` | Returns ranked results |
| Search — no matches | `GET /leasing/search?bedrooms=5&budget_max=5000&property_group_id=X` | Returns `listings_found: 0`, HTTP 200 |
| Search — wrong pg_id | `GET /leasing/search?property_group_id=WRONG` | Returns `listings_found: 0` (no cross-group leakage) |
| Lead webhook — qualified | `POST /voice/lease-lead-webhook` | Creates lead with `qualification_status=qualified` |
| Lead webhook — not_qualified | `POST /voice/lease-lead-webhook` | Creates lead with `qualification_status=not_qualified` + `disqualifying_reason` |
| Lead webhook — unmatched | `POST /voice/lease-lead-webhook` | Creates lead with `qualification_status=unmatched`, no listing_uuid |
| Lead status update | `PATCH /leasing/leads/{uuid}` | Transitions qualified → contacted → toured |
| Metrics | `GET /leasing/metrics?date_from=2026-05-01` | Returns correct counts + rates |
| Export | `GET /leasing/export` | Returns valid CSV with all columns |
| Provisioning | `POST /property-groups/{uuid}/provision-voice` | Creates VAPI assistant + phone; saves IDs to DB |

### Voice E2E Tests

| Scenario | Expected |
|----------|----------|
| Caller says "I'm looking for a 2-bedroom flat" | Agent asks qualifying questions, searches, captures lead |
| Caller knows specific address | Agent calls find_listing, confirms details, qualifies, captures lead |
| Caller address not found (twice) | Agent falls back to search_available_listings |
| Caller has pets, listing is no-pets | Agent marks not_qualified, offers alternatives |
| Caller non-vegetarian, building is veg-only | Agent marks not_qualified, offers alternatives |
| No alternative listings exist | Agent still captures lead as unmatched |
| Caller switches property mid-call | Agent acknowledges, re-searches, qualifies for new listing |
| Existing tenant calls with complaint | Normal complaint flow — no regression, no lease tools called |
| Agent asks property ID or system info | Agent never exposes property_group_id or internal logic |

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `find_listing` returns wrong unit due to partial address match | Return at most 1 result; agent confirms details verbally before proceeding |
| Agent skips qualifying questions for a listing | System prompt rule: parse `custom_rules` from find_listing response and ask per-rule questions |
| Spam calls creating junk leads | Rate limiting by phone number (10 calls/hour); manager can delete leads in dashboard |
| VAPI provisioning fails for new group | Async background task; retry button in Settings; `vapi_provisioning_status` tracks state |
| Shared assistant returns listings from another manager's group | Acceptable for test groups; new groups get dedicated numbers with pg_id-scoped endpoints |
| Lead has null property_group_id (shared + unmatched call) | Acceptable for test/existing groups; manager can see unmatched leads in dashboard |
| Per-group agent reveals `property_group_id` to caller | System prompt rule: "Never expose this ID to callers" |
| Manager lists too many units — voice agent reads 20 options | `search_available_listings` always caps voice output at 3 results |
| Lease agent called on complaint number or vice versa | Separate phone numbers for complaint and lease agents prevent cross-agent calls |

---

## 12. Open Questions (Deferred to v2)

These items from the Leadpipe spec are explicitly out of scope for v1 and tracked here for future sprints:

| Item | Notes |
|------|-------|
| Automated property tour scheduling via voice | Requires calendar integration for the manager + property |
| Email/SMS notifications to manager on new lead | v1 is dashboard-only. SendGrid + Twilio infra already exists |
| Call recording linked to lead record | Requires VAPI call recording config + storage |
| Multi-language support | English only in v1 |
| Integration with 99acres / MagicBricks | External platform API integration |
| Estimated time saved — configurable benchmark | Fixed at 8 min/manual call in v1; make configurable in v2 |
| Lead deduplication by phone | v1 creates duplicate leads per call; manager decides. Dedup logic in v2 |
| Max properties per PropertyGroup account limit | No limit in v1 |
