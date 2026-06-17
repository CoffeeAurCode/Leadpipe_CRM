# Plan — Voice Agent: City Recognition Across Landlord Listings

> Source: `leadpipe_dev_brief.md` — Task 1. Date: 2026-06-17.
> Owner: lease agent (Max) / `find_units` + `search_listings` + `vapi_agent_config.py`.

## Problem

When a caller names a city, Max fails to match it to available units even when the
landlord has buildings in that city. The brief requires:

1. Recognize city names spoken in **French and English**.
2. Cross-reference against **all cities in the landlord's active listings** — dynamic, not hardcoded.
3. Handle French/English variants and **phonetic near-matches** (`Mont-réal` vs `Montreal`, casual `Saint-Léonard`).
4. On match → confirm availability, continue qualification. On no match → inform + **offer other cities in the portfolio**.

## Root cause (it is NOT the conversational ask)

The agent already asks for the area conversationally and already passes the words to `find_units`:

- `vapi_agent_config.py:1055-1057` — Step 1 asks "Which area or building are you looking at?"
- `vapi_agent_config.py:1059-1060` — Step 2 silently calls `find_units` with the caller's words.
- `find_units` already scopes to `manager_id` + `is_active=True` and includes `city`/`state` in the haystack (`leasing.py:199-208`).

The failure is downstream, in matching and grounding:

- **Gap A — no diacritic/punctuation normalization.** `find_units` matches by lowercased substring only (`leasing.py:191`, `210-211`). `"montréal"` is not a substring of `"montreal"`; `"saint-léonard"` / `"st-léonard"` / `"saint leonard"` all miss each other. This is exactly the brief's named case.
- **Gap B — no phonetic / fuzzy fallback.** Token substring catches nothing when Deepgram (`language: "multi"`) transcribes a French city loosely. The brief explicitly requires phonetic near-matches.
- **Gap C — no dynamic city list exists.** On no-match `find_units` returns an empty list, yet the prompt (`vapi_agent_config.py:1067-1068`) tells Max to "list the areas/buildings you actually have." He has no data → silence or hallucination. No endpoint returns the distinct cities of a manager's active listings, so "offer other cities" cannot be met truthfully today.

## Design

Keep the intelligence in the backend; the prompt only reads tool results. Three layers:

1. **Normalize** both query and stored city before comparing.
2. **Fuzzy-match** the caller's location token against the manager's distinct active-listing cities (+ a small FR/EN alias map).
3. **Return `available_cities`** from `find_units` always, so Max can confirm a match and offer real alternatives on no-match.

---

## Implementation

### 1. Shared normalization + city helpers — new module `backend/app/services/city_matching.py`

```python
import unicodedata, difflib

_CITY_ALIASES = {
    # normalized spoken form -> canonical normalized city
    "mtl": "montreal",
    "saint leonard": "saint leonard",   # plus St-/Ste- expansion handled by _normalize
    # extend with common Quebec FR/EN pairs as they surface in real calls
}

def normalize_place(s: str) -> str:
    """Lowercase, strip diacritics, expand St/Ste -> Saint/Sainte,
    collapse hyphens/punctuation to single spaces."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = s.replace("-", " ")
    # token-level St./Ste. -> Saint/Sainte
    out = []
    for tok in s.split():
        tok = tok.strip(".,'")
        if tok in ("st", "st."):   out.append("saint");  continue
        if tok in ("ste", "ste."): out.append("sainte"); continue
        if tok:                    out.append(tok)
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
```

Notes:
- `difflib` is stdlib — no new dependency. Threshold tuned by manual test (start 0.82).
- The alias map is a **small assist**, not the source of truth. The dynamic city list (below) remains the authority — brief requires "not hardcoded."

### 2. `find_units` (`leasing.py:151-235`)

- After fetching `listings`, build the **distinct city set** for this manager from the already-fetched rows: `{ r["city"] for r in listings if r.get("city") }` (display form) and a normalized lookup.
- Replace the bare-substring location check: when a caller token doesn't substring-hit the haystack, fall back to `city_matches(normalize_place(token), city_norm)` against each listing's normalized city. Keep the existing flat_number/title/building/property substring behavior for non-city tokens.
- Add `available_cities` (sorted, display-cased, deduped) to **every** return — both found and not-found:
  ```python
  return {"found": bool(matches), "count": len(matches),
          "units": matches, "available_cities": available_cities}
  ```
- No-match early returns (`leasing.py:173`, exception handler `234`) must also include `available_cities` (empty list is fine in the exception path).

### 3. `search_listings` city filter (`leasing.py:429-430`)

The `ilike("city", "%...%")` filter has the same accent blind spot. Two options:

- **Minimal:** when `city_filter` is set, fetch without the DB `ilike`, then Python-filter rows with `city_matches(normalize_place(city_filter), normalize_place(row.city))`. Consistent with how bedrooms/parking are already post-filtered (`leasing.py:439-446`).
- Apply the same in `find_listing` Path 3 (`leasing.py:127-138`) if we want parity, but that endpoint is secondary — defer unless needed.

### 4. Tool schema — surface `available_cities` to the agent (`vapi_agent_config.py:1315-1345`)

Add to `find_units`' `variableExtractionPlan.schema.properties`:

```python
"available_cities": {"type": "array", "items": {"type": "string"}},
```

### 5. Prompt — Step 2 grounding (`vapi_agent_config.py:1059-1071`)

Rewrite the no-match branch to read from the tool result instead of memory:

- On match → unchanged (acknowledge, continue to size).
- On no-match → "I'm not finding anything in **[caller's city]** — right now we have places in **[available_cities]**. Any of those work?" using the `available_cities` array returned by `find_units`. Never invent a city not in that list.
- Keep the retry loop (re-call `find_units` with the new city), then No-Match path.

### 6. Deploy the agent change

Prompt/tool-schema edits do not take effect until pushed to the live per-manager assistants:

```
python backend/scripts/update_lease_agents.py
```

(Also `update_shared_agents.py` for the shared lease agent if still in use.)

---

## Out of scope / explicitly not doing

- No hardcoded city list as the matching authority (brief forbids it). Alias map is a phonetic assist only.
- No DB schema change — cities already live on `lease_listings.city`.
- No new dependency — `difflib` + `unicodedata` are stdlib.

## Test plan

Unit (`tests/`): `normalize_place` and `city_matches` for —
- `Montréal` / `Mont-réal` / `mont real` / `montreal` all collapse equal.
- `Saint-Léonard` / `St-Léonard` / `Saint Leonard` / `st leonard` all match.
- `Longueuil` vs a near-miss transcription (`longuil`, `long voy`) — fuzzy threshold catches the close one, rejects the far one.
- Non-city tokens (flat number, building name) still match via substring path.

Manual (live call, `docs/testing/`): caller says a French city in an English call and vice-versa; verify match continues to size, and no-match offers the real portfolio cities.

## Files touched

| File | Change |
|---|---|
| `backend/app/services/city_matching.py` | **New** — `normalize_place`, `city_matches`, alias map |
| `backend/app/routes/leasing.py` | `find_units` fuzzy city match + `available_cities`; `search_listings` city post-filter |
| `backend/app/services/vapi_agent_config.py` | `find_units` tool schema + Step 2 no-match prompt |
| `backend/scripts/update_lease_agents.py` | (run, not edit) push config to live assistants |

## CODEBASE_CONTEXT.md updates on completion

- `/leasing/find-units` row: note accent-insensitive + fuzzy city matching and the new `available_cities` field in the response.
- `/leasing/search-listings` row: note the city filter is now accent-insensitive (Python post-filter).
- Lease agent behaviour section: note Step 2 offers portfolio cities from `available_cities` on no-match.
