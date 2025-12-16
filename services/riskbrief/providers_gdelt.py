"""GDELT provider for Risk Brief."""
import requests
import logging
from datetime import datetime, timezone
from .config import USER_AGENT
from .classifier import classify_event, confidence_score
from .geo import geocode_place

logger = logging.getLogger(__name__)

GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch_gdelt(city: str, country: str, start_dt: datetime, end_dt: datetime, max_records: int = 100) -> list:
    """Fetch events from GDELT DOC 2.1 API."""
    q = f'"{city}" (homicide OR murder OR killed OR shooting OR protest OR manifestation OR demonstration OR accident OR crash OR collision)'
    params = {
        "query": q,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(max_records),
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end_dt.strftime("%Y%m%d%H%M%S"),
        "sort": "HybridRel"
    }
    headers = {"User-Agent": USER_AGENT}
    
    try:
        r = requests.get(GDELT_DOC, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"GDELT fetch error: {e}")
        return []

    out = []
    for a in data.get("articles", []) or []:
        title = a.get("title", "")
        url = a.get("url", "")
        seendate = a.get("seendate") or a.get("datetime") or ""
        
        dt_iso = ""
        try:
            if seendate and len(seendate) >= 14 and seendate[:14].isdigit():
                dt = datetime.strptime(seendate[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                dt_iso = dt.isoformat()
        except Exception:
            dt_iso = ""

        snippet = a.get("sourceCountry", "")
        category = classify_event(title, snippet)

        source_domain = a.get("domain", "") or a.get("sourceCountry", "")
        location = city

        lat = lon = None
        geo = geocode_place(city, country=country, limit=1)
        if geo:
            lat, lon = geo["lat"], geo["lon"]

        conf = confidence_score(source_domain, corroborated=False, has_dt=bool(dt_iso), has_loc=True)

        if category != "UNKNOWN":
            out.append({
                "title": title[:180],
                "datetime": dt_iso or "",
                "category": category,
                "location": location,
                "lat": lat,
                "lon": lon,
                "source": source_domain or "gdelt",
                "url": url,
                "confidence": conf,
                "raw": a
            })

    return out
