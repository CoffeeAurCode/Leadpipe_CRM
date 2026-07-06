import re

E164_RE = re.compile(r'^\+[1-9]\d{9,14}$')


def normalize_phone_e164(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip()
    if s.startswith('00'):
        s = '+' + s[2:]
    digits = re.sub(r'\D', '', s)
    if not digits:
        return None
    if s.startswith('+'):
        candidate = '+' + digits
    elif len(digits) == 10:
        # bare 10-digit numbers are assumed NANP (Canada/US) — primary market
        candidate = '+1' + digits
    else:
        candidate = '+' + digits
    return candidate if E164_RE.match(candidate) else None
