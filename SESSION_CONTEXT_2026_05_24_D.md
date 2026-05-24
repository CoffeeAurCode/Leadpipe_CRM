# Session Context — 2026-05-24 (Session D)

## What Happened

### 1. Reverted to commit f39e8d09
Discarded 9 commits (e8f5b1a6 → e0f9c5e2) that contained broken/experimental VAPI changes.
Files reverted: `leasing.py`, `voice.py`, `vapi_agent_config.py`, `LeadDetailModal.jsx`, plus diagnostic docs and a patch script.

The reverted code already had these features correctly implemented (they survived the revert):
- `submit_lease_lead` as `apiRequest` → `/voice/lease-lead-direct` (not a `function` type)
- `_lease_assistant_shell` with `server_messages: ["end-of-call-report"]`
- `/voice/lease-eoc-webhook` endpoint for EOC events
- `/voice/lease-lead-direct` endpoint for lead capture

### 2. Duplicate VAPI agents diagnosed and fixed

**Root cause**: `vapi_provisioning.py:provision_vapi_for_manager` always called `client.assistants.create()` on every retry. If a prior run created an assistant but failed before writing `status=active` to DB, re-running would create a duplicate.

**Code fix** (`backend/app/services/vapi_provisioning.py`):
- Now selects `vapi_lease_assistant_id` in the initial DB query
- If an assistant ID already exists in DB, calls `client.assistants.update()` instead of `create()`

**Cleanup script** (`backend/scripts/cleanup_duplicate_lease_agents.py`):
- Lists all VAPI agents named `Lease Agent [...]` or `Shared Lease Agent`
- Keeps only IDs that are `status=active` in `manager_vapi_config` (+ `VAPI_SHARED_LEASE_ASSISTANT_ID`)
- `--dry-run` flag to preview before deleting

### 3. Implemented hardening plan (from diagnosis_commit_d7ecf8f5 fix plan.md)

**`backend/app/services/vapi_agent_config.py`**:
- `build_assistant_config` (legacy): `server_messages` reduced to `["end-of-call-report", "tool-calls"]`
- `build_complaint_config`: same
- `_lease_assistant_shell`: was already `["end-of-call-report"]` — left as-is
- Added comments above each `server_messages` explaining why that list is used

**`backend/app/routes/voice.py`**:
- Added `[DEPRECATED]` print at top of `lease_lead_webhook` — keeps it alive for in-flight calls but logs when it's hit

**`backend/scripts/update_lease_agents.py`** (rewritten):
- Now handles both per-manager agents (from DB) AND shared lease agent (`VAPI_SHARED_LEASE_ASSISTANT_ID`)
- `--dry-run` flag
- After each update, asserts `serverMessages == ["end-of-call-report"]` — exits non-zero if VAPI ignored the change

**`backend/scripts/update_shared_agents.py`**:
- Added per-agent `server_messages` validation after update
- Complaint agent expects `["end-of-call-report", "tool-calls"]`
- Shared lease agent expects `["end-of-call-report"]`

**Deleted** `backend/scripts/update_lease_assistants.py`:
- Was a raw httpx script used for debugging; redundant now that `update_lease_agents.py` handles everything

---

## VAPI Architecture Summary (current state)

| Agent | server_messages | server URL | Lead tool type |
|---|---|---|---|
| Complaint Agent | `["end-of-call-report", "tool-calls"]` | `/voice/webhook` | `function` (submit_complaint) |
| Lease Agent (per-manager) | `["end-of-call-report"]` | `/voice/lease-eoc-webhook` | `apiRequest` → `/voice/lease-lead-direct` |
| Shared Lease Agent | `["end-of-call-report"]` | `/voice/lease-eoc-webhook` | `apiRequest` → `/voice/lease-lead-direct` |

**Why this matters**: VAPI routes `function-call` and `tool-calls` events to the `server URL`. The lease agent's server URL (`/voice/lease-eoc-webhook`) only handles `end-of-call-report`. If `tool-calls` is in `server_messages`, VAPI fires tool-call events at that endpoint which returns 200 with no result, silently breaking all tools. The fix: `submit_lease_lead` is now `apiRequest` (bypasses server routing entirely) and only `end-of-call-report` is in `server_messages`.

---

## Scripts Reference

```bash
# Delete orphaned duplicate VAPI agents (run once)
py -3.13 backend/scripts/cleanup_duplicate_lease_agents.py --dry-run
py -3.13 backend/scripts/cleanup_duplicate_lease_agents.py

# Push config to all lease agents (per-manager + shared)
py -3.13 backend/scripts/update_lease_agents.py

# Push config to complaint + shared agents
py -3.13 backend/scripts/update_shared_agents.py
```

---

## Pre-Testing Checklist
See below.
