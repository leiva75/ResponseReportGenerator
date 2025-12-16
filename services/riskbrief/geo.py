"""Geocoding utilities for Risk Brief."""
import requests
import logging
from typing import Optional, Dict
from .config import USER_AGENT

logger = logging.getLogger(__name__)

_geo_cache = {}


def geocode_place(place: str, country: str = "", limit: int = 1) -> Optional[Dict]:
    """Geocode a place name to lat/lon using Nominatim."""
    cache_key = f"{place}|{country}"
    if cache_key in _geo_cache:
        return _geo_cache[cache_key]
    
    try:
        query = f"{place}, {country}" if country else place
        url = "https://nominatim.openstreetmap.org/search"
        params = {'q': query, 'format': 'json', 'limit': limit}
        headers = {'User-Agent': USER_AGENT}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                result = {
                    'lat': float(data[0].get('lat', 0)),
                    'lon': float(data[0].get('lon', 0)),
                    'display_name': data[0].get('display_name', '')
                }
                _geo_cache[cache_key] = result
                return result
    except Exception as e:
        logger.warning(f"Geocoding failed for {place}, {country}: {e}")
    
    return None


def geocode_city(city: str, country: str) -> tuple:
    """Get lat/lon for a city."""
    geo = geocode_place(city, country)
    if geo:
        return geo['lat'], geo['lon']
    return None, None
