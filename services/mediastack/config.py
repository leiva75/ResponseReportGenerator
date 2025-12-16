import os
from services.paths import get_cache_dir

MEDIASTACK_API_KEY = os.environ.get("MEDIASTACK_API_KEY", "")
CACHE_TTL_HOURS = 6
CACHE_DB_PATH = str(get_cache_dir() / "mediastack_cache.db")

INCIDENT_KEYWORDS_ES = [
    "asesinato", "homicidio", "secuestro", "tiroteo", "balacera", 
    "violencia", "ataque", "explosión", "asalto", "cartel", "narco",
    "asesinado", "muerto", "matan", "disparo", "arma"
]

INCIDENT_KEYWORDS_EN = [
    "shooting", "homicide", "kidnapping", "violence", "attack", 
    "explosion", "murder", "killed", "gunfire", "cartel", "drug"
]

GATHERING_KEYWORDS_ES = [
    "manifestación", "protesta", "marcha", "huelga", "paro", 
    "bloqueo", "sindicato", "concentración", "movilización"
]

GATHERING_KEYWORDS_EN = [
    "strike", "protest", "demonstration", "march", "roadblock",
    "rally", "walkout", "union", "blockade"
]

FUTURE_KEYWORDS = [
    "mañana", "próximo", "convocan", "se realizará", "convocatoria",
    "this weekend", "planned", "will take place", "scheduled", 
    "upcoming", "tomorrow", "next week", "announced"
]

STRONG_VIOLENCE_KEYWORDS = [
    "asesinato", "homicidio", "tiroteo", "balacera", "explosión",
    "shooting", "homicide", "murder", "explosion", "killed"
]

USER_AGENT = "SecurityBriefBot/1.0"
