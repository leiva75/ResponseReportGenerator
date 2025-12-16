"""
City Security Brief Service
Main orchestration service for generating security briefs.
"""
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging
import os

from connectors.registry import get_registry
from services.security_cache import get_cache
from services.security_scoring import get_scorer
from services.security_normalize import get_normalizer

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "CitySecurityBrief/1.0 (touring-security-app)"


class SecurityBriefService:
    """Main service for generating city security briefs."""
    
    def __init__(self):
        self.registry = get_registry()
        self.cache = get_cache()
        self.scorer = get_scorer()
        self.normalizer = get_normalizer()
    
    def _geocode_location(self, city: str, country: str, address: Optional[str] = None) -> Tuple[Optional[float], Optional[float]]:
        """Geocode a location using Nominatim."""
        try:
            query = f"{city}, {country}"
            if address:
                query = f"{address}, {city}, {country}"
            
            params = {
                "q": query,
                "format": "json",
                "limit": 1
            }
            
            response = requests.get(
                NOMINATIM_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                if results:
                    lat = float(results[0]["lat"])
                    lon = float(results[0]["lon"])
                    logger.info(f"Geocoded {query} to ({lat}, {lon})")
                    return lat, lon
            
            logger.warning(f"Could not geocode {query}")
            return None, None
            
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None, None
    
    def generate_brief(
        self,
        city: str,
        country: str,
        address: Optional[str] = None,
        use_cache: bool = True,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """Generate a complete security brief for a city."""
        
        if use_cache:
            cached = self.cache.get(city, country, address, start_date, end_date)
            if cached:
                logger.info(f"Returning cached brief for {city}, {country}")
                cached["from_cache"] = True
                return cached
        
        lat, lon = self._geocode_location(city, country, address)
        
        raw_items = self.registry.fetch_all(city, country, lat, lon, address, start_date, end_date)
        
        items_as_dicts = []
        for item in raw_items:
            if hasattr(item, 'to_dict'):
                items_as_dicts.append(item.to_dict())
            elif isinstance(item, dict):
                items_as_dicts.append(item)
        
        scored_items = self.scorer.score_and_rank(items_as_dicts, lat, lon)
        
        risk_level, confidence = self.scorer.calculate_overall_risk(scored_items)
        
        brief = self.normalizer.normalize_to_brief(
            scored_items, city, country, risk_level, confidence
        )
        
        text_brief = self.normalizer.format_text_brief(brief)
        
        result = {
            "success": True,
            "brief": brief,
            "text_brief": text_brief,
            "coordinates": {"lat": lat, "lon": lon},
            "items_found": len(raw_items),
            "items_scored": len(scored_items),
            "from_cache": False
        }
        
        if use_cache:
            self.cache.set(city, country, result, address, start_date, end_date)
        
        return result
    
    def invalidate_cache(self, city: str, country: str, address: Optional[str] = None):
        """Force refresh by invalidating cache."""
        self.cache.invalidate(city, country, address)


_service_instance = None

def get_security_brief_service() -> SecurityBriefService:
    """Get the global service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = SecurityBriefService()
    return _service_instance
