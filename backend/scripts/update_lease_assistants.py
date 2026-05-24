"""
One-shot script — patches all existing VAPI lease assistants with the current
system prompt and tool schema from vapi_agent_config.py.

Run from the backend/ directory:
    python scripts/update_lease_assistants.py
"""
import os
import sys
import json
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from supabase import create_client
from app.services.vapi_agent_config import build_lease_config, build_lease_config_shared

VAPI_API_BASE = "https://api.vapi.ai"
VAPI_TOKEN = os.environ["PRIVATE_VAPI_API"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
BACKEND_URL = os.environ.get("BACKEND_URL", "https://tenant-management-mvp.onrender.com")
SHARED_ASSISTANT_ID = os.environ.get("VAPI_SHARED_LEASE_ASSISTANT_ID")


def _strip_tool_role(tools: list) -> list:
    cleaned = []
    for tool in tools:
        t = dict(tool)
        if "messages" in t:
            t["messages"] = [
                {k: v for k, v in m.items() if k in ("type", "content")}
                for m in t["messages"]
            ]
        cleaned.append(t)
    return cleaned


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
    if "server_messages" in new_config:
        payload["serverMessages"] = new_config["server_messages"]
    resp = httpx.patch(
        f"{VAPI_API_BASE}/assistant/{assistant_id}",
        headers={
            "Authorization": f"Bearer {VAPI_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if resp.status_code == 200:
        print(f"  [OK] {label} — assistant {assistant_id} updated")
    else:
        print(f"  [FAIL] {label} — {resp.status_code}: {resp.text[:300]}")


def main():
    db = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    rows = (
        db.table("manager_vapi_config")
        .select("manager_id, vapi_lease_assistant_id, vapi_provisioning_status")
        .eq("vapi_provisioning_status", "active")
        .execute()
    )

    if not rows.data:
        print("No active manager VAPI configs found.")
    else:
        print(f"Found {len(rows.data)} active manager(s).")
        for row in rows.data:
            manager_id = row["manager_id"]
            assistant_id = row["vapi_lease_assistant_id"]
            if not assistant_id:
                print(f"  [SKIP] manager {manager_id} — no assistant ID stored")
                continue
            cfg = build_lease_config(BACKEND_URL, manager_id)
            patch_assistant(assistant_id, cfg, f"manager {manager_id[:8]}")

    if SHARED_ASSISTANT_ID:
        print(f"\nUpdating shared lease assistant {SHARED_ASSISTANT_ID}...")
        cfg = build_lease_config_shared(BACKEND_URL)
        patch_assistant(SHARED_ASSISTANT_ID, cfg, "shared lease agent")
    else:
        print("\nNo VAPI_SHARED_LEASE_ASSISTANT_ID in .env — skipping shared agent.")


if __name__ == "__main__":
    main()
