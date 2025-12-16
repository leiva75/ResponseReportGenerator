from difflib import SequenceMatcher
from .config import KW_HOMICIDE, KW_PROTEST, KW_ACCIDENT


def _contains_any(text: str, keywords: list) -> bool:
    t = (text or "").lower()
    return any(k in t for k in keywords)


def classify_event(title: str, snippet: str = "") -> str:
    txt = f"{title} {snippet}".lower()
    if _contains_any(txt, KW_HOMICIDE):
        return "HOMICIDE"
    if _contains_any(txt, KW_PROTEST):
        return "PROTEST"
    if _contains_any(txt, KW_ACCIDENT):
        return "SERIOUS ACCIDENT"
    return "UNKNOWN"


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def confidence_score(source_domain: str, corroborated: bool, has_dt: bool, has_loc: bool) -> float:
    base = 0.50
    major = any(x in (source_domain or "").lower() for x in [
        "lemonde", "bbc", "reuters", "apnews", "franceinfo", "francetvinfo", "theguardian",
        "nytimes", "washingtonpost", "tf1info", "france24", "sky", "dw", "elpais"
    ])
    if major:
        base += 0.20
    if corroborated:
        base += 0.15
    if not has_dt:
        base -= 0.15
    if not has_loc:
        base -= 0.10
    if base < 0.0:
        base = 0.0
    if base > 1.0:
        base = 1.0
    return base
