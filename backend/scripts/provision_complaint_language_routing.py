"""
Provision per-tenant language routing for the complaint agent (migration 032).

What it does:
  1. Creates (or patches in place) the ENGLISH-LOCKED complaint assistant
     (build_complaint_config_english) — id stored in env VAPI_COMPLAINT_ENGLISH_ASSISTANT_ID.
  2. With --route-number: switches the complaint phone number from the static entry-assistant
     binding to dynamic routing — clears assistantId and points server.url at
     POST /voice/inbound-router, which returns the assistant matching tenants.preferred_language.

ORDER MATTERS: run --route-number ONLY after the backend with /voice/inbound-router is live on
Render (and env vars VAPI_COMPLAINT_ENGLISH_ASSISTANT_ID / VAPI_COMPLAINT_FRENCH_ASSISTANT_ID are
set there). Until then inbound keeps working via the static entry binding.

The entry + FR assistants are patched by provision_complaint_french_handoff.py — re-run it after
changing build_complaint_tools (the verify URL now carries &language=).

Run from the project root (base python is fine):
    python backend/scripts/provision_complaint_language_routing.py --dry-run
    python backend/scripts/provision_complaint_language_routing.py                  # EN assistant only
    python backend/scripts/provision_complaint_language_routing.py --route-number   # + repoint number
    python backend/scripts/provision_complaint_language_routing.py --rollback       # static entry binding back

Requires .env: PRIVATE_VAPI_API, VAPI_COMPLAINT_ASSISTANT_ID, VAPI_COMPLAINT_NUMBER_ID.
"""
import os
import sys
import argparse
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.config import settings
from app.services.vapi_agent_config import build_complaint_config_english

BACKEND_URL = "https://tenant-management-mvp.onrender.com"
VAPI_API_BASE = "https://api.vapi.ai"


def _to_vapi_payload(cfg: dict) -> dict:
    payload = {
        "name": cfg.get("name"),
        "firstMessage": cfg.get("first_message"),
        "firstMessageMode": cfg.get("first_message_mode"),
        "voicemailMessage": cfg.get("voicemail_message"),
        "endCallMessage": cfg.get("end_call_message"),
        "endCallPhrases": cfg.get("end_call_phrases"),
        "backgroundSound": cfg.get("background_sound"),
        "transcriber": cfg.get("transcriber"),
        "voice": cfg.get("voice"),
        "model": cfg.get("model"),
        "serverMessages": cfg.get("server_messages"),
        "clientMessages": cfg.get("client_messages"),
        "startSpeakingPlan": cfg.get("start_speaking_plan"),
        "stopSpeakingPlan": cfg.get("stop_speaking_plan"),
        "backgroundSpeechDenoisingPlan": cfg.get("background_speech_denoising_plan"),
    }
    return {k: v for k, v in payload.items() if v is not None}


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.PRIVATE_VAPI_API}",
        "Content-Type": "application/json",
    }


def provision_english_assistant(dry_run: bool) -> str:
    cfg = build_complaint_config_english(BACKEND_URL)
    payload = _to_vapi_payload(cfg)
    existing = os.environ.get("VAPI_COMPLAINT_ENGLISH_ASSISTANT_ID", "")
    if existing:
        if dry_run:
            print(f"  DRY RUN — PATCH /assistant/{existing} (English complaint assistant)")
            return existing
        resp = httpx.patch(f"{VAPI_API_BASE}/assistant/{existing}", headers=_headers(), json=payload, timeout=30)
        if resp.status_code != 200:
            raise SystemExit(f"  [FAIL] patch English assistant HTTP {resp.status_code}: {resp.text[:300]}")
        print(f"  [OK] patched English complaint assistant  id={existing}")
        return existing
    if dry_run:
        print(f"  DRY RUN — POST /assistant  name={payload['name']}")
        return "<dry-run-english-id>"
    resp = httpx.post(f"{VAPI_API_BASE}/assistant", headers=_headers(), json=payload, timeout=30)
    if resp.status_code not in (200, 201):
        raise SystemExit(f"  [FAIL] create English assistant HTTP {resp.status_code}: {resp.text[:300]}")
    new_id = resp.json()["id"]
    print(f"  [OK] created English complaint assistant  id={new_id}")
    print(f"\n  >>> ADD TO .env / Render env:  VAPI_COMPLAINT_ENGLISH_ASSISTANT_ID={new_id}\n")
    return new_id


def route_number(dry_run: bool) -> None:
    number_id = os.environ.get("VAPI_COMPLAINT_NUMBER_ID", "")
    if not number_id:
        raise SystemExit("  SKIP — VAPI_COMPLAINT_NUMBER_ID not set")
    body = {"assistantId": None, "server": {"url": f"{BACKEND_URL}/voice/inbound-router"}}
    if dry_run:
        print(f"  DRY RUN — PATCH /phone-number/{number_id}  -> server-url routing ({body['server']['url']})")
        return
    resp = httpx.patch(f"{VAPI_API_BASE}/phone-number/{number_id}", headers=_headers(), json=body, timeout=30)
    if resp.status_code != 200:
        raise SystemExit(f"  [FAIL] repoint number HTTP {resp.status_code}: {resp.text[:300]}")
    got = resp.json()
    print(f"  [OK] number {got.get('number')} now routes via server url {got.get('server', {}).get('url')} (assistantId={got.get('assistantId')})")


def rollback(dry_run: bool) -> None:
    number_id = os.environ.get("VAPI_COMPLAINT_NUMBER_ID", "")
    entry_id = os.environ.get("VAPI_COMPLAINT_ASSISTANT_ID", "")
    if not (number_id and entry_id):
        raise SystemExit("  SKIP — VAPI_COMPLAINT_NUMBER_ID / VAPI_COMPLAINT_ASSISTANT_ID not set")
    body = {"assistantId": entry_id, "server": None}
    if dry_run:
        print(f"  DRY RUN — PATCH /phone-number/{number_id}  -> static entry binding {entry_id}")
        return
    resp = httpx.patch(f"{VAPI_API_BASE}/phone-number/{number_id}", headers=_headers(), json=body, timeout=30)
    if resp.status_code != 200:
        raise SystemExit(f"  [FAIL] rollback HTTP {resp.status_code}: {resp.text[:300]}")
    print(f"  [OK] number bound statically to entry assistant again (English assistant left in place)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--route-number", action="store_true",
                        help="Repoint the complaint number to /voice/inbound-router (backend must be deployed first)")
    parser.add_argument("--rollback", action="store_true",
                        help="Restore the static entry-assistant binding on the number")
    args = parser.parse_args()

    print("=" * 64)
    print("Complaint language routing" + ("  [DRY RUN]" if args.dry_run else "  [LIVE]"))
    print("=" * 64)

    if args.rollback:
        rollback(args.dry_run)
    else:
        provision_english_assistant(args.dry_run)
        if args.route_number:
            route_number(args.dry_run)
        else:
            print("  (number binding untouched — run with --route-number after the backend deploy)")

    print("\nDone." + ("  (dry run — nothing changed)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
