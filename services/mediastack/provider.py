import os
import requests
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from .config import USER_AGENT
from services.location_service import get_country_code

logger = logging.getLogger(__name__)

MEDIASTACK_URL = "http://api.mediastack.com/v1/news"


def normalize_country_code(country_input: str) -> Optional[str]:
    """
    Normalize country input to ISO 3166-1 alpha-2 lowercase code.
    Accepts either country name (e.g., "France") or code (e.g., "FR").
    Returns lowercase alpha-2 code or None if unresolved.
    """
    if not country_input:
        return None
    
    original = country_input.strip()
    
    code = get_country_code(original)
    if code:
        return code.lower()
    
    logger.debug(f"Could not resolve country to ISO code: '{original}'")
    return None


def fetch_news(city: str, country: str, window_days: int = 14, limit: int = 30) -> list:
    """
    Fetch news articles from MediaStack API.
    
    Args:
        city: City name to search for in keywords
        country: Country name or ISO alpha-2 code
        window_days: Number of days to look back
        limit: Maximum number of articles to return
        
    Returns:
        List of article dictionaries
    """
    api_key = os.environ.get("MEDIASTACK_API_KEY", "")
    if not api_key:
        logger.warning("MEDIASTACK_API_KEY not configured")
        return []
    
    country_code = normalize_country_code(country)
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=window_days)
    
    lang_map = {
        "fr": "fr,en", "mx": "es,en", "es": "es,en", "de": "de,en",
        "it": "it,en", "pt": "pt,en", "br": "pt,en", "us": "en", "gb": "en"
    }
    languages = lang_map.get(country_code, "en") if country_code else "en"
    
    params = {
        "access_key": api_key,
        "languages": languages,
        "keywords": city,
        "sort": "published_desc",
        "limit": limit,
        "date": f"{start_date.strftime('%Y-%m-%d')},{end_date.strftime('%Y-%m-%d')}"
    }
    
    if country_code:
        params["countries"] = country_code
        logger.info(f"MediaStack query: city='{city}', country_code='{country_code}'")
    else:
        logger.warning(f"Omitting 'countries' param - could not resolve: '{country}'")
    
    headers = {"User-Agent": USER_AGENT}
    
    try:
        r = requests.get(MEDIASTACK_URL, params=params, headers=headers, timeout=30)
        data = r.json()
        
        if "error" in data:
            err = data["error"]
            logger.error(f"MediaStack API error: code={err.get('code')}, message={err.get('message')}")
            return []
        
        if r.status_code != 200:
            logger.error(f"MediaStack HTTP {r.status_code}")
            return []
        
        articles = data.get("data", []) or []
        logger.info(f"MediaStack returned {len(articles)} articles for {city}")
        return articles
        
    except requests.RequestException as e:
        logger.error(f"MediaStack request failed: {type(e).__name__}")
        return []
    except Exception as e:
        logger.error(f"MediaStack unexpected error: {type(e).__name__}")
        return []
