"""SerpAPI provider for Risk Brief."""
import requests
import logging
from datetime import datetime, timezone
from .config import SERPAPI_KEY, USER_AGENT
from .classifier import classify_event, confidence_score
from .geo import geocode_place
from .dateparser import extract_datetime_iso

logger = logging.getLogger(__name__)


def fetch_serpapi_news(city: str, country: str, max_results: int = 50) -> list:
    """Fetch news from SerpAPI Google News (if key configured)."""
    if not SERPAPI_KEY:
        return []

    q = f'{city} (homicide OR meurtre OR protest OR manifestation OR accident OR crash OR collision)'
    params = {
        "engine": "google_news",
        "q": q,
        "gl": "fr",
        "hl": "fr",
        "api_key": SERPAPI_KEY
    }
    headers = {"User-Agent": USER_AGENT}
    
    try:
        r = requests.get("https://serpapi.com/search.json", params=params, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"SerpAPI fetch error: {e}")
        return []

    out = []
    items = data.get("news_results", []) or []
    for it in items[:max_results]:
        title = it.get("title", "")
        link = it.get("link", "")
        source = (it.get("source") or "").strip() or "serpapi"

        dt_iso = ""
        ds = it.get("date", "")
        if ds:
            dt_iso = extract_datetime_iso(ds) or ""

        snippet = it.get("snippet", "") or ""
        category = classify_event(title, snippet)

        geo = geocode_place(city, country=country, limit=1)
        lat = geo["lat"] if geo else None
        lon = geo["lon"] if geo else None

        conf = confidence_score(source, corroborated=False, has_dt=bool(dt_iso), has_loc=True)

        if category != "UNKNOWN":
            out.append({
                "title": title[:180],
                "datetime": dt_iso,
                "category": category,
                "location": city,
                "lat": lat,
                "lon": lon,
                "source": source,
                "url": link,
                "confidence": conf,
                "raw": it
            })
    return out
