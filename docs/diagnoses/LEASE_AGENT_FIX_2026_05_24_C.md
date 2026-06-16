# Lease Agent Fix — 2026-05-24 (Test C)

## Change 1 — `update_lease_assistants.py` (critical, deploy + re-run required)

Add `server_messages` to the VAPI PATCH payload inside `patch_assistant`.

**File:** `backend/scripts/update_lease_assistants.py`

```diff
 def patch_assistant(assistant_id: str, new_config: dict, label: str):
     model_block = new_config.get("model", {})
     payload = {
         "model": {
             "provider": model_block.get("provider", "openai"),
             "model": model_block.get("model", "gpt-4o-mini"),
             "messages": model_block.get("messages", []),
             "tools": _strip_tool_role(model_block.get("tools", [])),
         }
     }
     if "server" in new_config:
         payload["server"] = new_config["server"]
+    if "server_messages" in new_config:
+        payload["serverMessages"] = new_config["server_messages"]
     resp = httpx.patch(
```

**Why `serverMessages` (camelCase)?** VAPI's REST API uses camelCase field names. The Python config dict uses `server_messages` (snake_case) but the PATCH body must match VAPI's JSON field name `serverMessages`.

---

## Change 2 — `leasing.py` (secondary bug — apply after Change 1 is confirmed working)

`find_listing` returns at most 1 result for flat_number and title matches. A building-name query that falls through to the address fallback gets up to 20, which is fine. But the first two paths need to return all matches, not just the first.

**File:** `backend/app/routes/leasing.py`

```diff
-        results = q.ilike("flat_number", f"%{query}%").limit(1).execute()
+        results = q.ilike("flat_number", f"%{query}%").limit(20).execute()

         if not results.data:
             ...
-            results = fallback_q.execute()
+            results = fallback_q.limit(20).execute()
```

(The third fallback — address search — already uses `.limit(20)`, no change needed there.)

---

## Deployment Steps

### Step 1 — Apply Change 1 to the code

Edit `backend/scripts/update_lease_assistants.py` as shown above.

### Step 2 — Run the update script locally

```bash
cd backend
python scripts/update_lease_assistants.py
```

Expected output for each assistant:
```
[OK] manager 28c43c77 — assistant c76a69ea-... updated
[OK] manager 7fb0c018 — assistant 70a03059-... updated
[OK] shared lease agent — assistant 2dba3a50-... updated
```

If any `[FAIL]` lines appear, the `serverMessages` key may need a different spelling — check VAPI's API response body for the correct field name. Fallback: try `"server_messages"` (snake_case) if `"serverMessages"` is rejected.

### Step 3 — Commit and push to Render

Change 1 (the script) does not affect Render runtime — it's a one-shot local script. The push to Render is only needed if Change 2 is also applied (leasing.py is runtime code).

### Step 4 — Place a test call

Wait 3 minutes after "Your service is live 🎉" before calling.

**Verification — Render logs must show within 20s of the call connecting:**
```
GET /leasing/find-listing?query=...       ← find_listing called ✓
GET /leasing/search?bedrooms=...          ← search_available_listings called ✓
POST /voice/lease-lead-webhook            ← lead captured ✓
POST /voice/lease-eoc-webhook             ← EOC fallback fired (optional, only if lead wasn't saved above) ✓
```

If tools are still blocked after Step 2, log into the VAPI dashboard, open the assistant, and verify that "Server Messages" shows only `end-of-call-report`. If other events appear, remove them manually.

---

## Why This Is Safe (No Regressions)

- **Complaint agent:** Not touched. Has its own `build_complaint_config` path which does not use `patch_assistant`.
- **`server` URL in VAPI:** Already correct from Session B — no change needed.
- **System prompt / tools:** The update script re-sends these too; they are identical to what's live, so no change in behavior there.
- **EOC fallback webhook:** Already deployed and working. The only effect of fixing `server_messages` is that VAPI stops sending non-EOC events to it, which is exactly what we want.
- **`find_listing` limit change:** Changing `limit(1)` to `limit(20)` on a read-only query cannot break writes. It can only return more results than before — the LLM prompt already says to present all of them.
