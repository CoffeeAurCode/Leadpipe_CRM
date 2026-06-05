# Voice Agent Test Plan â€” Pre-Launch
**Portfolio:** 280 units (first manager)  
**Date:** 2026-06-04  
**Agents:**
- **Complaint Agent â€” Alex** â†’ `+14382314283`
- **Lease Agent â€” Max** â†’ see LeasingTab for your assigned number

---

## Prerequisites

- [ ] Manager account logged in with active subscription
- [ ] At least one property group created (triggers VAPI provisioning)
- [ ] LeasingTab shows `Active` lease line with a phone number

### Step A — Import properties, buildings & units

1. Open the app → **Properties** tab
2. Click **Import CSV** (top-right of the Properties page)
3. Ensure the **Properties** tab is selected inside the import modal
4. Upload `seed_properties.csv` — columns match exactly, no mapping needed → click **Import**

**Creates:** property group "Clearview Heights TEST", buildings "Maple Tower" and "Oak Residences", all 26 units.

### Step B — Import tenants

> **Before uploading:** open `seed_tenants.csv` and replace `+15145550011` (Alex Martin / T101) with your real phone number in E.164 format (e.g. `+15145559999`). This is the number the complaint agent tests use for inbound and outbound calls.

1. Open the app → **Tenants** tab
2. Click **Import CSV** (top-right)
3. The modal defaults to the Tenants tab — upload your edited `seed_tenants.csv` → click **Import**

**Creates:** 5 test tenants (T101, T102, T104, T201, T202) linked to their flats. T103 stays vacant.

### Step C — Seed listings, complaints & appointments

Run `seed_listings.sql` in the **Supabase SQL Editor**.
No placeholders to replace — all UUIDs are resolved automatically from flat numbers.

**Creates:** 20 lease listings with edge-case `custom_rules`, 2 test complaints, 2 test appointments (including the availability blocker for scenario C08).

---

## What the Seed Creates

| Step | Table | Count | Purpose |
|---|---|---|---|
| A — CSV import | `properties_list` | 1 | "Clearview Heights TEST" property group |
| A — CSV import | `buildings` | 2 | Maple Tower (lease), Oak Residences (complaint) |
| A — CSV import | `flats` | 26 | 20 lease units + 6 complaint test units |
| B — CSV import | `tenants` | 5 | Test tenants for complaint agent |
| C — SQL | `lease_listings` | 20 | All custom_rules edge cases covered |
| C — SQL | `complaints` | 2 | One real, one blocker for availability test |
| C — SQL | `appointments` | 2 | One for view/reschedule/cancel; one blocks 2026-07-15 14:00 |

> **Portfolio size note:** 20 listings > threshold of 10, so `load_listings` always returns `has_more=true`. The lease agent will always use `search_listings` to fetch units â€” matching real 280-unit behaviour.

---

## Listing Inventory (Lease Agent Reference)

All listings are in Maple Tower, Clearview Heights, Montreal.

| Code | Beds | Rent/mo | Floor | Pets | Non-Smoking | Max Occ | Parking | Laundry | Available |
|---|---|---|---|---|---|---|---|---|---|
| TST01 | Studio | $900 | 1 | yes | no | â€” | None | Shared | Jul 1 |
| TST02 | Studio | $1,050 | 2 | **no** | **yes** | **1** | None | Shared | Jul 1 |
| T1B01 | 1-bed | $1,200 | 1 | yes | no | 2 | None | In-unit | Jul 1 |
| T1B02 | 1-bed | $1,350 | 2 | **small only** | no | 2 | None | In-unit | Jul 15 |
| T1B03 | 1-bed | $1,400 | 3 | **no** | **yes** | 2 | None | In-unit | Jul 1 |
| T1B04 | 1-bed | $1,100 | 1 | yes | no | **1** | None | Shared | Jul 1 |
| T2B01 | 2-bed | $1,700 | 2 | yes | no | 4 | 1 spot | In-unit | Jul 1 |
| T2B02 | 2-bed | $1,800 | 3 | yes | **yes** | 3 | 1 spot | In-unit | Jul 1 |
| T2B03 | 2-bed | $1,950 | 4 | **no** | **yes** | 3 | None | In-unit | **Aug 1** |
| T2B04 | 2-bed | $1,600 | 1 | **small only** | no | 4 | None | Shared | Jul 1 |
| T2B05 | 2-bed | $2,100 | 5 | yes | no | **5** | 2 spots | In-unit | Jul 1 |
| T2B06 | 2-bed | $2,200 | 6 | **no** | no | 3 | 1 spot | In-unit | **Aug 15** |
| T3B01 | 3-bed | $2,400 | 2 | yes | no | **6** | 2 spots | In-unit | Jul 1 |
| T3B02 | 3-bed | $2,600 | 3 | yes | **yes** | **5** | 2 spots | In-unit | Jul 1 |
| T3B03 | 3-bed | $2,800 | 4 | **no** | **yes** | **4** | 2 spots | In-unit | **Aug 1** |
| T3B04 | 3-bed | $2,500 | 2 | **small only** | no | **5** | None | Shared | Jul 15 |
| T3B05 | 3-bed | $3,000 | 5 | yes | no | **none** | 2 spots | In-unit | Jul 1 |
| T4B01 | 4-bed | $3,200 | 3 | yes | no | **8** | 2 spots | In-unit | Jul 1 |
| T4B02 | 4-bed | $3,500 | 4 | yes | **yes** | **6** | 2 spots | In-unit | **Aug 1** |
| T4B03 | 4-bed | $2,900 | 2 | **no** | **yes** | **6** | None | In-unit | Jul 1 |

Bolded values = the edge case being tested in that listing.

---

## Complaint Test Setup

All units in Oak Residences, Clearview Heights. Call from the phone listed â€” or use the outbound call button in the dashboard to have the agent call you.

| Flat | Tenant | Registered Phone | Test Purpose |
|---|---|---|---|
| T101 | Alex Martin | **YOUR PHONE** (replace in seed) | All valid-caller tests |
| T102 | Sophie Leblanc | +15145550022 | Availability blocker appointment |
| T103 | *(vacant)* | â€” | Vacant-flat response test |
| T104 | James Wong | +15145550044 | Invalid-phone test (call from different number) |
| T201 | Marie Audet | +15145550061 | French-caller test |
| T202 | David Park | +15145550062 | View / reschedule / cancel appointment test |

**Seeded appointment for T202:** maintenance callback, scheduled `2026-07-10 10:00`  
**Blocker for availability test:** appointment on `2026-07-15 14:00` (any Â±45min slot returns unavailable)

---

## Part A â€” Lease Agent Tests (call Max's number)

> **Before each call:** open the LeasingTab â†’ Leads view. After each call: refresh and verify a new lead row appeared with the right data.

---

### L01 â€” Baseline happy path
**Goal:** end-to-end qualified lead, all fields captured.

**Say:** "Hi" â†’ "I'm looking for a 2-bedroom, budget around eighteen hundred, no pets, and I don't smoke" â†’ "Around July, just me and my partner" â†’ name when asked â†’ "Yes, I'm employed full-time" â†’ "I'm currently renting, my landlord knows I'm moving"

**Max must:**
1. Not dump units at "Hi" â€” asks size/budget first
2. Fire search_listings with bedrooms=2, budget_max=1800
3. Present units that pass all filters: T2B01 ($1,700, pets=yes), T2B02 ($1,800, pets=yes), T2B04 ($1,600, small_only) â†’ all 3 qualify (caller has no pets)
4. Collect qualification answers
5. Call submit_lease_lead exactly once

**DB check:**
```sql
SELECT caller_name, bedrooms, budget_max, qualification_status, notes,
       array_length(interested_listing_ids, 1) AS interests
FROM lease_leads ORDER BY created_at DESC LIMIT 1;
```
Expected: qualification_status = `qualified`, bedrooms = 2, budget_max = 1800.

---

### L02 â€” "What do you have?" â€” preference-first enforcement
**Goal:** critical regression test for Fix 4. Agent must NOT dump units.

**Say:** "Hi, what do you have available?"

**Max must:**
- Ask a preference question before mentioning any units
- Acceptable first responses: "What size are you looking for?", "Do you have a budget in mind?", "What are you looking for?"
- FAIL if Max lists any unit names, rents, or flat numbers in this turn

**DB check:** not applicable â€” just observe the agent's response.

---

### L03 â€” Large dog (big-pet silent filter)
**Goal:** units with pets=no and pets=small_only are excluded silently.

**Say:** "2-bedroom please, I have a German Shepherd" â†’ budget: "around two thousand"

**Max must:**
- Present only T2B01 ($1,700, pets=yes) and T2B02 ($1,800, pets=yes)
- **Silently exclude:** T2B03 (no pets), T2B04 (small_only)
- Never say "this unit doesn't allow large pets" for the excluded ones â€” they just never appear

**DB check:**
```sql
SELECT notes, interested_listing_ids FROM lease_leads ORDER BY created_at DESC LIMIT 1;
```
Expected: notes mention dog/German Shepherd. No T2B03/2B04 UUID in interested_listing_ids.

---

### L04 â€” Small cat (small_only units are eligible)
**Goal:** pets=small_only should NOT be excluded for a small-pet owner.

**Say:** "2-bedroom, I have a small cat" â†’ budget: "eighteen hundred max"

**Max must:**
- Present units with pets=yes AND pets=small_only
- Within budget â‰¤$1,800: T2B01 ($1,700, yes), T2B02 ($1,800, yes), T2B04 ($1,600, small_only)
- Exclude T2B03 ($1,950 over budget; also no pets anyway)
- **T2B04 must appear** â€” small_only is acceptable for a small cat

**DB check:** verify T2B04's UUID appears in either `listing_uuid` or `interested_listing_ids` if caller showed interest.

---

### L05 â€” Smoker (non-smoking filter)
**Goal:** units with non_smoking=true are silently excluded.

**Say:** "3-bedroom, I smoke"

**Max must:**
- Present only T3B01 ($2,400, ns=false), T3B04 ($2,500, ns=false), T3B05 ($3,000, ns=false)
- **Silently exclude:** T3B02 (ns=true), T3B03 (ns=true)
- search_listings returns top 5 cheapest 3-beds first â†’ 3B01, 3B04, 3B01, etc. After smoking filter: 3 remain

**DB check:** notes mention smoking. None of T3B02/3B03 UUIDs appear in the lead.

---

### L06 â€” Family of 6 (occupancy filter)
**Goal:** units with max_occupants < 6 are silently excluded.

**Say:** "Looking for a 3-bedroom, we're 6 people total"

**Max must:**
- Present only: T3B01 (max=6), T3B05 (max=none/null)
- **Silently exclude:** T3B02 (max=5), T3B03 (max=4), T3B04 (max=5)
- 2 units remain â†’ describe directly, ask which interests them

**DB check:** occupants = 6 in lead record.

---

### L07 â€” Budget only ($1,500 ceiling)
**Goal:** strict budget filter, agent asks to narrow further when many results exist.

**Say:** "Something under fifteen hundred a month, I'm flexible on size"

**Max must:**
- Pass budget_max=1500 to search_listings (â‰¤$1,500)
- Results: TST01 ($900), TST02 ($1,050), T1B04 ($1,100), T1B01 ($1,200), T1B02 ($1,350) â†’ 5+ matches
- Since 5 matches without a size filter, agent asks one narrowing question: "What size are you looking for?"
- After: studio / 1-bed â†’ narrows further

**DB check:** budget_max â‰¤ 1500 in lead record.

---

### L08 â€” Combined filter: large dog + 2-bed + $1,800 budget
**Goal:** all three filters compound correctly.

**Say:** "2-bedroom, budget around eighteen hundred, I have a Rottweiler"

**Max must:**
- Apply: bedrooms=2 + budget_max=1800 + pets=yes (big dog excludes small_only)
- Passing: T2B01 ($1,700, pets=yes), T2B02 ($1,800, pets=yes)
- Excluded: T2B04 ($1,600, small_only â†’ big dog), T2B03 ($1,950, over budget + no pets)

**DB check:** notes mention Rottweiler, bedrooms=2, budget_max=1800.

---

### L09 â€” Zero matches after filtering
**Goal:** agent gives an honest close, still captures lead.

**Say:** "4-bedroom, budget three thousand, I smoke, and I have a Doberman"

Filters applied: bedrooms=4 + budget_max=3000 + smoking (ns=false) + big dog (pets=yes)
- T4B01: $3,200 â†’ over budget
- T4B02: $3,500 â†’ over budget
- T4B03: $2,900, pets=no â†’ excluded for dog
â†’ 0 matches

**Max must:**
- Offer closest alternative if any (there isn't one for all combined filters)
- Say honestly: "We don't have the right fit at the moment"
- **Still capture the lead** with all preferences in notes

**DB check:**
```sql
SELECT qualification_status, notes, bedrooms, budget_max FROM lease_leads ORDER BY created_at DESC LIMIT 1;
```
Expected: qualification_status = `unmatched`, notes detail all stated preferences.

---

### L10 â€” Just browsing (no stated preferences)
**Goal:** agent must gather at least one preference before showing anything.

**Say:** "Hi, I'm just browsing, what's available?"

**Max must:**
- NOT say "let me pull up our listings" or list units
- Ask: "What size place are you looking for?" or "Do you have a rough budget in mind?"
- Only after the caller gives a preference does Max share results

**Observe:** agent's first response after "just browsing". It must be a question, not a unit listing.

---

### L11 â€” 6 results â†’ narrow down
**Goal:** when â‰¥6 matches exist, agent asks one more question before presenting.

**Say:** "I'm looking for a 2-bedroom" (no budget stated)

search_listings with bedrooms=2, no budget â†’ returns 5 cheapest: 2B04, 2B01, 2B02, 2B03, 2B05.

**Max must:**
- With 5 results, present brief list: "I've got five 2-bedroom options â€” I'll go through them"
- OR ask one narrowing question if the count feels overwhelming to the agent
- In any case, do NOT present all 6 2-beds as a wall of text

**DB check:** lead created with bedrooms=2.

---

### L12 â€” Multiple unit interest (interested_listing_ids)
**Goal:** caller interested in 2+ units â†’ all UUIDs captured.

**Say:** (Continue from L11 or start fresh) â†’ after Max presents 2-bed options â†’ "I'm interested in the first one and the third one"

**Max must:**
- Note both units
- Collect qualification info once (not twice)
- Include both UUIDs in `interested_listing_ids` when submitting lead

**DB check:**
```sql
SELECT interested_listing_ids FROM lease_leads ORDER BY created_at DESC LIMIT 1;
```
Expected: array length â‰¥ 2.

---

### L13 â€” Disqualified (pet revealed during qualification)
**Goal:** if pet status wasn't volunteered during preferences, disqualification happens at Q6 during qualification.

**Say:** "2-bedroom please" â†’ budget: "two thousand" â†’ no mention of pets during preference gathering  
Agent presents results (including T2B03 which has pets=no, since pets unknown â†’ no filter applied)  
â†’ "I'm interested in the third option" (whichever is the no-pets unit)  
â†’ During qualification, when asked about pets: "Yes, I have a dog"

**Max must:**
- Disqualify: "Unfortunately this unit doesn't allow pets"
- qualification_status = `not_qualified`
- disqualifying_reason = "pets not allowed" (or similar)
- **Still submit the lead**

**DB check:**
```sql
SELECT qualification_status, disqualifying_reason FROM lease_leads ORDER BY created_at DESC LIMIT 1;
```

---

### L14 â€” Out-of-scope (maintenance call to lease line)
**Goal:** Max handles misdirected calls gracefully, still logs a lead.

**Say:** "Hi, my kitchen sink is leaking, I need someone to come fix it"

**Max must:**
- Explain politely: he handles rental inquiries, not maintenance
- Direct caller to the property management team
- Ask if there's anything on the leasing side
- **Still call submit_lease_lead** with notes like "caller called about maintenance â€” misdirected call"

**DB check:** lead exists with notes mentioning maintenance/misdirected.

---

### L15 â€” French caller
**Goal:** agent locks to French after first French utterance. Tools still submitted in English.

**Say:** "Bonjour, je cherche un appartement Ã  louer, deux chambres"

**Max must:**
- Respond in French from the first reply onwards
- Never slip back to English
- When filing the lead: all field values in English (translated from French)

**Observe:** entire call stays in French. Lead created with English field values.

---

### L16 â€” Ambiguous opener ("hi")
**Goal:** agent responds in English, does NOT force the bilingual "English / French" opener.

**Say:** "Hi"

**Max must:**
- Respond in English
- NOT say "English or French? / Anglais ou franÃ§ais?"
- Not force bilingual â€” just respond naturally in English

**Observe:** Max's first response. It must be a single-language English greeting.

---

### L17 â€” No budget preference
**Goal:** agent notes "no preference" and moves on. Never pushes for a budget.

**Say:** "2-bedroom please" â†’ when asked about budget: "I don't really have a specific budget"

**Max must:**
- Accept "no preference" and move on without asking again
- Pass budget_max=0 to search_listings (no budget filter)
- Present all 2-bed units (filtered by any other stated preferences)

**DB check:** budget_max = 0 in lead record.

---

### L18 â€” Early hang-up (fallback lead)
**Goal:** even with no submit_lease_lead call, the EOC webhook creates a partial lead.

**Say:** "Hi, I'm looking for..." â†’ hang up after ~15 seconds

**Max must not** need to do anything â€” the backend handles this.

**DB check (30 seconds after hanging up):**
```sql
SELECT caller_name, phone, qualification_status, notes FROM lease_leads ORDER BY created_at DESC LIMIT 1;
```
Expected: caller_name = `Unknown`, qualification_status = `unmatched`, notes contain partial transcript.

---

### L19 â€” Solo occupancy unit (max_occupants = 1)
**Goal:** family/couple is silently excluded from solo-only units.

**Say:** "1-bedroom please, me and my partner â€” two of us"

**Max must:**
- Exclude T1B04 (max_occupants=1 â€” couple exceeds limit)
- Present T1B01 ($1,200, max=2) and T1B02 ($1,350, max=2)
- T1B03 also max=2 but pets=no / ns=true â€” should appear since no pet/smoke preference stated

**DB check:** occupants = 2 in lead record.

---

### L20 â€” Caller refuses to give name
**Goal:** agent uses "Anonymous" and still submits the lead.

**Go through** a normal 2-bed inquiry â†’ when Max asks "Could I get your name?" â†’ say "I'd prefer not to give my name"

**Max must:**
- Accept the refusal gracefully
- Use "Anonymous" as caller_name
- **Not leave caller_name blank** â€” submit_lease_lead still fires

**DB check:** caller_name = `Anonymous` in the lead record.

---

## Part B — Complaint Agent Tests (call Alex: +14382314283)

> For inbound tests: call from the phone registered to the test tenant (or use the OutboundCallButton in the dashboard to have Alex call you first).

> **Startup acceptance criteria (applies to every C-series test):** After the Bug 1 fix (`firstMessageMode`, `numWords: 5`, `confidenceThreshold: 0.6`), every complaint call must pass all three before the functional test below is evaluated:
> 1. Greeting plays within **3 seconds** of call connecting — no dead silence at call connect
> 2. Greeting completes cleanly — last word must not stretch, repeat, or cut off
> 3. Speaking 1–4 words during the greeting must NOT interrupt it — only 5+ spoken words should yield the turn

---

### C01 â€” Full valid complaint + callback booking
**Phone:** Your phone (registered to flat T101)

**Say:**
1. Flat number: "T 1 0 1"
2. Issue: "My kitchen faucet has been dripping non-stop for three days, it's wasting water"
3. Callback time: "Tomorrow at 2pm" (or any future date)
4. Confirm details when asked

**Alex must:**
1. Call Verify_phone_number â†’ status = valid â†’ proceed
2. Identify category as water/plumbing (maps to `water`)
3. Call check_availability â†’ available â†’ confirm with caller
4. Call submit_complaint with flat_number=T101, category=water, description, appointment_date
5. Confirm: "Your complaint has been logged and a callback is scheduled"

**DB check:**
```sql
SELECT flat_number, category, description, source FROM complaints ORDER BY created_at DESC LIMIT 1;
SELECT flat_number, appointment_date, status FROM appointments ORDER BY created_at DESC LIMIT 1;
SELECT complaint_status FROM call_logs ORDER BY created_at DESC LIMIT 1;
```

**Voice Stats check (Bug 2 regression):** Open the **Voice Stats** tab → verify:
- `Total` counter > 0
- This call appears in the **Recent Calls** list with `complaint_status = created`

---

### C02 — Invalid phone (mismatch)
**Phone:** Any number NOT registered to flat T102 (e.g., your second phone, or call from any unregistered number)

**Say:**
1. Flat number: "T 1 0 2" (Sophie Leblanc's flat â€” but you're calling from the wrong phone)

**Alex must:**
- Call Verify_phone_number â†’ status = invalid
- Say: "I'm sorry, the number you're calling from doesn't match our records for that flat. Please contact our office directly. Have a good day."
- END CALL IMMEDIATELY â€” no follow-up questions

**DB check:** call_log created with complaint_status = `incomplete` or `failed`.

---

### C03 â€” Vacant flat
**Phone:** Any number

**Say:**
1. Flat number: "T 1 0 3" (vacant â€” no tenant assigned)

**Alex must:**
- Call Verify_phone_number â†’ status = vacant
- Say: "I'm sorry, that flat doesn't appear to have a registered tenant. Please contact our office for assistance. Have a good day."
- END CALL IMMEDIATELY

---

### C04 â€” Invalid flat number twice
**Phone:** Any number

**Say:**
1. First attempt: "X 9 9 9" (doesn't exist)
2. Second attempt: "Z 0 0 0" (doesn't exist again)

**Alex must:**
- Accept the first attempt, verify it â†’ vacant or error response
- On second failure: "I wasn't able to verify your flat number. If you need assistance, please contact our office directly."
- END CALL

---

### C05 â€” View active appointment
**Phone:** David Park's phone (+15145550062, registered to T202)

**Say:**
1. Flat number: "T 2 0 2"
2. After verification: "I'd like to check my appointment"

**Alex must:**
- Call view_active_appointments â†’ returns the seeded maintenance appointment (2026-07-10 10:00)
- Read back: category (maintenance), date (July 10th), time (10am)
- Ask: "Would you like to make any changes to this appointment?"

---

### C06 â€” View appointment â€” none exists
**Phone:** Your phone (T101, Alex Martin â€” no appointment seeded)

**Say:**
1. Flat number: "T 1 0 1"
2. After verification: "Do I have any appointments scheduled?"

**Alex must:**
- Call view_active_appointments â†’ empty result
- Say: "There are currently no active appointments scheduled for your flat."
- Ask if there's anything else to help with

---

### C07 â€” Reschedule appointment (available slot)
**Phone:** David Park's phone (T202)

**Say:**
1. Flat: "T 2 0 2"
2. "I'd like to reschedule my appointment"
3. New time: "July 20th at 3pm" (no existing appointment near this time)

**Alex must:**
- Call view_active_appointments â†’ finds the appointment
- Ask for new time â†’ "July 20th at 3pm"
- Call check_availability(2026-07-20T15:00:00) â†’ available
- Confirm: "July 20th at 3pm. Is that correct?"
- Call update_appointment
- Confirm: "Your appointment has been successfully updated"

**DB check:**
```sql
SELECT appointment_date, status FROM appointments WHERE flat_number = 'T202' ORDER BY id DESC LIMIT 1;
```
Expected: appointment_date updated to 2026-07-20T15:00:00.

---

### C08 â€” Reschedule to unavailable slot (conflict then retry)
**Phone:** David Park's phone (T202)

**Say:**
1. Flat: "T 2 0 2"
2. "I'd like to reschedule"
3. First new time: **"July 15th at 2pm"** (blocked â€” appointment for T102 exists at 14:00, window Â±1hr)
4. Second new time: "July 16th at 10am"

**Alex must:**
- check_availability(2026-07-15T14:00:00) â†’ unavailable
- Say: "I'm sorry, the manager already has an appointment around that time. Could you suggest another date or time?"
- check_availability(2026-07-16T10:00:00) â†’ available
- Confirm and update

**Observe:** the loop â€” Alex loops back and asks for another time without frustration.

---

### C09 â€” Cancel appointment
**Phone:** David Park's phone (T202)

**Say:**
1. Flat: "T 2 0 2"
2. "I'd like to cancel my appointment"

**Alex must:**
- Call view_active_appointments â†’ finds appointment
- Read it back: "You have a maintenance callback scheduled for July 10th at 10am"
- Ask for confirmation: "Just to confirm, you'd like to cancel this appointment. Is that correct?"
- Call cancel_appointment
- Confirm: "Your appointment has been successfully cancelled"

**DB check:** appointment status = `cancelled`.

---

### C10 â€” Emergency (gas/safety risk)
**Phone:** Your phone (T101)

**Say:**
1. Flat: "T 1 0 1"
2. After verification: "I smell something like gas near my stove, I'm not sure if it's a leak"

**Alex must:**
- Detect potential emergency
- Ask for explicit confirmation: "Is this something that feels like a gas smell â€” a safety concern?"
- If confirmed: get a callback time, call check_availability, schedule callback
- Call submit_complaint with an appropriate category (security or other)
- Never attempt to troubleshoot ("try turning off the stove") â€” just schedules the callback

**DB check:** complaint created, source = voice, category mapped to security or other.

---

### C11 â€” French caller
**Phone:** Marie Audet's phone (+15145550061, registered to T201)

**Say (in French):**
1. "Mon numÃ©ro d'appartement est T 2 0 1"
2. "Mon chauffage ne fonctionne pas depuis hier"
3. Callback time in French: "Demain matin Ã  dix heures"

**Alex must:**
- Lock to French from the first French utterance
- All tool submissions in English (flat_number=T201, category=electricity or maintenance, description in English)
- Final confirmation in French

**DB check:** complaint created with English field values despite French conversation.

---

### C12 â€” Leasing inquiry on complaint line
**Phone:** Any number

**Say:** "Hi, I'm looking to rent an apartment in your building â€” do you have anything available?"

**Alex must:**
- Politely explain this line is for existing tenants (maintenance/service)
- Direct the caller to the leasing team / leasing line
- NOT attempt to handle the leasing inquiry
- NOT ask for flat number (caller is not a tenant)

**Observe:** Alex stays in scope. No verification attempted. Caller redirected cleanly.

---

### C13 — Greeting quality regression (Bug 1 fix)
**Goal:** confirm the three config fixes eliminated the startup hang and word-stretch artifact.

**Phone:** Your phone (T101)

**Call 1 — silent listen:**
1. Call +14382314283
2. Do NOT speak — let the greeting finish uninterrupted
3. Start a timer at call connect

**Alex must:**
- Begin speaking within **3 seconds** of connect (no dead silence)
- Complete the full greeting `"Hi, this is Alex — how can I help you today?"` without the last word stretching, repeating, or cutting off
- Remain on the line after the greeting and wait for input (no hang-up from VAPI silence timeout during the pause)

**Call 2 — interrupt resilience:**
1. Call again
2. While Alex is speaking, say exactly **3 words** (e.g. `"Yes, hi, hello"`) — do not pause between words
3. Note whether Alex stops or continues

**Alex must:**
- **NOT stop mid-greeting** — 3 words is below the `numWords: 5` threshold
- Continue through the end of the greeting before yielding the turn

**Call 3 — interrupt trigger:**
1. Call again
2. While Alex is speaking, say **6 or more words** clearly (e.g. `"Yes I'm calling about a problem with my flat"`)

**Alex must:**
- Stop speaking and yield the turn (the `numWords: 5` threshold is met)
- Respond to what was said rather than restarting the greeting

**Pass criteria:** Call 1 timing ≤ 3 s, no stretch/repeat; Call 2 greeting not interrupted; Call 3 greeting interrupted cleanly.

---

### C14 — Voice Stats tab data visibility (Bug 2 regression)
**Goal:** confirm the RLS SELECT policy fix — authenticated managers can read their own `call_logs` rows.

**Prerequisite:** C01 completed (a call_log with your `manager_id` was inserted by the webhook).

**Steps:**
1. Open the app → **Voice Stats** tab
2. If the counters are still 0, click **Refresh**
3. Check the `Total` counter and the **Recent Calls** list

**Must pass:**
- `Total` > 0
- The C01 call appears in Recent Calls with `complaint_status = created`
- No errors in the browser console for `/call_logs/stats`

**SQL double-check:**
```sql
SELECT complaint_status, manager_id, created_at
FROM call_logs
ORDER BY created_at DESC
LIMIT 5;
```
Expected: rows returned (not empty). `manager_id` matches `auth.uid()` of the logged-in manager.

---

## Post-Test Verification Queries

Run these in the Supabase SQL Editor after testing sessions:

```sql
-- Recent leads (lease agent)
SELECT 
  caller_name, phone, bedrooms, budget_max, qualification_status, 
  disqualifying_reason, notes, array_length(interested_listing_ids, 1) AS interests,
  created_at
FROM lease_leads
ORDER BY created_at DESC
LIMIT 10;

-- Recent call logs (complaint agent)
SELECT call_id, phone_number, complaint_status, created_at
FROM call_logs
ORDER BY created_at DESC
LIMIT 10;

-- Recent complaints (complaint agent)
SELECT flat_number, category, description, source, status, created_at
FROM complaints
ORDER BY created_at DESC
LIMIT 10;

-- Recent appointments
SELECT flat_number, appointment_date, status, notes, created_at
FROM appointments
ORDER BY created_at DESC
LIMIT 10;

-- Check all test leads exist (run after full lease agent pass)
SELECT COUNT(*) AS lead_count FROM lease_leads
WHERE created_at > NOW() - INTERVAL '1 day';

-- Leads with empty caller_name (should be zero â€” only Anonymous allowed)
SELECT * FROM lease_leads
WHERE (caller_name IS NULL OR caller_name = '')
  AND created_at > NOW() - INTERVAL '1 day';
```

---

## Edge Case Coverage Checklist

| Edge Case | Scenario(s) |
|---|---|
| No unit dump on first message | L02, L10 |
| Large pet filter (exclude no+small_only) | L03, L08, L09 |
| Small pet filter (include small_only) | L04 |
| Smoker filter (exclude non_smoking) | L05, L09 |
| Occupancy filter (max_occupants) | L06, L19 |
| Budget filter | L07, L08, L09 |
| Combined multi-filter | L08, L09 |
| Zero matches â†’ honest close | L09 |
| Multiple unit interests in one call | L12 |
| Disqualification during qualification | L13 |
| Out-of-scope call (lease line) | L14 |
| Out-of-scope call (complaint line) | C12 |
| French language locked | L15, C11 |
| Ambiguous opener (no bilingual force) | L16 |
| No budget preference | L17 |
| Early hang-up â†’ partial lead | L18 |
| Caller refuses name â†’ Anonymous | L20 |
| Valid verification + full complaint | C01 |
| Phone mismatch (invalid) | C02 |
| Vacant flat | C03 |
| Repeated invalid flat â†’ end call | C04 |
| View existing appointment | C05 |
| View â€” no appointment | C06 |
| Reschedule to open slot | C07 |
| Reschedule â†’ conflict â†’ retry | C08 |
| Cancel appointment | C09 |
| Emergency handling | C10 |
| All leads captured regardless of outcome | L09, L13, L14, L18, C02, C03 |
| Greeting plays without startup hang | C13 |
| Last word of greeting does not stretch or repeat | C13 |
| Connection noise (< 5 words) does not interrupt greeting | C13 |
| 5+ spoken words correctly interrupt greeting | C13 |
| Voice Stats tab shows data after call completes | C01, C14 |

---

## Cleanup

Run in the **Supabase SQL Editor** in this exact order (respects foreign keys):

```sql
-- 1. Test leads generated during testing
DELETE FROM lease_leads
  WHERE listing_uuid IN (
    SELECT ll.uuid FROM lease_listings ll
    JOIN properties_list pg ON ll.property_group_id = pg.id
    WHERE pg.name = 'Clearview Heights TEST'
  )
  OR notes ILIKE '%Clearview Heights%'
  OR notes ILIKE '%test seed%';

-- 2. Appointments seeded + any created during complaint agent tests
DELETE FROM appointments
  WHERE flat_number IN ('T101','T102','T103','T104','T201','T202')
     OR flat_number LIKE 'T%B%' OR flat_number LIKE 'TST%';

-- 3. Complaints seeded + any created during complaint agent tests
DELETE FROM complaints
  WHERE flat_number IN ('T101','T102','T103','T104','T201','T202')
     OR flat_number LIKE 'T%B%' OR flat_number LIKE 'TST%';

-- 4. Lease listings (seeded by seed_listings.sql)
DELETE FROM lease_listings
  WHERE flat_number LIKE 'T%B%' OR flat_number LIKE 'TST%';

-- 5. Unlink tenants before deleting (bidirectional FK)
UPDATE flats SET tenant_uuid = NULL, occupied = false
  WHERE flat_number IN ('T101','T102','T104','T201','T202');

-- 6. Tenants (seeded by CSV import)
DELETE FROM tenants
  WHERE flat_uuid IN (
    SELECT uuid FROM flats
    WHERE flat_number IN ('T101','T102','T104','T201','T202')
  );

-- 7. Flats (seeded by CSV import)
DELETE FROM flats
  WHERE flat_number LIKE 'T%B%' OR flat_number LIKE 'TST%'
     OR flat_number IN ('T101','T102','T103','T104','T201','T202');

-- 8. Buildings (seeded by CSV import)
DELETE FROM buildings
  WHERE name IN ('Maple Tower', 'Oak Residences')
    AND property_id IN (
      SELECT id FROM properties_list WHERE name = 'Clearview Heights TEST'
    );

-- 9. Property group (seeded by CSV import)
DELETE FROM properties_list WHERE name = 'Clearview Heights TEST';
```