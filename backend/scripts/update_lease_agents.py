"""
Push the latest vapi_agent_config.py config to all active lease agents:
  - Per-manager agents (from manager_vapi_config table)
  - Shared lease agent (from VAPI_SHARED_LEASE_ASSISTANT_ID env var)

Uses direct HTTP PATCH (not the VAPI SDK) — the SDK silently drops firstMessageMode
and other fields that aren't in its Pydantic discriminated-union types.

Run from the project root:
    python backend/scripts/update_lease_agents.py [--dry-run]

Requires .env with SUPABASE_URL, SUPABASE_SERVICE_KEY, PRIVATE_VAPI_API, VAPI_SHARED_LEASE_ASSISTANT_ID.
"""
import os
import sys
import argparse
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from supabase import create_client

from app.config import settings
from app.services.vapi_agent_config import build_lease_config, build_lease_config_shared

BACKEND_URL = "https://tenant-management-mvp.onrender.com"
VAPI_API_BASE = "https://api.vapi.ai"
EXPECTED_SERVER_MESSAGES = ["end-of-call-report"]


def _to_vapi_payload(cfg: dict) -> dict:
    """Convert snake_case config dict to camelCase VAPI REST payload."""
    payload = {
        "name": cfg.get("name"),
        "firstMessageMode": cfg.get("first_message_mode"),
        "voicemailMessage": cfg.get("voicemail_message"),
        "endCallMessage": cfg.get("end_call_message"),
        "endCallPhrases": cfg.get("end_call_phrases"),
        "backgroundSound": cfg.get("background_sound"),
        "transcriber": cfg.get("transcriber"),
        "voice": cfg.get("voice"),
        "model": cfg.get("model"),
        "server": cfg.get("server"),
        "serverMessages": cfg.get("server_messages"),
        "analysisPlan": cfg.get("analysis_plan"),
        "startSpeakingPlan": cfg.get("start_speaking_plan"),
        "stopSpeakingPlan": cfg.get("stop_speaking_plan"),
        "backgroundSpeechDenoisingPlan": cfg.get("background_speech_denoising_plan"),
    }
    return {k: v for k, v in payload.items() if v is not None}


def update_and_verify(assistant_id: str, cfg: dict, label: str, dry_run: bool, headers: dict) -> bool:
    print(f"\n  [{label}]  id={assistant_id}")
    if dry_run:
        print(f"    DRY RUN — would update with name={cfg.get('name')}")
        return True

    payload = _to_vapi_payload(cfg)
    try:
        resp = httpx.patch(
            f"{VAPI_API_BASE}/assistant/{assistant_id}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"    [FAIL] HTTP {resp.status_code}: {resp.text[:200]}")
            return False

        data = resp.json()
        actual_sm = data.get("serverMessages")
        fmm = data.get("firstMessageMode")
        tools = data.get("model", {}).get("tools", [])
        tool_names = [t.get("name") or t.get("function", {}).get("name") for t in tools]

        if actual_sm != EXPECTED_SERVER_MESSAGES:
            print(f"    [FAIL] serverMessages={actual_sm} — expected {EXPECTED_SERVER_MESSAGES}")
            return False

        print(f"    [OK]  name={data.get('name')}  serverMessages={actual_sm}")
        print(f"          firstMessageMode={fmm}  tools={tool_names}")
        return True

    except Exception as e:
        print(f"    [FAIL] {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without executing")
    args = parser.parse_args()

    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    headers = {
        "Authorization": f"Bearer {settings.PRIVATE_VAPI_API}",
        "Content-Type": "application/json",
    }

    shared_id = os.environ.get("VAPI_SHARED_LEASE_ASSISTANT_ID", "")

    rows = (
        db.table("manager_vapi_config")
        .select("manager_id, vapi_lease_assistant_id")
        .eq("vapi_provisioning_status", "active")
        .execute()
    )
    agents = rows.data or []

    print(f"Lease agents to update: {len(agents)} per-manager + {'1 shared' if shared_id else '0 shared'}")
    print(f"Backend URL: {BACKEND_URL}")
    if args.dry_run:
        print("DRY RUN mode — no changes will be made")
    print("=" * 60)

    success = 0
    failed = 0

    for row in agents:
        manager_id = row["manager_id"]
        assistant_id = row.get("vapi_lease_assistant_id")
        if not assistant_id:
            print(f"\n  [{manager_id[:8]}]  SKIP — no assistant_id in DB")
            continue
        profile = db.table("manager_profiles").select("name").eq("user_id", manager_id).maybe_single().execute()
        manager_name = (profile.data or {}).get("name") or "our property management team"
        cfg = build_lease_config(BACKEND_URL, manager_id, manager_name=manager_name)
        ok = update_and_verify(assistant_id, cfg, manager_id[:8], args.dry_run, headers)
        if ok:
            success += 1
        else:
            failed += 1

    if shared_id:
        cfg = build_lease_config_shared(BACKEND_URL)
        ok = update_and_verify(shared_id, cfg, "shared", args.dry_run, headers)
        if ok:
            success += 1
        else:
            failed += 1
    else:
        print("\n  [shared]  SKIP — VAPI_SHARED_LEASE_ASSISTANT_ID not set")

    print("\n" + "=" * 60)
    print(f"Done. {success} updated, {failed} failed.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
