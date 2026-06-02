"""
One-time cleanup script:
  1. Enable voice_calls for ALL existing units (upsert overwrites any explicit False).
  2. Delete flats whose flat_number contains spaces or special characters.

Run from the backend/ directory:
    python -m scripts.fix_voice_and_flat_names

Requires .env with SUPABASE_URL and SUPABASE_SERVICE_KEY.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.config import settings

ALPHANUMERIC = re.compile(r'^[A-Z0-9]+$')


def main():
    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    # ── 1. Enable voice_calls for all units ──────────────────────────────────
    print("=== Step 1: Enable voice_calls for all units ===")

    all_flats = db.table("flats").select("id, flat_number").execute()
    flat_rows = all_flats.data or []
    print(f"  Total units found: {len(flat_rows)}")

    rows_to_upsert = [
        {"unit_id": f["id"], "feature_key": "voice_calls", "enabled": True}
        for f in flat_rows
    ]

    if rows_to_upsert:
        db.table("property_features") \
            .upsert(rows_to_upsert, on_conflict="unit_id,feature_key") \
            .execute()
        print(f"  [OK] voice_calls enabled for {len(rows_to_upsert)} units")
    else:
        print("  [SKIP] No units found")

    # ── 2. Delete flats with invalid flat_number ─────────────────────────────
    print("\n=== Step 2: Remove flats with invalid flat_number ===")

    bad_flats = [
        f for f in flat_rows
        if not ALPHANUMERIC.match(f["flat_number"].strip().upper())
    ]

    if not bad_flats:
        print("  [OK] No flats with invalid names found")
        return

    print(f"  Found {len(bad_flats)} flat(s) to delete:")
    for f in bad_flats:
        print(f"    id={f['id']}  flat_number={f['flat_number']!r}")

    for f in bad_flats:
        fid = f["id"]
        fname = f["flat_number"]

        # Delete dependent records first to avoid FK violations
        db.table("property_features").delete().eq("unit_id", fid).execute()

        flat_resp = db.table("flats").select("uuid").eq("id", fid).execute()
        if flat_resp.data:
            fuuid = flat_resp.data[0]["uuid"]
            # Delete leaf-to-root: leads → listings → appointments/complaints → flat
            listings = db.table("lease_listings").select("uuid").eq("flat_uuid", fuuid).execute()
            for listing in (listings.data or []):
                db.table("lease_leads").delete().eq("listing_uuid", listing["uuid"]).execute()
            db.table("lease_listings").delete().eq("flat_uuid", fuuid).execute()
            db.table("appointments").delete().eq("flat_uuid", fuuid).execute()
            db.table("complaints").delete().eq("flat_uuid", fuuid).execute()

        db.table("flats").delete().eq("id", fid).execute()
        print(f"  [DELETED] flat_number={fname!r} (id={fid})")

    print(f"\n  Done. {len(bad_flats)} flat(s) removed.")


if __name__ == "__main__":
    main()
