"""
Phase-0 tooling for the banded entity-confirmation feature.

Manufactures labeled `garble -> truth` pairs at volume by round-tripping each
manager's REAL city/building values through a French-accent TTS and back through
Deepgram (the same nova-3 'multi' transcriber the live agent uses). The resulting
pairs feed (a) the phonetic-encoder bake-off and (b) threshold fitting for
rank_candidates in app/services/city_matching.py.

Run from the project root:
    python backend/scripts/generate_stt_garble_corpus.py [--manager-id UUID] [--rounds 3]

Modes:
  • Round-trip mode (preferred): set ELEVENLABS_API_KEY and DEEPGRAM_API_KEY. The
    script speaks each city in a French voice and transcribes it back, producing
    realistic garble. Use --rounds to vary voice stability for diverse garbles.
  • Offline-seed mode (no keys): emits only the hand-labeled SEED_CORPUS below
    (garbles harvested from real call transcripts) so the corpus file always exists.

Output: docs/testing/lease_agent_stt_garble_corpus.json — a list of
  {truth, spoken, source, decision, top, band} rows. `decision`/`top`/`band` are
  what the CURRENT thresholds produce (for tuning, not ground truth).
"""
import argparse
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from supabase import create_client

from app.config import settings
from app.services.city_matching import rank_candidates
from app.services.vapi_agent_config import VOICE_CONFIG, TRANSCRIBER_CONFIG

OUT_PATH = ROOT.parent / "docs" / "testing" / "lease_agent_stt_garble_corpus.json"

# Garbles harvested from real call transcripts (see the 2026-06 diagnoses). Truth is
# the canonical listing value; these are the cases banded confirmation must rescue
# (mild, phonetically-near garble) or correctly drop (severe garble -> NO_MATCH).
SEED_CORPUS = [
    {"truth": "Saint-Lazare", "spoken": "Saint-L'Asor", "source": "transcript"},
    {"truth": "Saint-Lazare", "spoken": "Saint-Lavaure", "source": "transcript"},
    {"truth": "Saint-Lazare", "spoken": "Saint Lazole", "source": "transcript"},
    {"truth": "Saint-Lazare", "spoken": "Saint-Lazar", "source": "transcript"},
    {"truth": "Saint-Lazare", "spoken": "thing on low", "source": "transcript"},  # severe -> NO_MATCH
    {"truth": "Montréal", "spoken": "Montreal", "source": "transcript"},
    {"truth": "Châteauguay", "spoken": "Shata gway", "source": "transcript"},
]

ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


def _distinct_values(db, manager_id: str | None) -> tuple[list, list]:
    q = db.table("lease_listings").select("city, manager_id, flats!inner(building_id)").eq("is_active", True)
    if manager_id:
        q = q.eq("manager_id", manager_id)
    rows = (q.limit(500).execute().data) or []
    cities = sorted({(r.get("city") or "").strip() for r in rows if (r.get("city") or "").strip()})

    bq = db.table("buildings").select("name, manager_id")
    if manager_id:
        bq = bq.eq("manager_id", manager_id)
    brows = (bq.limit(500).execute().data) or []
    buildings = sorted({(b.get("name") or "").strip() for b in brows if (b.get("name") or "").strip()})
    return cities, buildings


def _tts(text: str, stability: float, key: str) -> bytes | None:
    try:
        resp = httpx.post(
            ELEVEN_URL.format(voice_id=VOICE_CONFIG["voiceId"]),
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": VOICE_CONFIG.get("model", "eleven_turbo_v2_5"),
                "voice_settings": {"stability": stability, "similarity_boost": 0.75},
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"    [tts FAIL] HTTP {resp.status_code}: {resp.text[:120]}")
            return None
        return resp.content
    except Exception as e:
        print(f"    [tts FAIL] {e}")
        return None


def _stt(audio: bytes, key: str) -> str:
    try:
        resp = httpx.post(
            DEEPGRAM_URL,
            params={
                "model": TRANSCRIBER_CONFIG.get("model", "nova-3"),
                "language": TRANSCRIBER_CONFIG.get("language", "multi"),
                "numerals": "true",
            },
            headers={"Authorization": f"Token {key}", "Content-Type": "audio/mpeg"},
            content=audio,
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"    [stt FAIL] HTTP {resp.status_code}: {resp.text[:120]}")
            return ""
        data = resp.json()
        return (
            data.get("results", {}).get("channels", [{}])[0]
            .get("alternatives", [{}])[0].get("transcript", "")
        ).strip()
    except Exception as e:
        print(f"    [stt FAIL] {e}")
        return ""


def _label(spoken: str, truth: str, all_cities: list) -> dict:
    rank = rank_candidates(spoken, all_cities, field_name="city")
    return {
        "decision": rank.decision,
        "top": rank.top.value if rank.top else None,
        "band": [c.value for c in rank.candidates],
        "truth_in_band": truth in [c.value for c in rank.candidates],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manager-id", default=None)
    parser.add_argument("--rounds", type=int, default=3, help="TTS variations per value")
    args = parser.parse_args()

    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    cities, buildings = _distinct_values(db, args.manager_id)
    print(f"Distinct cities: {len(cities)} | buildings: {len(buildings)}")

    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "")
    dg_key = os.environ.get("DEEPGRAM_API_KEY", "")
    roundtrip = bool(eleven_key and dg_key)
    print("Mode:", "round-trip (TTS->Deepgram)" if roundtrip else "offline-seed (set ELEVENLABS_API_KEY + DEEPGRAM_API_KEY for round-trip)")

    corpus = []
    # Hand-labeled seeds first, scored against this portfolio's real cities.
    label_pool = cities or sorted({r["truth"] for r in SEED_CORPUS})
    for row in SEED_CORPUS:
        corpus.append({**row, **_label(row["spoken"], row["truth"], label_pool)})

    if roundtrip:
        stabilities = [0.2, 0.5, 0.8][: max(1, args.rounds)]
        for truth in cities:
            print(f"  {truth!r}")
            for stab in stabilities:
                audio = _tts(truth, stab, eleven_key)
                if not audio:
                    continue
                spoken = _stt(audio, dg_key)
                if not spoken:
                    continue
                corpus.append({
                    "truth": truth,
                    "spoken": spoken,
                    "source": f"roundtrip_stability_{stab}",
                    **_label(spoken, truth, cities),
                })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {len(corpus)} labeled pairs -> {OUT_PATH}")
    by_decision = {}
    for row in corpus:
        by_decision[row["decision"]] = by_decision.get(row["decision"], 0) + 1
    print("Current-threshold decisions:", by_decision)


if __name__ == "__main__":
    main()
