"""
Event collectors for Risk Brief - GDELT, SerpAPI with deduplication.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict

from .config import PAST_DAYS
from .cache import init_cache, upsert_event, load_cached
from .dedup import deduplicate
from .geo import geocode_city
from .providers_gdelt import fetch_gdelt
from .providers_serpapi import fetch_serpapi_news

logger = logging.getLogger(__name__)


def fetch_past_incidents(city: str, country: str, since_days: int = PAST_DAYS) -> List[Dict]:
    """
    Fetch past incidents from multiple sources with deduplication and caching.
    """
    init_cache()
    
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=since_days)
    
    cached = load_cached(city, country, start_dt.isoformat())
    
    events = []
    events += fetch_gdelt(city, country, start_dt, end_dt, max_records=120)
    events += fetch_serpapi_news(city, country, max_results=60)
    
    events = deduplicate(events)
    for e in events:
        upsert_event(city, country, e)
    
    merged = load_cached(city, country, start_dt.isoformat())
    
    result = deduplicate(merged)
    logger.info(f"Fetched {len(result)} deduplicated events for {city}, {country}")
    return result


def fetch_upcoming_protests(city: str, country: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
    """
    Fetch upcoming protests from news sources.
    """
    search_start = start_dt - timedelta(days=3)
    search_end = end_dt + timedelta(days=3)
    
    events = fetch_serpapi_news(city, country, max_results=60)
    events += fetch_gdelt(city, country, search_start, search_end, max_records=60)
    
    protests = [e for e in events if e.get("category") == "PROTEST"]
    
    return deduplicate(protests)
