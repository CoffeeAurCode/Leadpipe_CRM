#!/usr/bin/env python3
"""
One-time setup: create (or update) VAPI assistants for complaint and shared lease agents,
then patch .env with the returned IDs.

Run from the backend/ directory:
    py -3.13 scripts/setup_vapi_agents.py

VAPI tool URLs always use the production backend URL regardless of the local BACKEND_URL env var.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from vapi import Vapi, UpdateVapiPhoneNumberDto
from vapi.core.api_error import ApiError

from app.services.vapi_agent_config import build_complaint_config, build_lease_config_shared

VAPI_API_KEY        = os.environ.get("PRIVATE_VAPI_API", "")
EXISTING_NUMBER_ID  = os.environ.get("VAPI_NUMBER_ID", "")
# Always use the production URL for VAPI tool webhook URLs
VAPI_BACKEND_URL    = "https://tenant-management-mvp.onrender.com"
ENV_PATH            = Path(__file__).resolve().parent.parent / ".env"

# If these are set, update rather than create
EXISTING_COMPLAINT_ID = os.environ.get("VAPI_COMPLAINT_ASSISTANT_ID", "")
EXISTING_LEASE_ID     = os.environ.get("VAPI_SHARED_LEASE_ASSISTANT_ID", "")


def patch_env(key: str, value: str):
    content = ENV_PATH.read_text(encoding="utf-8")
    pattern = rf"^{re.escape(key)}=.*$"
    new_line = f"{key}={value}"
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content = content.rstrip("\n") + f"\n{new_line}\n"
    ENV_PATH.write_text(content, encoding="utf-8")
    print(f"  .env updated: {new_line}")


def upsert_assistant(client: Vapi, label: str, existing_id: str, cfg: dict) -> str:
    if existing_id:
        print(f"  Updating existing assistant {existing_id}...")
        try:
            result = client.assistants.update(id=existing_id, **cfg)
            print(f"  OK: {result.id}  name={result.name}")
            return result.id
        except ApiError as e:
            print(f"  Update failed ({e.status_code}), will create new...")
    print(f"  Creating new assistant for {label}...")
    try:
        result = client.assistants.create(**cfg)
        print(f"  OK: {result.id}  name={result.name}")
        return result.id
    except ApiError as e:
        print(f"  FAILED {e.status_code}: {e.body}")
        sys.exit(1)


def main():
    if not VAPI_API_KEY:
        print("[ERROR] PRIVATE_VAPI_API not set in .env")
        sys.exit(1)

    client = Vapi(token=VAPI_API_KEY)

    print("=" * 60)
    print("VAPI Voice Agent Setup")
    print(f"  Tool URLs will point to: {VAPI_BACKEND_URL}")
    print("=" * 60)

    # ── 1. Complaint assistant ─────────────────────────────────────
    print("\n[1/3] Complaint assistant (Alex)...")
    complaint_cfg = build_complaint_config(VAPI_BACKEND_URL)
    complaint_id = upsert_assistant(client, "Complaint", EXISTING_COMPLAINT_ID, complaint_cfg)

    # ── 2. Link existing VAPI phone number to complaint assistant ──
    if EXISTING_NUMBER_ID:
        print(f"\n[2/3] Linking phone {EXISTING_NUMBER_ID} to complaint assistant...")
        try:
            client.phone_numbers.update(
                id=EXISTING_NUMBER_ID,
                request=UpdateVapiPhoneNumberDto(assistant_id=complaint_id),
            )
            print("  OK: phone linked.")
        except ApiError as e:
            print(f"  WARNING {e.status_code}: {e.body}")
            print("  Link manually in the VAPI dashboard if needed.")
    else:
        print("\n[2/3] No VAPI_NUMBER_ID set — skipping phone link.")

    # ── 3. Shared lease assistant ──────────────────────────────────
    print("\n[3/3] Shared lease assistant...")
    lease_cfg = build_lease_config_shared(VAPI_BACKEND_URL)
    lease_id = upsert_assistant(client, "Shared Lease", EXISTING_LEASE_ID, lease_cfg)

    # ── 4. Patch .env ──────────────────────────────────────────────
    print("\n[4/4] Patching .env...")
    patch_env("VAPI_COMPLAINT_ASSISTANT_ID", complaint_id)
    patch_env("VAPI_COMPLAINT_NUMBER_ID", EXISTING_NUMBER_ID)
    patch_env("VAPI_SHARED_LEASE_ASSISTANT_ID", lease_id)
    patch_env("VAPI_SHARED_LEASE_NUMBER_ID", "")

    print("\n" + "=" * 60)
    print("Done.")
    print(f"  VAPI_COMPLAINT_ASSISTANT_ID    = {complaint_id}")
    print(f"  VAPI_COMPLAINT_NUMBER_ID       = {EXISTING_NUMBER_ID}")
    print(f"  VAPI_SHARED_LEASE_ASSISTANT_ID = {lease_id}")
    print(f"  VAPI_SHARED_LEASE_NUMBER_ID    = (empty - link Twilio in VAPI dashboard)")
    print("=" * 60)
    print("\nNext: restart the backend to pick up the new env vars.")


if __name__ == "__main__":
    main()
