"""
Push the latest vapi_agent_config.py config to the two live shared agents:
  - Complaint agent  (VAPI_COMPLAINT_ASSISTANT_ID  → +14382314283)
  - Shared lease agent (VAPI_SHARED_LEASE_ASSISTANT_ID → +14313415768)

Only updates assistant configs. Phone number bindings already exist and are
not touched — reassigning them is unnecessary and risky.

Run from the project root:
    python backend/scripts/update_shared_agents.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from vapi import Vapi
from vapi.core.api_error import ApiError

from app.services.vapi_agent_config import build_complaint_config, build_lease_config_shared

VAPI_API_KEY             = os.environ.get("PRIVATE_VAPI_API", "")
COMPLAINT_ASSISTANT_ID   = os.environ.get("VAPI_COMPLAINT_ASSISTANT_ID", "")
LEASE_ASSISTANT_ID       = os.environ.get("VAPI_SHARED_LEASE_ASSISTANT_ID", "")
BACKEND_URL              = "https://tenant-management-mvp.onrender.com"


def check_env():
    missing = {k: v for k, v in {
        "PRIVATE_VAPI_API": VAPI_API_KEY,
        "VAPI_COMPLAINT_ASSISTANT_ID": COMPLAINT_ASSISTANT_ID,
        "VAPI_SHARED_LEASE_ASSISTANT_ID": LEASE_ASSISTANT_ID,
    }.items() if not v}
    if missing:
        print(f"ERROR: missing env vars: {', '.join(missing)}")
        sys.exit(1)


def update_assistant(client: Vapi, label: str, assistant_id: str, cfg: dict, expected_server_messages: list):
    print(f"\n[{label}]")
    print(f"  assistant_id : {assistant_id}")
    try:
        result = client.assistants.update(id=assistant_id, **cfg)
        actual = getattr(result, "server_messages", None)
        if actual != expected_server_messages:
            print(f"  [FAIL] serverMessages = {actual} — expected {expected_server_messages}")
            sys.exit(1)
        print(f"  [OK]  name={result.name}  serverMessages={actual}")
    except ApiError as e:
        print(f"  FAILED {e.status_code}: {e.body}")
        sys.exit(1)
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)


def main():
    check_env()

    client = Vapi(token=VAPI_API_KEY)

    print("=" * 60)
    print("Updating shared VAPI agents with new voice config")
    print(f"  Backend URL: {BACKEND_URL}")
    print("=" * 60)

    update_assistant(
        client,
        "Complaint agent (+14382314283)",
        COMPLAINT_ASSISTANT_ID,
        build_complaint_config(BACKEND_URL),
        expected_server_messages=["end-of-call-report", "tool-calls"],
    )

    update_assistant(
        client,
        "Shared lease agent (+14313415768)",
        LEASE_ASSISTANT_ID,
        build_lease_config_shared(BACKEND_URL),
        expected_server_messages=["end-of-call-report"],
    )

    print("\n" + "=" * 60)
    print("Done. Both assistants updated.")
    print("Phone number bindings were not changed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
