"""
Provision the dedicated French complaint assistant and wire the gated handoff onto the ENTRY
complaint assistant.

Mirror of provision_lease_french_handoff.py, adapted for the complaint agent — which is a single
GLOBAL assistant (VAPI_COMPLAINT_ASSISTANT_ID → +14382314283), not per-manager. So:
  - There is exactly ONE entry + ONE French assistant. No fleet, no Supabase, no DB migration.
  - The French assistant id lives in an env var (VAPI_COMPLAINT_FRENCH_ASSISTANT_ID), the way
    the shared lease French id lives in VAPI_SHARED_LEASE_FRENCH_ASSISTANT_ID.

Design (same as the lease handoff):
  - NO squad, NO phone-number change. The inbound number stays on the entry assistant.
  - French callers are handed off to a dedicated nova-3 "fr" assistant by assistantId, with
    contextEngineeringPlan:"all" so the French assistant continues, not restarts.
  - The entry assistant's only live change is one additive, French-gated handoff tool + the
    [French Routing] gate + a bilingual opener; English behavior is unchanged.

Like the rest of the project, this uses direct HTTP (not the Vapi SDK), which silently drops
camelCase fields such as firstMessageMode.

Run from the project root (base python is fine — no Supabase needed):
    python backend/scripts/provision_complaint_french_handoff.py --dry-run   # preview
    python backend/scripts/provision_complaint_french_handoff.py             # execute
    python backend/scripts/provision_complaint_french_handoff.py --rollback --dry-run
    python backend/scripts/provision_complaint_french_handoff.py --rollback

Requires .env: PRIVATE_VAPI_API, VAPI_COMPLAINT_ASSISTANT_ID.
Optional: VAPI_COMPLAINT_FRENCH_ASSISTANT_ID (set after first run to update in place).
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
from app.services.vapi_agent_config import (
    build_complaint_config,
    build_complaint_config_french,
)

BACKEND_URL = "https://tenant-management-mvp.onrender.com"
VAPI_API_BASE = "https://api.vapi.ai"


def _to_vapi_payload(cfg: dict) -> dict:
    """snake_case config dict -> camelCase VAPI REST payload (mirrors update_shared_agents.py)."""
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


def _create_french_assistant(cfg: dict, dry_run: bool) -> str:
    payload = _to_vapi_payload(cfg)
    tx = payload["transcriber"]
    if dry_run:
        print(f"    DRY RUN — POST /assistant  name={payload['name']}  transcriber={tx['model']}/{tx['language']}")
        return "<dry-run-french-id>"
    resp = httpx.post(f"{VAPI_API_BASE}/assistant", headers=_headers(), json=payload, timeout=30)
    if resp.status_code not in (200, 201):
        raise SystemExit(f"    [FAIL] create French assistant HTTP {resp.status_code}: {resp.text[:300]}")
    new_id = resp.json()["id"]
    print(f"    [OK] created French assistant  id={new_id}  transcriber={tx['model']}/{tx['language']}")
    return new_id


def _patch_assistant(assistant_id: str, cfg: dict, dry_run: bool, label: str) -> None:
    payload = _to_vapi_payload(cfg)
    handoff = [t for t in cfg["model"]["tools"] if t.get("type") == "handoff"]
    target = handoff[0]["destinations"][0]["assistantId"] if handoff else None
    if dry_run:
        print(f"    DRY RUN — PATCH /assistant/{assistant_id} ({label})  handoff->{target}")
        return
    resp = httpx.patch(f"{VAPI_API_BASE}/assistant/{assistant_id}", headers=_headers(), json=payload, timeout=30)
    if resp.status_code != 200:
        raise SystemExit(f"    [FAIL] patch {label} HTTP {resp.status_code}: {resp.text[:300]}")
    got = [t for t in resp.json().get("model", {}).get("tools", []) if t.get("type") == "handoff"]
    print(f"    [OK] patched {label}  id={assistant_id}  handoff_present={bool(got)}")


def _delete_assistant(assistant_id: str, dry_run: bool, label: str) -> None:
    if dry_run:
        print(f"    DRY RUN — DELETE /assistant/{assistant_id} ({label})")
        return
    resp = httpx.delete(f"{VAPI_API_BASE}/assistant/{assistant_id}", headers=_headers(), timeout=30)
    if resp.status_code not in (200, 204):
        print(f"    [WARN] delete {label} HTTP {resp.status_code}: {resp.text[:200]}")
    else:
        print(f"    [OK] deleted {label}  id={assistant_id}")


def provision(dry_run: bool) -> None:
    entry_id = os.environ.get("VAPI_COMPLAINT_ASSISTANT_ID", "")
    if not entry_id:
        raise SystemExit("  SKIP — VAPI_COMPLAINT_ASSISTANT_ID not set")

    existing_fr = os.environ.get("VAPI_COMPLAINT_FRENCH_ASSISTANT_ID", "")
    print(f"\n  entry={entry_id}  existing_french={existing_fr or '(none)'}")

    fr_cfg = build_complaint_config_french(BACKEND_URL)
    if existing_fr:
        _patch_assistant(existing_fr, fr_cfg, dry_run, "French complaint assistant")
        fr_id = existing_fr
    else:
        fr_id = _create_french_assistant(fr_cfg, dry_run)
        if not dry_run:
            print(f"\n    >>> ADD TO .env / Render env:  VAPI_COMPLAINT_FRENCH_ASSISTANT_ID={fr_id}")
            print("    (so update_shared_agents.py keeps the handoff on future redeploys)\n")

    entry_cfg = build_complaint_config(BACKEND_URL, french_assistant_id=fr_id)
    _patch_assistant(entry_id, entry_cfg, dry_run, "entry complaint assistant")


def rollback(dry_run: bool) -> None:
    entry_id = os.environ.get("VAPI_COMPLAINT_ASSISTANT_ID", "")
    fr_id = os.environ.get("VAPI_COMPLAINT_FRENCH_ASSISTANT_ID", "")
    if not entry_id:
        raise SystemExit("  SKIP — VAPI_COMPLAINT_ASSISTANT_ID not set")
    print(f"\n  ROLLBACK  entry={entry_id}  french={fr_id or '(none)'}")
    entry_cfg = build_complaint_config(BACKEND_URL, french_assistant_id=None)
    _patch_assistant(entry_id, entry_cfg, dry_run, "entry complaint (remove handoff)")
    if fr_id:
        _delete_assistant(fr_id, dry_run, "French complaint assistant")
        if not dry_run:
            print("    >>> REMOVE env var VAPI_COMPLAINT_FRENCH_ASSISTANT_ID")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without calling the API")
    parser.add_argument("--rollback", action="store_true",
                        help="Undo: remove the handoff from the entry assistant and delete the French assistant")
    args = parser.parse_args()

    mode = "ROLLBACK" if args.rollback else "PROVISION"
    print("=" * 64)
    print(f"Complaint French handoff {mode}" + ("  [DRY RUN]" if args.dry_run else "  [LIVE]"))
    print("=" * 64)

    if args.rollback:
        rollback(args.dry_run)
    else:
        provision(args.dry_run)

    print("\nDone." + ("  (dry run — nothing changed)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
