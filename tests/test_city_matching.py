"""
Unit tests for the lease agent's city matching (Task 1 — city recognition).

Pure logic, no backend required:
    python tests/test_city_matching.py
"""
import importlib.util
import os
import sys

_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend", "app", "services", "city_matching.py",
)
_spec = importlib.util.spec_from_file_location("city_matching", _MODULE_PATH)
city_matching = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(city_matching)
normalize_place = city_matching.normalize_place
city_matches = city_matching.city_matches
rank_candidates = city_matching.rank_candidates


def _check(query, city, expected):
    got = city_matches(normalize_place(query), normalize_place(city))
    ok = got == expected
    print(f"  [{'PASS' if ok else 'FAIL'}] {query!r} vs {city!r} -> {got} (want {expected})")
    return ok


# Two genuinely near-homophone cities + clearly-distinct ones. The whole point of
# banding is that Saint-Lazare/Saint-Lazaire confirm together while Châteauguay etc.
# never get dragged into the question.
PORTFOLIO = ["Saint-Lazare", "Saint-Lazaire", "Châteauguay", "Montréal", "Longueuil", "Laval"]
PORTFOLIO_SINGLE = ["Saint-Lazare", "Châteauguay", "Laval"]


def _check_rank(spoken, cities, want_decision, want_band=None, forbid_in_band=None):
    r = rank_candidates(spoken, cities, field_name="city")
    band = {c.value for c in r.candidates}
    ok = r.decision == want_decision
    if want_band is not None:
        ok = ok and band == set(want_band)
    if forbid_in_band is not None:
        ok = ok and not (band & set(forbid_in_band))
    detail = f"-> {r.decision} top={r.top.value if r.top else None} band={sorted(band)}"
    print(f"  [{'PASS' if ok else 'FAIL'}] {spoken!r} {detail} (want {want_decision}"
          + (f", band={want_band}" if want_band is not None else "") + ")")
    return ok


def main():
    failures = 0

    print("normalize_place collapses accents / hyphens / St:")
    norm_cases = [
        ("Montréal", "montreal"),
        ("Mont-réal", "mont real"),
        ("Saint-Léonard", "saint leonard"),
        ("St-Léonard", "saint leonard"),
        ("Ste-Foy", "sainte foy"),
        ("Trois-Rivières", "trois rivieres"),
    ]
    for raw, expected in norm_cases:
        got = normalize_place(raw)
        ok = got == expected
        failures += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {raw!r} -> {got!r} (want {expected!r})")

    print("\ncity_matches — should MATCH (variants / phonetic near-miss):")
    for q, c in [
        ("Montreal", "Montréal"),
        ("Mont-réal", "Montreal"),
        ("mont real", "Montreal"),
        ("Saint-Léonard", "St-Leonard"),
        ("saint leonard", "Saint-Léonard"),
        ("longuil", "Longueuil"),
        ("Three Rivers", "Trois-Rivières"),
        ("mtl", "Montreal"),
        ("Quebec City", "Québec"),
    ]:
        failures += not _check(q, c, True)

    print("\ncity_matches — should NOT match (different cities):")
    for q, c in [
        ("Laval", "Montreal"),
        ("Longueuil", "Laval"),
        ("Brossard", "Montreal"),
        ("please", "Laval"),
    ]:
        failures += not _check(q, c, False)

    print("\nrank_candidates — AUTO_ACCEPT (clear winner, no extra turn):")
    failures += not _check_rank("Montreal", PORTFOLIO, "AUTO_ACCEPT")
    failures += not _check_rank("Chateauguay", PORTFOLIO, "AUTO_ACCEPT")
    failures += not _check_rank("Laval", PORTFOLIO, "AUTO_ACCEPT", forbid_in_band=["Longueuil", "Montréal"])
    # Single near-homophone in portfolio → implicit accept, not a confirm turn.
    failures += not _check_rank("Saint-Lazar", PORTFOLIO_SINGLE, "AUTO_ACCEPT", want_band=["Saint-Lazare"])

    print("\nrank_candidates — CONFIRM (only the confusable band, never the distinct ones):")
    failures += not _check_rank(
        "Saint-Lazar", PORTFOLIO, "CONFIRM",
        want_band=["Saint-Lazare", "Saint-Lazaire"],
    )
    failures += not _check_rank(
        "Saint-Lavaure", PORTFOLIO, "CONFIRM",
        forbid_in_band=["Châteauguay", "Montréal", "Longueuil", "Laval"],
    )

    print("\nrank_candidates — NO_MATCH (severe garble falls through to available_cities):")
    failures += not _check_rank("thing on low", PORTFOLIO, "NO_MATCH")
    failures += not _check_rank("Vancouver", PORTFOLIO, "NO_MATCH")

    print("\nrank_candidates — distinct-city non-collision regression:")
    # Châteauguay must never co-occur with Saint-Lazare in a band, and vice versa.
    r = rank_candidates("Saint-Lazar", PORTFOLIO, field_name="city")
    band = {c.value for c in r.candidates}
    ok = "Châteauguay" not in band
    failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] Châteauguay not banded with Saint-Lazar (band={sorted(band)})")

    print()
    if failures:
        print(f"{failures} FAILED")
        sys.exit(1)
    print("ALL PASSED")


if __name__ == "__main__":
    main()
