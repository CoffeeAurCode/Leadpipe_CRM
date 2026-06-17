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


def _check(query, city, expected):
    got = city_matches(normalize_place(query), normalize_place(city))
    ok = got == expected
    print(f"  [{'PASS' if ok else 'FAIL'}] {query!r} vs {city!r} -> {got} (want {expected})")
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

    print()
    if failures:
        print(f"{failures} FAILED")
        sys.exit(1)
    print("ALL PASSED")


if __name__ == "__main__":
    main()
