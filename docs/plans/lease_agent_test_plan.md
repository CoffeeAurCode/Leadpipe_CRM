# Lease Agent Migration — Test Plan

Tests the changes described in `lease_agent_script_migration_plan.md`:
1. New Max / 7-question system prompt is live on all VAPI agents
2. Sidebar tab labels show "Complaint AI" and "Leasing AI"

---

## 1. Automated / Script Tests

### 1A. Dry-run deploy script

```bash
python backend/scripts/update_lease_agents.py --dry-run
```

**Pass criteria:**
- Exit code 0
- Output lists all per-manager agents + shared agent
- Prints "DRY RUN — would update" for each (no actual changes)

---

### 1B. Live deploy + assertion

```bash
python backend/scripts/update_lease_agents.py
```

**Pass criteria:**
- Exit code 0
- Each agent prints `[OK] name=... serverMessages=['end-of-call-report']`
- No `[FAIL]` lines

---

### 1C. Verify agent config via VAPI REST API

For each agent ID in `manager_vapi_config.vapi_lease_assistant_id` (plus
`VAPI_SHARED_LEASE_ASSISTANT_ID`), run:

```bash
python backend/scripts/check_lease_agent_config.py
```

Create `backend/scripts/check_lease_agent_config.py` with this content:

```python
"""
Read every active lease agent from VAPI and assert:
  1. first_message contains "Max"
  2. system prompt contains "Q1" and "Q7" and "Max"
  3. search_available_listings is NOT in the tool list
  4. find_listing IS in the tool list
  5. submit_lease_lead IS in the tool list
  6. serverMessages == ["end-of-call-report"]
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from supabase import create_client
from vapi import Vapi
from app.config import settings

db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
client = Vapi(token=settings.PRIVATE_VAPI_API)
shared_id = os.environ.get("VAPI_SHARED_LEASE_ASSISTANT_ID", "")

rows = db.table("manager_vapi_config").select("vapi_lease_assistant_id").eq("vapi_provisioning_status", "active").execute()
ids = [r["vapi_lease_assistant_id"] for r in rows.data if r.get("vapi_lease_assistant_id")]
if shared_id:
    ids.append(shared_id)

failures = []
for aid in ids:
    a = client.assistants.get(id=aid)
    first_msg = getattr(a, "first_message", "") or ""
    sys_prompt = ""
    try:
        sys_prompt = a.model.messages[0]["content"]
    except Exception:
        pass
    tool_names = []
    try:
        tool_names = [t.get("function", {}).get("name") or t.get("name") for t in (a.model.tools or [])]
    except Exception:
        pass
    server_msgs = getattr(a, "server_messages", None)

    checks = {
        "first_message contains Max": "Max" in first_msg,
        "system prompt contains Max": "Max" in sys_prompt,
        "system prompt contains Q1": "Q1" in sys_prompt or "move-in" in sys_prompt.lower() or "Move-in" in sys_prompt,
        "system prompt contains Q7": "Q7" in sys_prompt or "non-smoking" in sys_prompt.lower() or "Non-smoking" in sys_prompt,
        "find_listing in tools": "find_listing" in tool_names or any("find_listing" in (n or "") for n in tool_names),
        "submit_lease_lead in tools": "submit_lease_lead" in tool_names or any("submit_lease_lead" in (n or "") for n in tool_names),
        "search_available_listings NOT in tools": not any("search_available_listings" in (n or "") for n in tool_names),
        "serverMessages correct": server_msgs == ["end-of-call-report"],
    }
    all_ok = all(checks.values())
    status = "OK" if all_ok else "FAIL"
    print(f"\n[{status}] {aid[:12]}")
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    if not all_ok:
        failures.append(aid)

print(f"\n{'='*60}")
print(f"Done. {len(ids)-len(failures)}/{len(ids)} passed.")
if failures:
    sys.exit(1)
```

Run with:

```bash
python backend/scripts/check_lease_agent_config.py
```

**Pass criteria:** Exit code 0, all checks PASS.

---

### 1D. Frontend i18n key check

```bash
grep -n "voiceStats\|leasing" frontend/src/i18n/en.json
```

**Expected output:**
```
"voiceStats": "Complaint AI",
"leasing": "Leasing AI",
```

```bash
grep -n "voiceStats\|leasing" frontend/src/i18n/fr-CA.json
```

**Expected output:**
```
"voiceStats": "Complaint AI",
"leasing": "Leasing AI",
```

---

### 1E. Frontend test suite

```bash
cd frontend && npm test -- --watchAll=false
```

**Pass criteria:** All existing tests pass. If `Sidebar.test.jsx` checks for the old label
strings ("Voice Stats", "Leasing"), update those assertions to "Complaint AI" and "Leasing AI".

---

## 2. Manual Tests

### 2A. Sidebar label verification (browser)

1. Start the dev server: `cd frontend && npm run dev`
2. Open the app in a browser and log in.
3. Verify the sidebar shows **"Complaint AI"** (was "Voice Stats") and **"Leasing AI"** (was "Leasing").
4. Switch language to French (FR toggle in the UI).
5. Verify the sidebar still shows **"Complaint AI"** and **"Leasing AI"** (brand names — same in both languages).

---

### 2B. Lease agent — English call (7-question flow)

Call the lease number and run through this script:

| Step | Caller says | Expected agent response |
|---|---|---|
| 1 | (call connects) | "Hey, thanks for calling! I'm Max…Which unit are you inquiring about?" |
| 2 | "Unit 101" | Looks up listing. Moves to Q1: "When are you looking to move in?" |
| 3 | "Next month" | Q2: "Is your current landlord aware that you're looking?" |
| 4 | "Yes" | Q3: "Do you have any questions about the unit itself?" |
| 5 | "What's the rent?" | Reads back monthly_rent from listing data |
| 5b | "No more questions" | Q4: "Are you currently employed?" |
| 6 | "Yes, full-time" | Q5: "How many people would be moving in with you?" |
| 7 | "Just me" | Q6: "Do you have any pets?" |
| 8 | "No" | Q7: "Just so you know, this is a non-smoking unit…Is that okay?" |
| 9 | "Yes, that's fine" | Asks for name, then confirms lead captured. Says goodbye. |

**Pass criteria:** Agent follows the 7-question structure, submits lead, ends call politely.

---

### 2C. Lease agent — Pet rejection

1. Call the lease number with a unit where `pets_allowed = "no"`.
2. When Q6 is asked, say "Yes, I have a dog."
3. **Expected:** "Unfortunately this unit doesn't allow pets."
4. Lead should be captured with `qualification_status = "not_qualified"`.

---

### 2D. Lease agent — French call

1. Call the lease number.
2. At the opening greeting, respond in French.
3. Verify agent locks to French for all 7 questions.
4. Verify no English/French mixing occurs.

---

### 2E. Lease agent — Unit not found

1. Call and say a unit number that does not exist (e.g. "Unit 9999").
2. **Expected:** Agent asks to confirm once, then if still not found, says it can't pull up
   that unit and closes the lead as "unmatched".

---

### 2F. Lease agent — Caller doesn't know unit number (address query)

1. Call and say "I saw an apartment on Maple Street, I'm not sure of the unit number."
2. **Expected:** Agent calls `find_listing` with the address query, reads back the
   matching unit(s), and continues with the 7-question flow.

---

### 2G. Lead appears in Leasing AI tab

1. After a test call (2B or 2C), open the app.
2. Navigate to **Leasing AI** tab.
3. **Expected:** New lead appears with caller name, unit, qualification_status, and answers.

---

## 3. Regression Checks

| Area | Check |
|---|---|
| Complaint agent | Still answers calls normally (separate agent — no changes) |
| Voice Stats / Complaint AI tab | Tab loads correctly, shows call stats |
| Leasing AI tab | Tab loads correctly, shows leads and listings |
| Sidebar navigation | All 10 nav items still navigate to correct views |
