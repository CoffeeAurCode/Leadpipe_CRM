# Why We Run `python -m scripts.reprovision_existing_groups`

## The Problem This Solves

When a prospective tenant calls our leasing phone number, the lease agent should only show them listings that belong to the manager who owns that number. That is the core requirement: **one phone number → one manager → only that manager's listings**.

We achieve this by giving every property group its own dedicated VAPI phone number and its own dedicated lease assistant. When the assistant is created, we hardcode `?property_group_id=<uuid>` directly into its tool URLs. This means every search the assistant makes is scoped at the VAPI level — it is physically impossible for the agent to return listings from a different manager.

The problem is that this provisioning system was built after the product already existed. Property groups created before this feature were never provisioned. They have no dedicated phone number, no dedicated assistant. Any call they receive goes through the old **shared** agent, which has no `property_group_id` in its tool URLs and therefore searches across every manager's listings in the database. This is wrong.

The script exists to fix those pre-existing property groups by running the same provisioning logic that new groups get automatically.

---

## What "Provisioning" Actually Means

Provisioning a property group does three things via the VAPI API:

1. **Creates a new lease assistant** — a full VAPI assistant configured with our lease agent system prompt, voice settings, and tool definitions. Crucially, `find_listing` and `search_available_listings` tool URLs are built with `?property_group_id=<this-group's-uuid>` baked in.

2. **Purchases a new phone number** — VAPI allocates a real phone number from its pool.

3. **Links the number to the assistant** — so that when someone calls that number, VAPI routes the call to that specific scoped assistant.

The three IDs are then written back to the `properties_list` row in Supabase:

| Column | What it stores |
|---|---|
| `vapi_lease_assistant_id` | VAPI assistant ID (used for assistant lookup) |
| `vapi_phone_number_id` | VAPI phone number ID (used for inbound routing) |
| `vapi_phone_number` | The actual E.164 number (shown to the manager in the UI) |
| `vapi_provisioning_status` | `pending` → `active` (or `failed`) |

After provisioning, the `properties_list` row is the source of truth for which phone number belongs to which manager.

---

## What the Script Does, Step by Step

```python
rows = (
    db.table("properties_list")
    .select("id, name, vapi_provisioning_status")
    .neq("vapi_provisioning_status", "active")
    .execute()
)
```

It queries Supabase for every property group that does not already have `vapi_provisioning_status = "active"`. This includes groups with status `not_applicable`, `pending`, `failed`, or NULL. It skips any group that was already successfully provisioned.

For each unprovisioned group, it calls `provision_vapi_for_property_group()` — the exact same function that runs automatically in the background when a manager creates a new property group today. Running the script is equivalent to having been there when those old property groups were created, but with the provisioning system already built.

If one group fails (e.g. VAPI returns an error), the script logs the failure, sets that group's status to `failed`, and continues to the next. It does not abort.

---

## Why the Command Is Written This Way

```
cd backend && python -m scripts.reprovision_existing_groups
```

**`cd backend`** — The script imports from `app.config`, `app.services.vapi_provisioning`, and `app.services.vapi_agent_config`. Python resolves those imports relative to where it is run from. If you run it from the repo root, Python looks for a folder called `app` there and fails. You must be inside `backend/` so that the `app/` package is importable.

**`python -m scripts.reprovision_existing_groups`** — The `-m` flag tells Python to run the file as a **module** inside a package, not as a standalone script. This matters because of relative imports.

When you run `python scripts/reprovision_existing_groups.py` (without `-m`), Python treats the file as a top-level script. `sys.path` does not include the directory as a package root in the same way, and imports like `from app.config import settings` can silently resolve differently or fail entirely depending on the environment.

When you run `python -m scripts.reprovision_existing_groups`, Python treats `scripts` as a package inside the current directory (`backend/`). It sets `sys.path` correctly so that `from app.config import settings` resolves to `backend/app/config.py`. This is the safe, reproducible way to run any module that imports from sibling packages.

The `.env` file in `backend/` is also loaded by the script via `dotenv`. Running from within `backend/` ensures `load_dotenv()` finds the right file.

---

## What Happens After the Script Runs

Each previously-unprovisioned property group now has its own phone number and scoped lease assistant. From this point:

- **Inbound calls** — A prospective tenant who calls a property group's number reaches only that group's scoped assistant. The assistant's tool URLs have `property_group_id` hardcoded, so it can only find that manager's listings.

- **Lead capture** — When the agent submits a lead via `submit_lease_lead`, the webhook resolves `property_group_id` by looking up the calling assistant's ID (`call.assistantId → properties_list.vapi_lease_assistant_id`). This always finds the correct row. The lead is stored with the correct `manager_id`.

- **No shared agent fallback** — With all groups provisioned, no call should ever fall through to the shared agent. The shared agent becomes a legacy artifact.

---

## When to Run This Script Again

Only once, to fix existing groups. You do not need to run it again for new property groups — provisioning happens automatically as a `BackgroundTask` in `POST /properties-list`.

The only reason to run it again would be if a property group's provisioning status shows `failed` (VAPI was down or the API key was wrong at the time of creation). In that case the script is safe to re-run — it skips groups that are already `active` and retries only the failed ones.

---

## Checklist Before Running

- [ ] You are in the `backend/` directory
- [ ] `backend/.env` exists and contains `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `PRIVATE_VAPI_API`, `BACKEND_URL`
- [ ] `BACKEND_URL` points to your deployed backend (not `localhost`) — VAPI needs a publicly reachable URL to call your tool endpoints
- [ ] You have enough VAPI credits to purchase phone numbers (one per unprovisioned group)
- [ ] Run `pip install -r requirements.txt` if you have not recently installed dependencies

```bash
cd backend
python -m scripts.reprovision_existing_groups
```

Watch the output for any `FAILED` lines. If a group fails, check the error message — the most common causes are an invalid `PRIVATE_VAPI_API` key or VAPI being temporarily unavailable. You can re-run the script safely to retry only the failed groups.
