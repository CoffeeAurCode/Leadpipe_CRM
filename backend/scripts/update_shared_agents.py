"""
Push the latest vapi_agent_config.py config to the two live shared agents:
  - Complaint agent  (VAPI_COMPLAINT_ASSISTANT_ID  → +14382567782)
  - Shared lease agent (VAPI_SHARED_LEASE_ASSISTANT_ID → +14313415768)

Only updates assistant configs. Phone number bindings already exist and are
not touched — reassigning them is unnecessary and risky.

Uses direct HTTP PATCH (not the VAPI SDK) — the SDK silently drops firstMessageMode,
apiRequest tool subfields, and other fields that aren't in its Pydantic types.
PATCH is a partial merge, so fields we don't send are left untouched.

Run from the project root:
    python backend/scripts/update_shared_agents.py [--dry-run]
"""
import os
import sys
import argparse
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services.vapi_agent_config import build_complaint_config, build_lease_config_shared

VAPI_API_KEY                    = os.environ.get("PRIVATE_VAPI_API", "")
COMPLAINT_ASSISTANT_ID          = os.environ.get("VAPI_COMPLAINT_ASSISTANT_ID", "")
COMPLAINT_FRENCH_ASSISTANT_ID   = os.environ.get("VAPI_COMPLAINT_FRENCH_ASSISTANT_ID", "")
LEASE_ASSISTANT_ID              = os.environ.get("VAPI_SHARED_LEASE_ASSISTANT_ID", "")
BACKEND_URL                     = "https://tenant-management-mvp.onrender.com"
VAPI_API_BASE                   = "https://api.vapi.ai"

# snake_case (vapi_agent_config) → camelCase (VAPI REST). Only keys present in a
# given config are sent; PATCH merge leaves everything else intact.
_KEY_MAP = {
    "name": "name",
    "first_message": "firstMessage",
    "first_message_mode": "firstMessageMode",
    "voicemail_message": "voicemailMessage",
    "end_call_message": "endCallMessage",
    "end_call_phrases": "endCallPhrases",
    "background_sound": "backgroundSound",
    "transcriber": "transcriber",
    "voice": "voice",
    "model": "model",
    "server": "server",
    "server_messages": "serverMessages",
    "analysis_plan": "analysisPlan",
    "client_messages": "clientMessages",
    "start_speaking_plan": "startSpeakingPlan",
    "stop_speaking_plan": "stopSpeakingPlan",
    "background_speech_denoising_plan": "backgroundSpeechDenoisingPlan",
}


def _to_vapi_payload(cfg: dict) -> dict:
    payload = {}
    for snake, camel in _KEY_MAP.items():
        v = cfg.get(snake)
        if v is not None:
            payload[camel] = v
    return payload


def check_env():
    missing = {k: v for k, v in {
        "PRIVATE_VAPI_API": VAPI_API_KEY,
        "VAPI_COMPLAINT_ASSISTANT_ID": COMPLAINT_ASSISTANT_ID,
        "VAPI_SHARED_LEASE_ASSISTANT_ID": LEASE_ASSISTANT_ID,
    }.items() if not v}
    if missing:
        print(f"ERROR: missing env vars: {', '.join(missing)}")
        sys.exit(1)


def update_assistant(label: str, assistant_id: str, cfg: dict, expected_server_messages: list, dry_run: bool, headers: dict) -> bool:
    print(f"\n[{label}]")
    print(f"  assistant_id : {assistant_id}")
    if dry_run:
        names = [t.get("name") or t.get("function", {}).get("name") for t in cfg.get("model", {}).get("tools", [])]
        print(f"  DRY RUN — would update name={cfg.get('name')}  tools={names}")
        return True
    try:
        resp = httpx.patch(
            f"{VAPI_API_BASE}/assistant/{assistant_id}",
            headers=headers,
            json=_to_vapi_payload(cfg),
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"  [FAIL] HTTP {resp.status_code}: {resp.text[:300]}")
            return False
        data = resp.json()
        actual_sm = data.get("serverMessages")
        tools = data.get("model", {}).get("tools", [])
        names = [t.get("name") or t.get("function", {}).get("name") for t in tools]
        if actual_sm != expected_server_messages:
            print(f"  [FAIL] serverMessages={actual_sm} — expected {expected_server_messages}")
            return False
        print(f"  [OK]  name={data.get('name')}  serverMessages={actual_sm}")
        print(f"        firstMessageMode={data.get('firstMessageMode')}  tools={names}")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without executing")
    args = parser.parse_args()

    check_env()
    headers = {"Authorization": f"Bearer {VAPI_API_KEY}", "Content-Type": "application/json"}

    print("=" * 60)
    print("Updating shared VAPI agents with new voice config")
    print(f"  Backend URL: {BACKEND_URL}")
    if args.dry_run:
        print("  DRY RUN mode — no changes will be made")
    print("=" * 60)

    # Preserve the French handoff across redeploys: pass the French assistant id from env so the
    # PATCH does NOT strip the gated handoff tool + [French Routing] gate (mirrors update_lease_agents).
    ok1 = update_assistant(
        "Complaint agent (+14382567782)",
        COMPLAINT_ASSISTANT_ID,
        build_complaint_config(BACKEND_URL, french_assistant_id=COMPLAINT_FRENCH_ASSISTANT_ID or None),
        ["end-of-call-report", "tool-calls"],
        args.dry_run, headers,
    )
    ok2 = update_assistant(
        "Shared lease agent (+14313415768)",
        LEASE_ASSISTANT_ID,
        build_lease_config_shared(BACKEND_URL),
        ["end-of-call-report"],
        args.dry_run, headers,
    )

    print("\n" + "=" * 60)
    if ok1 and ok2:
        print("Done. Both assistants updated. Phone number bindings were not changed.")
    else:
        print("FAILED — see errors above.")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
