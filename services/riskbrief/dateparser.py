import re
from datetime import datetime, timedelta
from dateutil import parser as du_parser
from dateutil.tz import gettz

FR_MONTHS = {
    "janvier": "january", "février": "february", "fevrier": "february", "mars": "march",
    "avril": "april", "mai": "may", "juin": "june", "juillet": "july",
    "août": "august", "aout": "august", "septembre": "september", "octobre": "october",
    "novembre": "november", "décembre": "december", "decembre": "december"
}

FR_WEEKDAYS = {
    "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6
}
EN_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
}

def _normalize_text(text: str) -> str:
    t = (text or "").strip().lower()
    for fr, en in FR_MONTHS.items():
        t = re.sub(rf"\b{re.escape(fr)}\b", en, t)
    t = re.sub(r"(\d{1,2})h(\d{2})", r"\1:\2", t)
    t = re.sub(r"(\d{1,2})h\b", r"\1:00", t)
    return t

def _next_weekday(base: datetime, target_wd: int, next_week: bool = False) -> datetime:
    days_ahead = (target_wd - base.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return base + timedelta(days=days_ahead)

def extract_datetime_iso(
    text: str,
    base_dt: datetime | None = None,
    tz_name: str = "Europe/Paris"
) -> str | None:
    tz = gettz(tz_name)
    base = base_dt or datetime.now(tz=tz)

    t = _normalize_text(text)

    if not t:
        return None

    m = re.search(r"\b(il y a|ago)\s+(\d+)\s*(minute|minutes|min|hour|hours|heure|heures|day|days|jour|jours)\b", t)
    if m:
        n = int(m.group(2))
        unit = m.group(3)
        if unit.startswith(("min", "minute")):
            dt = base - timedelta(minutes=n)
        elif unit.startswith(("hour", "heure")):
            dt = base - timedelta(hours=n)
        else:
            dt = base - timedelta(days=n)
        return dt.isoformat()

    m = re.search(r"\b(il y a)?\s*(\d+)\s*(h|heure|heures|hours)\b", t)
    if m and ("il y a" in t or "ago" in t):
        n = int(m.group(2))
        dt = base - timedelta(hours=n)
        return dt.isoformat()

    if re.search(r"\b(aujourd'hui|today)\b", t):
        day = base
        hhmm = re.search(r"\b(\d{1,2}:\d{2})\b", t)
        if hhmm:
            h, mi = map(int, hhmm.group(1).split(":"))
            day = day.replace(hour=h, minute=mi, second=0, microsecond=0)
        return day.isoformat()

    if re.search(r"\b(demain|tomorrow)\b", t):
        day = base + timedelta(days=1)
        hhmm = re.search(r"\b(\d{1,2}:\d{2})\b", t)
        if hhmm:
            h, mi = map(int, hhmm.group(1).split(":"))
            day = day.replace(hour=h, minute=mi, second=0, microsecond=0)
        else:
            day = day.replace(hour=12, minute=0, second=0, microsecond=0)
        return day.isoformat()

    if re.search(r"\b(après-demain|apres-demain)\b", t):
        day = base + timedelta(days=2)
        hhmm = re.search(r"\b(\d{1,2}:\d{2})\b", t)
        if hhmm:
            h, mi = map(int, hhmm.group(1).split(":"))
            day = day.replace(hour=h, minute=mi, second=0, microsecond=0)
        else:
            day = day.replace(hour=12, minute=0, second=0, microsecond=0)
        return day.isoformat()

    m = re.search(r"\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b(?:\s+(prochain|suivant))?", t)
    if m:
        wd = FR_WEEKDAYS[m.group(1)]
        dt = _next_weekday(base, wd, next_week=bool(m.group(2)))
        hhmm = re.search(r"\b(\d{1,2}:\d{2})\b", t)
        if hhmm:
            h, mi = map(int, hhmm.group(1).split(":"))
            dt = dt.replace(hour=h, minute=mi, second=0, microsecond=0)
        else:
            dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)
        return dt.isoformat()

    m = re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b(?:\s+(next|this))?", t)
    if m:
        wd = EN_WEEKDAYS[m.group(1)]
        dt = _next_weekday(base, wd, next_week=(m.group(2) == "next"))
        hhmm = re.search(r"\b(\d{1,2}:\d{2})\b", t)
        if hhmm:
            h, mi = map(int, hhmm.group(1).split(":"))
            dt = dt.replace(hour=h, minute=mi, second=0, microsecond=0)
        else:
            dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)
        return dt.isoformat()

    try:
        dt = du_parser.parse(t, fuzzy=True, dayfirst=True, default=base)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.isoformat()
    except Exception:
        return None
