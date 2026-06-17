import difflib
import unicodedata

_CITY_ALIASES = {
    "mtl": "montreal",
    "quebec city": "quebec",
    "ville de quebec": "quebec",
    "three rivers": "trois rivieres",
}


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
