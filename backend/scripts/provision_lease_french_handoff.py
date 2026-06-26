"""
Provision the dedicated French lease assistant and wire the gated handoff onto the ENTRY assistant.

Design (see docs/development_plans/PLAN_lease_agent_french_squad_routing_2026-06-26.md):
  - NO squad, NO phone-number change. The inbound number stays on the entry assistant.
  - French callers are handed off to a dedicated nova-3 "fr" assistant by assistantId,
    with contextEngineeringPlan:"all" so the French assistant continues, not restarts.
  - The entry assistant's only live change is one additive, French-gated handoff tool;
    English behavior is unchanged.

Like the rest of the project, this uses direct HTTP (not the Vapi SDK), which silently
drops camelCase fields such as firstMessageMode.

Run from the project root. The --all / --rollback paths hit Supabase, so use the backend venv
(base python lacks `supabase`):  backend/.venv/Scripts/python.exe
    python backend/scripts/provision_lease_french_handoff.py --dry-run                    # preview SHARED pilot
    python backend/scripts/provision_lease_french_handoff.py                              # execute SHARED pilot
    ...python provision_lease_french_handoff.py --all --fleet-only --confirm-fleet --dry-run   # preview per-manager
    ...python provision_lease_french_handoff.py --all --fleet-only --confirm-fleet             # per-manager live
    ...python provision_lease_french_handoff.py --rollback --all --fleet-only --dry-run        # preview rollback
    ...python provision_lease_french_handoff.py --rollback --all --fleet-only                  # roll back per-manager

Pilot (shared agent) is the default and the safe first step. Fleet rollout (--all) is gated
behind --confirm-fleet and requires the manager_vapi_config.vapi_lease_french_assistant_id
column (backend/migrations/031_lease_french_assistant_id.sql) AND a validated pilot.

Requires .env: PRIVATE_VAPI_API, VAPI_SHARED_LEASE_ASSISTANT_ID.
Optional: VAPI_SHARED_LEASE_FRENCH_ASSISTANT_ID (set after first run to update in place).
For --all: SUPABASE_URL, SUPABASE_SERVICE_KEY.
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
    build_lease_config_shared,
    build_lease_config_french_shared,
    build_lease_config,
    build_lease_config_french,
)

BACKEND_URL = "https://tenant-management-mvp.onrender.com"
VAPI_API_BASE = "https://api.vapi.ai"


def _to_vapi_payload(cfg: dict) -> dict:
    """snake_case config dict -> camelCase VAPI REST payload (mirrors update_lease_agents.py)."""
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


def provision_shared(dry_run: bool) -> None:
    entry_id = os.environ.get("VAPI_SHARED_LEASE_ASSISTANT_ID", "")
    if not entry_id:
        print("  [shared] SKIP — VAPI_SHARED_LEASE_ASSISTANT_ID not set")
        return

    existing_fr = os.environ.get("VAPI_SHARED_LEASE_FRENCH_ASSISTANT_ID", "")
    print(f"\n  [shared]  entry={entry_id}  existing_french={existing_fr or '(none)'}")

    fr_cfg = build_lease_config_french_shared(BACKEND_URL)
    if existing_fr:
        _patch_assistant(existing_fr, fr_cfg, dry_run, "shared French assistant")
        fr_id = existing_fr
    else:
        fr_id = _create_french_assistant(fr_cfg, dry_run)
        if not dry_run:
            print(f"\n    >>> ADD TO .env / Render env:  VAPI_SHARED_LEASE_FRENCH_ASSISTANT_ID={fr_id}")
            print("    (so update_lease_agents.py keeps the handoff on future redeploys)\n")

    entry_cfg = build_lease_config_shared(BACKEND_URL, french_assistant_id=fr_id)
    _patch_assistant(entry_id, entry_cfg, dry_run, "shared entry assistant")


def provision_fleet(dry_run: bool) -> None:
    from supabase import create_client
    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    # Requires the new column; if it is missing this select 400s with a clear message.
    rows = (
        db.table("manager_vapi_config")
        .select("manager_id, vapi_lease_assistant_id, vapi_lease_french_assistant_id")
        .eq("vapi_provisioning_status", "active")
        .execute()
    )
    for row in (rows.data or []):
        manager_id = row["manager_id"]
        entry_id = row.get("vapi_lease_assistant_id")
        if not entry_id:
            print(f"\n  [{manager_id[:8]}] SKIP — no entry assistant id")
            continue
        profile = db.table("manager_profiles").select("name").eq("user_id", manager_id).maybe_single().execute()
        manager_name = (profile.data or {}).get("name") or "our property management team"

        existing_fr = row.get("vapi_lease_french_assistant_id")
        print(f"\n  [{manager_id[:8]}]  entry={entry_id}  existing_french={existing_fr or '(none)'}")

        fr_cfg = build_lease_config_french(BACKEND_URL, manager_id, manager_name=manager_name)
        if existing_fr:
            _patch_assistant(existing_fr, fr_cfg, dry_run, "French assistant")
            fr_id = existing_fr
        else:
            fr_id = _create_french_assistant(fr_cfg, dry_run)
            if not dry_run:
                db.table("manager_vapi_config").update(
                    {"vapi_lease_french_assistant_id": fr_id}
                ).eq("manager_id", manager_id).execute()
                print(f"    [OK] stored vapi_lease_french_assistant_id={fr_id}")

        entry_cfg = build_lease_config(BACKEND_URL, manager_id, manager_name=manager_name, french_assistant_id=fr_id)
        _patch_assistant(entry_id, entry_cfg, dry_run, "entry assistant")


def _delete_assistant(assistant_id: str, dry_run: bool, label: str) -> None:
    if dry_run:
        print(f"    DRY RUN — DELETE /assistant/{assistant_id} ({label})")
        return
    resp = httpx.delete(f"{VAPI_API_BASE}/assistant/{assistant_id}", headers=_headers(), timeout=30)
    if resp.status_code not in (200, 204):
        print(f"    [WARN] delete {label} HTTP {resp.status_code}: {resp.text[:200]}")
    else:
        print(f"    [OK] deleted {label}  id={assistant_id}")


def rollback_shared(dry_run: bool) -> None:
    entry_id = os.environ.get("VAPI_SHARED_LEASE_ASSISTANT_ID", "")
    fr_id = os.environ.get("VAPI_SHARED_LEASE_FRENCH_ASSISTANT_ID", "")
    if not entry_id:
        print("  [shared] SKIP — VAPI_SHARED_LEASE_ASSISTANT_ID not set")
        return
    print(f"\n  [shared]  ROLLBACK  entry={entry_id}  french={fr_id or '(none)'}")
    entry_cfg = build_lease_config_shared(BACKEND_URL, french_assistant_id=None)
    _patch_assistant(entry_id, entry_cfg, dry_run, "shared entry (remove handoff)")
    if fr_id:
        _delete_assistant(fr_id, dry_run, "shared French assistant")
        if not dry_run:
            print("    >>> REMOVE env var VAPI_SHARED_LEASE_FRENCH_ASSISTANT_ID")


def rollback_fleet(dry_run: bool) -> None:
    from supabase import create_client
    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    rows = (
        db.table("manager_vapi_config")
        .select("manager_id, vapi_lease_assistant_id, vapi_lease_french_assistant_id")
        .eq("vapi_provisioning_status", "active")
        .execute()
    )
    for row in (rows.data or []):
        manager_id = row["manager_id"]
        entry_id = row.get("vapi_lease_assistant_id")
        fr_id = row.get("vapi_lease_french_assistant_id")
        if not entry_id or not fr_id:
            print(f"\n  [{manager_id[:8]}] SKIP — no French handoff to remove")
            continue
        profile = db.table("manager_profiles").select("name").eq("user_id", manager_id).maybe_single().execute()
        manager_name = (profile.data or {}).get("name") or "our property management team"
        print(f"\n  [{manager_id[:8]}]  ROLLBACK  entry={entry_id}  french={fr_id}")
        entry_cfg = build_lease_config(BACKEND_URL, manager_id, manager_name=manager_name, french_assistant_id=None)
        _patch_assistant(entry_id, entry_cfg, dry_run, "entry (remove handoff)")
        _delete_assistant(fr_id, dry_run, "French assistant")
        if not dry_run:
            db.table("manager_vapi_config").update(
                {"vapi_lease_french_assistant_id": None}
            ).eq("manager_id", manager_id).execute()
            print("    [OK] cleared vapi_lease_french_assistant_id")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without calling the API")
    parser.add_argument("--all", action="store_true", help="Fleet rollout to all per-manager agents")
    parser.add_argument("--confirm-fleet", action="store_true",
                        help="Required with --all; acknowledges the pilot is validated and the DB column exists")
    parser.add_argument("--fleet-only", action="store_true",
                        help="With --all: skip the scopeless shared agent, provision per-manager agents only")
    parser.add_argument("--rollback", action="store_true",
                        help="Undo: remove the handoff from entry assistants and delete the French assistants")
    args = parser.parse_args()

    mode = "ROLLBACK" if args.rollback else "PROVISION"
    print("=" * 64)
    print(f"French handoff {mode}" + ("  [DRY RUN]" if args.dry_run else "  [LIVE]"))
    print("=" * 64)

    if args.rollback:
        if args.all:
            if not args.fleet_only:
                rollback_shared(args.dry_run)
            rollback_fleet(args.dry_run)
        else:
            rollback_shared(args.dry_run)
    elif args.all:
        if not args.confirm_fleet:
            raise SystemExit(
                "Refusing --all without --confirm-fleet.\n"
                "Validate the SHARED pilot with a real French + English test call first,\n"
                "and apply backend/migrations/031_lease_french_assistant_id.sql,\n"
                "then re-run with: --all --confirm-fleet"
            )
        if not args.fleet_only:
            provision_shared(args.dry_run)
        provision_fleet(args.dry_run)
    else:
        provision_shared(args.dry_run)

    print("\nDone." + ("  (dry run — nothing changed)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
