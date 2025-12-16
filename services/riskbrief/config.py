import os
from services.paths import get_cache_dir

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()
USER_AGENT = os.getenv("APP_USER_AGENT", "ResponseSecurityRiskBrief/1.0 (contact: ops@example.com)")

CACHE_DB = os.getenv("CACHE_DB", str(get_cache_dir() / "events_cache.db"))
DEFAULT_RADIUS_KM = float(os.getenv("DEFAULT_RADIUS_KM", "25"))
PAST_DAYS = int(os.getenv("PAST_DAYS", "30"))

KW_HOMICIDE = [
    "homicide", "murder", "killed", "shot", "shooting", "stabbing", "dead", "fatal shooting",
    "meurtre", "homicide", "tué", "abattu", "poignard", "assassinat"
]
KW_PROTEST = [
    "protest", "demonstration", "demonstrators", "rally", "march", "strike", "blocked", "riot",
    "manifestation", "rassemblement", "cortège", "grève", "barricade", "émeute"
]
KW_ACCIDENT = [
    "crash", "collision", "accident", "serious accident", "fatal accident", "car crash",
    "grave accident", "accident grave", "percuté", "heurté", "renversé", "blessé grave"
]
