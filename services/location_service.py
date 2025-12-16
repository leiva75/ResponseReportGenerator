"""
Location service for country/city autocomplete and validation.
Uses OpenStreetMap Nominatim for geocoding.
"""

import logging
import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

COMMON_COUNTRIES = [
    {"name": "France", "code": "FR"},
    {"name": "Germany", "code": "DE"},
    {"name": "United Kingdom", "code": "GB"},
    {"name": "Netherlands", "code": "NL"},
    {"name": "Belgium", "code": "BE"},
    {"name": "Spain", "code": "ES"},
    {"name": "Italy", "code": "IT"},
    {"name": "Switzerland", "code": "CH"},
    {"name": "Austria", "code": "AT"},
    {"name": "Portugal", "code": "PT"},
    {"name": "Denmark", "code": "DK"},
    {"name": "Sweden", "code": "SE"},
    {"name": "Norway", "code": "NO"},
    {"name": "Finland", "code": "FI"},
    {"name": "Poland", "code": "PL"},
    {"name": "Czech Republic", "code": "CZ"},
    {"name": "Hungary", "code": "HU"},
    {"name": "Ireland", "code": "IE"},
    {"name": "Luxembourg", "code": "LU"},
    {"name": "Greece", "code": "GR"},
    {"name": "Romania", "code": "RO"},
    {"name": "Bulgaria", "code": "BG"},
    {"name": "Croatia", "code": "HR"},
    {"name": "Slovakia", "code": "SK"},
    {"name": "Slovenia", "code": "SI"},
    {"name": "Estonia", "code": "EE"},
    {"name": "Latvia", "code": "LV"},
    {"name": "Lithuania", "code": "LT"},
    {"name": "Cyprus", "code": "CY"},
    {"name": "Malta", "code": "MT"},
    {"name": "United States", "code": "US"},
    {"name": "Canada", "code": "CA"},
    {"name": "Australia", "code": "AU"},
    {"name": "Japan", "code": "JP"},
    {"name": "China", "code": "CN"},
    {"name": "South Korea", "code": "KR"},
    {"name": "Brazil", "code": "BR"},
    {"name": "Mexico", "code": "MX"},
    {"name": "Argentina", "code": "AR"},
    {"name": "Russia", "code": "RU"},
    {"name": "Turkey", "code": "TR"},
    {"name": "United Arab Emirates", "code": "AE"},
    {"name": "Saudi Arabia", "code": "SA"},
    {"name": "South Africa", "code": "ZA"},
    {"name": "India", "code": "IN"},
    {"name": "Singapore", "code": "SG"},
    {"name": "New Zealand", "code": "NZ"},
    {"name": "Israel", "code": "IL"},
]

COUNTRY_CODE_MAP = {c["name"].lower(): c["code"] for c in COMMON_COUNTRIES}
COUNTRY_CODE_MAP.update({c["code"].lower(): c["code"] for c in COMMON_COUNTRIES})


def get_country_code(country_name: str) -> Optional[str]:
    """Get ISO country code from country name."""
    if not country_name:
        return None
    country_lower = country_name.lower().strip()
    return COUNTRY_CODE_MAP.get(country_lower)


def search_countries(query: str, limit: int = 10) -> List[Dict]:
    """
    Search for countries matching query.
    Returns list of country suggestions.
    """
    if not query or len(query) < 1:
        return COMMON_COUNTRIES[:limit]
    
    query_lower = query.lower().strip()
    results = []
    
    for country in COMMON_COUNTRIES:
        if query_lower in country["name"].lower() or query_lower == country["code"].lower():
            results.append(country)
            if len(results) >= limit:
                break
    
    return results


def search_cities(query: str, country: str = '', limit: int = 10) -> List[Dict]:
    """
    Search for cities matching query, optionally filtered by country.
    Uses OpenStreetMap Nominatim for geocoding.
    
    Returns list of city suggestions with name and country.
    """
    if not query or len(query) < 2:
        return []
    
    try:
        url = "https://nominatim.openstreetmap.org/search"
        
        params = {
            'q': query,
            'format': 'json',
            'addressdetails': 1,
            'limit': limit * 2,
            'featuretype': 'city'
        }
        
        country_code = get_country_code(country)
        if country_code:
            params['countrycodes'] = country_code
        
        headers = {
            'User-Agent': 'ReportListingApp/1.0 (security-report-generator)',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"Nominatim returned status {response.status_code}")
            return []
        
        data = response.json()
        results = []
        seen_cities = set()
        
        for place in data:
            place_type = place.get('type', '')
            place_class = place.get('class', '')
            
            if place_class not in ['place', 'boundary'] and place_type not in ['city', 'town', 'village', 'municipality', 'administrative']:
                continue
            
            address = place.get('address', {})
            city_name = (
                address.get('city') or 
                address.get('town') or 
                address.get('village') or 
                address.get('municipality') or
                place.get('name', '')
            )
            
            if not city_name:
                continue
            
            country_name = address.get('country', '')
            state = address.get('state', '')
            
            city_key = f"{city_name.lower()}_{country_name.lower()}"
            if city_key in seen_cities:
                continue
            seen_cities.add(city_key)
            
            results.append({
                'name': city_name,
                'state': state,
                'country': country_name,
                'country_code': address.get('country_code', '').upper(),
                'display': f"{city_name}, {country_name}" if country_name else city_name,
                'lat': place.get('lat'),
                'lon': place.get('lon')
            })
            
            if len(results) >= limit:
                break
        
        return results
        
    except requests.exceptions.Timeout:
        logger.warning("Nominatim city search timeout")
        return []
    except requests.exceptions.RequestException as e:
        logger.warning(f"Nominatim city search error: {e}")
        return []
    except Exception as e:
        logger.error(f"City search error: {e}")
        return []


def validate_city_in_country(city: str, country: str) -> bool:
    """
    Validate that a city exists in the given country.
    Returns True if the city is found in the country.
    """
    if not city or not country:
        return True
    
    results = search_cities(city, country, limit=5)
    
    city_lower = city.lower().strip()
    for result in results:
        if result['name'].lower() == city_lower:
            return True
    
    return len(results) > 0
