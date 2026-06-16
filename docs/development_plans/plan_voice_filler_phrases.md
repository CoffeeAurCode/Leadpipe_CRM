# Plan: Add Filler Phrases to Voice Agent Tool Calls

## Problem

Both the complaint agent and lease agent go silent while VAPI makes HTTP calls to the backend (DB lookups, phone verification, listing searches). These pauses feel broken to callers.

## Solution

VAPI tool definitions support a `messages` array. Each entry fires at a specific lifecycle point:

| `type` | When it fires |
|---|---|
| `request-start` | Immediately when the HTTP call begins — **use this for filler** |
| `request-response-delayed` | If the response takes longer than `timingMilliseconds` |
| `request-complete` | After a successful response |
| `request-failed` | After a failed response |

Adding a `request-start` message with `"role": "assistant"` causes the LLM to **speak that phrase** before the silence.

---

## File to Edit

**`backend/app/services/vapi_agent_config.py`**

There are two tool-builder functions:
- `build_complaint_tools(backend_url)` — 6 tools (lines ~707–876)
- `_build_lease_tools(backend_url, manager_id)` — 3 tools (lines ~1020–1139)

---

## Changes Per Tool

Each tool gets a `"messages"` key added at the top level of its dict. The phrases should be:
- Natural and conversational
- Bilingual (English first, then French, matching the agent's existing bilingual pattern)
- Under ~10 words each (agents speak fast; filler shouldn't be a monologue)

### Complaint Agent Tools

| Tool | Filler Phrase (EN / FR) |
|---|---|
| `verify_phone_number` | "One moment while I verify that for you. / Un instant, je vérifie ça." |
| `check_availability` | "Let me check that time slot for you. / Laissez-moi vérifier ce créneau." |
| `view_active_appointments` | "Give me a second to pull up your appointments. / Un instant, je récupère vos rendez-vous." |
| `update_appointment` | "Just a moment while I update that. / Un instant pendant que je mets ça à jour." |
| `cancel_appointment` | "One moment while I cancel that for you. / Un instant, j'annule ça pour vous." |
| `submit_complaint` | "Let me get that logged for you right away. / Je l'enregistre pour vous tout de suite." |

### Lease Agent Tools

| Tool | Filler Phrase (EN / FR) |
|---|---|
| `find_listing` | "Give me a second to look that up. / Un instant, je cherche ça." |
| `search_available_listings` | "Let me search our available units for you. / Laissez-moi chercher les unités disponibles." |
| `submit_lease_lead` | "Just a moment while I save your information. / Un instant pendant que j'enregistre vos informations." |

---

## Message Block Format

Add this structure inside each tool dict (alongside `"name"`, `"url"`, `"method"`, etc.):

```python
"messages": [
    {
        "type": "request-start",
        "content": "<filler phrase here>",
        "role": "assistant",
        "endCallAfterSpoken": False,
    }
]
```

For tools where the backend can be slow (webhook/async tools like `submit_complaint` and `submit_lease_lead`), also add a delayed fallback:

```python
"messages": [
    {
        "type": "request-start",
        "content": "<filler phrase>",
        "role": "assistant",
        "endCallAfterSpoken": False,
    },
    {
        "type": "request-response-delayed",
        "content": "Still working on it, just another moment.",
        "timingMilliseconds": 3000,
        "role": "assistant",
        "endCallAfterSpoken": False,
    }
]
```

---

## Implementation Steps

1. Open `backend/app/services/vapi_agent_config.py`
2. In `build_complaint_tools()`: add `"messages"` to each of the 6 tool dicts
3. In `_build_lease_tools()`: add `"messages"` to each of the 3 tool dicts
4. Re-provision any live VAPI assistants so the new config is pushed (call `provision_vapi_for_manager()` or equivalent re-deploy)

---

## Notes

- No backend route changes needed — this is purely config in `vapi_agent_config.py`
- The `request-start` message fires client-side in VAPI's runtime; the backend never sees it
- Existing `"messages"` fields in tools are currently `[]` (empty) — just populate them
- Keep phrases short: VAPI starts speaking immediately and the DB call usually resolves in < 1 s
