import difflib
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Optional

try:
    from rapidfuzz.fuzz import ratio as _rapidfuzz_ratio
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False

try:
    import jellyfish
    _HAS_JELLYFISH = True
except ImportError:
    _HAS_JELLYFISH = False

_CITY_ALIASES = {
    "mtl": "montreal",
    "quebec city": "quebec",
    "ville de quebec": "quebec",
    "three rivers": "trois rivieres",
}

# Banded-confirmation thresholds (Phase 1 — city). Tune against the garble corpus.
T_HIGH = 0.86      # clear-winner floor
MARGIN = 0.08      # min gap #1 over #2 to auto-accept
T_CONFIRM = 0.66   # lowest top score still worth confirming
BAND = 0.06        # who joins the confirm question (within this of the top)
T_FLOOR = 0.55     # below this → no match, fall through to available_cities
N_MAX = 3          # max candidates voiced in a confirm question


def normalize_place(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("-", " ")
    out = []
    for tok in s.split():
        tok = tok.strip(".,'")
        if tok in ("st", "st."):
            out.append("saint")
        elif tok in ("ste", "ste."):
            out.append("sainte")
        elif tok:
            out.append(tok)
    return " ".join(out)


def city_matches(query_norm: str, city_norm: str, threshold: float = 0.82) -> bool:
    if not query_norm or not city_norm:
        return False
    if query_norm in city_norm or city_norm in query_norm:
        return True
    canon = _CITY_ALIASES.get(query_norm)
    if canon and (canon == city_norm or canon in city_norm):
        return True
    return difflib.SequenceMatcher(None, query_norm, city_norm).ratio() >= threshold


# ===========================================================================
# Phonetic + hybrid similarity (C1) — swappable phonetic backend
# ===========================================================================

# Default phonetic encoder: single Metaphone (jellyfish). Sound-based, which is the
# right axis against Deepgram's pseudo-English rendering of French-accented audio.
# Swap to a Beider-Morse / French-Soundex encoder via set_phonetic_encoder if the
# corpus bake-off shows it false-accepting at scale.
_PHONETIC_ENCODER: Optional[Callable[[str], str]] = jellyfish.metaphone if _HAS_JELLYFISH else None


def set_phonetic_encoder(fn: Optional[Callable[[str], str]]) -> None:
    global _PHONETIC_ENCODER
    _PHONETIC_ENCODER = fn


def _phonetic_code(norm: str) -> str:
    if not _PHONETIC_ENCODER or not norm:
        return ""
    try:
        return " ".join(_PHONETIC_ENCODER(tok) for tok in norm.split() if tok)
    except Exception:
        return ""


def _phonetic_ratio(a_norm: str, b_norm: str) -> float:
    ca, cb = _phonetic_code(a_norm), _phonetic_code(b_norm)
    if not ca or not cb:
        return 0.0
    if ca == cb:
        return 1.0
    return difflib.SequenceMatcher(None, ca, cb).ratio()


def _rapidfuzz_score(a_norm: str, b_norm: str) -> float:
    if not _HAS_RAPIDFUZZ:
        return 0.0
    return _rapidfuzz_ratio(a_norm, b_norm) / 100.0


def similarity(spoken: str, candidate: str) -> float:
    """Hybrid sound+string score in [0, 1]. Inputs are normalized internally.

    max(rapidfuzz, phonetic (Metaphone), difflib) — the phonetic leg rescues
    sound-alike/spelled-different garble ("Saint-L'Asor"→"Saint-Lazare") that the
    pure character ratios miss; the string legs catch edit-distance garble.
    """
    a, b = normalize_place(spoken), normalize_place(candidate)
    if not a or not b:
        return 0.0
    return max(
        _rapidfuzz_score(a, b),
        _phonetic_ratio(a, b),
        difflib.SequenceMatcher(None, a, b).ratio(),
    )


# ===========================================================================
# Banded candidate ranking — the "did you mean X or Y?" decision
# ===========================================================================

@dataclass
class Candidate:
    value: str   # original display value (e.g. "Saint-Lazare")
    score: float


@dataclass
class RankResult:
    decision: str                       # AUTO_ACCEPT | CONFIRM | NO_MATCH
    field_name: str
    spoken: str
    top: Optional[Candidate]
    candidates: list                    # the band to voice (CONFIRM); [top] for AUTO_ACCEPT; [] for NO_MATCH
    scored: list = field(default_factory=list)   # all candidates, sorted desc (debug/tuning)


def rank_candidates(
    spoken: str,
    candidate_values,
    field_name: str = "city",
    t_high: float = T_HIGH,
    margin: float = MARGIN,
    t_confirm: float = T_CONFIRM,
    band: float = BAND,
    t_floor: float = T_FLOOR,
    n_max: int = N_MAX,
) -> RankResult:
    """Score `spoken` against a manager's real, distinct values for one field and
    decide between three outcomes:

      AUTO_ACCEPT — one clear winner (top >= t_high and beats #2 by >= margin).
      CONFIRM     — genuinely confusable: top is plausible (>= t_floor) but not a
                    clear winner; voice only the values within `band` of the top
                    (capped at n_max). Leans to confirming in the gray zone because
                    a false accept costs the whole call, a false confirm costs a turn.
      NO_MATCH    — nothing close (top < t_floor); caller falls through to the
                    existing available_cities offer.
    """
    spoken_norm = normalize_place(spoken)
    best: dict = {}
    for v in candidate_values:
        vn = normalize_place(v)
        if not vn:
            continue
        s = similarity(spoken, v)
        if vn not in best or s > best[vn].score:
            best[vn] = Candidate(value=v, score=s)
    scored = sorted(best.values(), key=lambda c: c.score, reverse=True)

    if not spoken_norm or not scored:
        return RankResult("NO_MATCH", field_name, spoken, None, [], scored)

    top = scored[0]
    second = scored[1] if len(scored) > 1 else None
    gap = top.score - (second.score if second else 0.0)

    if top.score < t_floor:
        return RankResult("NO_MATCH", field_name, spoken, None, [], scored)

    if top.score >= t_high and (second is None or gap >= margin):
        return RankResult("AUTO_ACCEPT", field_name, spoken, top, [top], scored)

    band_members = [c for c in scored if (top.score - c.score) <= band][:n_max]
    return RankResult("CONFIRM", field_name, spoken, top, band_members, scored)
