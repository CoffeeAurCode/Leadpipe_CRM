"""
Deploy / sync the Vapi voice agent to the Vapi cloud.

Usage (from the backend/ directory):
    python -m scripts.deploy_vapi_agent

What it does:
  1. Loads config from .env
  2. Connects to Vapi via the Python SDK
  3. Updates the existing assistant with the Python-defined config
  4. Binds the updated assistant to the purchased phone number

Required .env variables:
    PRIVATE_VAPI_API      — Vapi server-side API key
    VAPI_ASSISTANT_ID     — ID of the existing assistant to update
    VAPI_NUMBER_ID        — Vapi phone number ID to bind to
    BACKEND_URL           — Public base URL of this backend (for tool webhook URLs)
"""

import os
import sys
from pathlib import Path

# Allow running as `python -m scripts.deploy_vapi_agent` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from vapi import Vapi, UpdateVapiPhoneNumberDto
from vapi.core.api_error import ApiError

from app.services.vapi_agent_config import build_assistant_config

# ---------------------------------------------------------------------------
# Load required env vars
# ---------------------------------------------------------------------------
VAPI_API_KEY    = os.environ.get("PRIVATE_VAPI_API", "")
ASSISTANT_ID    = os.environ.get("VAPI_ASSISTANT_ID", "")
PHONE_NUMBER_ID = os.environ.get("VAPI_NUMBER_ID", "")
BACKEND_URL     = os.environ.get("BACKEND_URL", "")

def _check_env():
    missing = [k for k, v in {
        "PRIVATE_VAPI_API": VAPI_API_KEY,
        "VAPI_ASSISTANT_ID": ASSISTANT_ID,
        "VAPI_NUMBER_ID": PHONE_NUMBER_ID,
        "BACKEND_URL": BACKEND_URL,
    }.items() if not v]
    if missing:
        print(f"[ERROR] Missing required env vars: {', '.join(missing)}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------
def deploy():
    _check_env()

    print("=" * 60)
    print("Vapi Agent Deploy Script")
    print("=" * 60)
    print(f"  Assistant ID : {ASSISTANT_ID}")
    print(f"  Phone Number : {PHONE_NUMBER_ID}")
    print(f"  Backend URL  : {BACKEND_URL}")
    print()

    client = Vapi(token=VAPI_API_KEY)
    config = build_assistant_config()

    # ── Step 1: Update the assistant ────────────────────────────────────────
    print("[1/2] Updating assistant on Vapi...")
    try:
        updated = client.assistants.update(id=ASSISTANT_ID, **config)
        print(f"  [OK] Assistant updated: {updated.id}")
        print(f"       Name: {updated.name}")
    except ApiError as e:
        print(f"  [ERROR] Vapi API error {e.status_code}: {e.body}")
        sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] Unexpected error: {e}")
        sys.exit(1)

    # ── Step 2: Bind assistant to phone number ───────────────────────────────
    print(f"[2/2] Binding assistant to phone number {PHONE_NUMBER_ID}...")
    try:
        phone = client.phone_numbers.update(
            id=PHONE_NUMBER_ID,
            request=UpdateVapiPhoneNumberDto(assistant_id=ASSISTANT_ID),
        )
        print(f"  [OK] Phone number bound: {getattr(phone, 'number', PHONE_NUMBER_ID)}")
    except ApiError as e:
        print(f"  [ERROR] Vapi API error {e.status_code}: {e.body}")
        sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] Unexpected error: {e}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("Deploy complete.")
    print(f"  Assistant ID : {ASSISTANT_ID}")
    print("  Test: make a call to the Vapi number and verify the agent.")
    print("=" * 60)


if __name__ == "__main__":
    deploy()
