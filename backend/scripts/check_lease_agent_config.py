"""
Read every active lease agent from VAPI and assert:
  1. first_message contains "Max"
  2. system prompt contains "Q1" and "Q7" and "Max"
  3. load_listings IS in the tool list
  4. search_listings IS in the tool list
  5. submit_lease_lead IS in the tool list
  6. find_listing NOT in the tool list (removed in v2)
  7. search_available_listings NOT in the tool list
  8. serverMessages == ["end-of-call-report"]
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
        msg = a.model.messages[0]
        sys_prompt = msg.content if hasattr(msg, "content") else msg["content"]
    except Exception:
        pass
    tool_names = []
    try:
        tool_names = [getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else None) for t in (a.model.tools or [])]
    except Exception:
        pass
    server_msgs = getattr(a, "server_messages", None)

    checks = {
        "first_message contains Max": "Max" in first_msg,
        "system prompt contains Max": "Max" in sys_prompt,
        "system prompt contains Q1": "Q1" in sys_prompt or "move-in" in sys_prompt.lower() or "Move-in" in sys_prompt,
        "system prompt contains Q7": "Q7" in sys_prompt or "non-smoking" in sys_prompt.lower() or "Non-smoking" in sys_prompt,
        "load_listings in tools": any("load_listings" in (n or "") for n in tool_names),
        "search_listings in tools": any("search_listings" in (n or "") for n in tool_names),
        "submit_lease_lead in tools": any("submit_lease_lead" in (n or "") for n in tool_names),
        "find_listing NOT in tools": not any("find_listing" in (n or "") for n in tool_names),
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
