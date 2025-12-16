"""
Security Intelligence V2 - ACLED-based Analysis Engine

Primary source: ACLED (Armed Conflict Location & Event Data)
- Structured conflict event data
- Fatality counts
- Demonstrations and protests
- Geo-coordinates

Fallback chain:
1. MediaStack (if configured) - Real-time news from 7,500+ sources
2. GDELT + RSS (free) - Global news aggregation

Key functions:
- get_violent_incidents(city, country, days=30)
- get_demonstrations(city, country, days=14)
- build_risk_assessment(incidents, demonstrations)
- get_full_security_intel(city, country)

All data is sourced and no numbers are invented.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .intel_providers import (
    ACLEDProvider, GDELTProvider, RSSProvider, is_acled_available,
    MediaStackProvider, is_mediastack_available
)
from .security_intel_cache import SecurityIntelCache
from .intel_utils import enrich_incident, sort_events, get_confidence_score

logger = logging.getLogger(__name__)

CITY_COUNTRY_MAPPINGS = {
    'mexico': {
        'city': 'Mexico City',
        'aliases': ['Ciudad de México', 'CDMX', 'DF'],
        'country': 'Mexico'
    },
    'singapore': {
        'city': 'Singapore',
        'aliases': ['Singapore City', 'SG'],
        'country': 'Singapore'
    },
    'luxembourg': {
        'city': 'Luxembourg City',
        'aliases': ['Ville de Luxembourg'],
        'country': 'Luxembourg'
    },
    'monaco': {
        'city': 'Monaco',
        'aliases': ['Monte Carlo', 'Monaco-Ville'],
        'country': 'Monaco'
    },
    'panama': {
        'city': 'Panama City',
        'aliases': ['Ciudad de Panamá'],
        'country': 'Panama'
    },
    'guatemala': {
        'city': 'Guatemala City',
        'aliases': ['Ciudad de Guatemala'],
        'country': 'Guatemala'
    },
    'kuwait': {
        'city': 'Kuwait City',
        'aliases': ['Al Kuwayt'],
        'country': 'Kuwait'
    },
    'djibouti': {
        'city': 'Djibouti City',
        'aliases': ['Djibouti'],
        'country': 'Djibouti'
    },
}

COUNTRY_NAMES = {
    'mexico', 'singapore', 'luxembourg', 'monaco', 'panama', 
    'guatemala', 'kuwait', 'djibouti', 'san marino', 'andorra',
    'liechtenstein', 'vatican', 'brazil', 'argentina', 'chile',
    'colombia', 'peru', 'venezuela', 'ecuador', 'bolivia',
    'paraguay', 'uruguay', 'france', 'germany', 'spain', 'italy',
    'portugal', 'netherlands', 'belgium', 'austria', 'switzerland',
    'poland', 'czech', 'hungary', 'greece', 'sweden', 'norway',
    'denmark', 'finland', 'ireland', 'united kingdom', 'uk',
    'russia', 'ukraine', 'turkey', 'egypt', 'morocco', 'algeria',
    'tunisia', 'south africa', 'nigeria', 'kenya', 'ethiopia',
    'japan', 'china', 'korea', 'india', 'thailand', 'vietnam',
    'indonesia', 'philippines', 'malaysia', 'australia', 'canada'
}

ISO2_TO_COUNTRY = {
    'AT': 'Austria', 'BE': 'Belgium', 'BG': 'Bulgaria', 'HR': 'Croatia',
    'CZ': 'Czech Republic', 'DK': 'Denmark', 'EE': 'Estonia', 'FI': 'Finland',
    'FR': 'France', 'DE': 'Germany', 'GR': 'Greece', 'HU': 'Hungary',
    'IE': 'Ireland', 'IT': 'Italy', 'LV': 'Latvia', 'LT': 'Lithuania',
    'NL': 'Netherlands', 'NO': 'Norway', 'PL': 'Poland', 'PT': 'Portugal',
    'RO': 'Romania', 'SK': 'Slovakia', 'SI': 'Slovenia', 'ES': 'Spain',
    'SE': 'Sweden', 'CH': 'Switzerland', 'GB': 'United Kingdom',
    'US': 'United States', 'CA': 'Canada', 'AU': 'Australia', 'NZ': 'New Zealand',
    'JP': 'Japan', 'CN': 'China', 'KR': 'South Korea', 'IN': 'India',
    'BR': 'Brazil', 'AR': 'Argentina', 'MX': 'Mexico', 'CL': 'Chile',
    'RU': 'Russia', 'UA': 'Ukraine', 'TR': 'Turkey', 'EG': 'Egypt',
    'ZA': 'South Africa', 'NG': 'Nigeria', 'KE': 'Kenya', 'MA': 'Morocco'
}


def convert_iso2_to_country(country_input: str) -> str:
    """Convert ISO2 code to full country name if applicable."""
    if not country_input:
        return country_input
    upper = country_input.upper().strip()
    if upper in ISO2_TO_COUNTRY:
        return ISO2_TO_COUNTRY[upper]
    return country_input


def normalize_city_country(city: str, country: str) -> Dict:
    """
    Normalize city/country input to handle edge cases.
    
    Handles cases where:
    - city equals country name (e.g., "Mexico" as city)
    - city is actually a country name
    
    Returns:
        Dict with 'city', 'country', 'city_aliases' keys
    """
    city_lower = city.lower().strip() if city else ''
    country_lower = country.lower().strip() if country else ''
    
    if city_lower in CITY_COUNTRY_MAPPINGS:
        mapping = CITY_COUNTRY_MAPPINGS[city_lower]
        return {
            'city': mapping['city'],
            'country': mapping['country'] if not country else country,
            'city_aliases': mapping['aliases']
        }
    
    if city_lower == country_lower:
        if city_lower in CITY_COUNTRY_MAPPINGS:
            mapping = CITY_COUNTRY_MAPPINGS[city_lower]
            return {
                'city': mapping['city'],
                'country': country,
                'city_aliases': mapping['aliases']
            }
        else:
            return {
                'city': city,
                'country': country,
                'city_aliases': [f"{city} City", city]
            }
    
    if city_lower in COUNTRY_NAMES and city_lower != country_lower:
        return {
            'city': f"{city} City" if not city.endswith('City') else city,
            'country': city if not country else country,
            'city_aliases': [city]
        }
    
    return {
        'city': city,
        'country': country,
        'city_aliases': []
    }


def get_violent_incidents(city: str, country: str, days: int = 30,
                           use_cache: bool = True,
                           offline_mode: bool = False) -> Dict:
    """
    Get violent incidents for a location.
    
    Uses ACLED as primary source, falls back to GDELT if not configured.
    
    Args:
        city: City name
        country: Country name
        days: Number of days to look back (default 30)
        use_cache: Whether to use cached data (default True)
        offline_mode: Only use cached data, don't fetch (default False)
    
    Returns:
        Dict with incidents, total count, fatalities, trend, scope
    """
    cache = SecurityIntelCache()
    cache_key = f"incidents_v2_{city}_{country}_{days}"
    
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            cached['from_cache'] = True
            return cached
    
    if offline_mode:
        return {
            'success': False,
            'incidents': [],
            'total_incidents': 0,
            'total_fatalities': 0,
            'trend': 'unknown',
            'scope': 'N/A',
            'source': 'offline',
            'offline': True,
            'message': 'Offline mode - no cached data available'
        }
    
    acled = ACLEDProvider()
    if acled.is_configured():
        result = acled.get_violent_incidents(country, city, days)
        if result['success']:
            result['source'] = 'ACLED'
            result['fetched_at'] = datetime.now().isoformat()
            if use_cache:
                cache.set(cache_key, result)
            return result
        else:
            logger.warning(f"ACLED failed: {result.get('error')}, falling back to GDELT")
    
    normalized = normalize_city_country(city, country)
    norm_city = normalized['city']
    norm_country = normalized['country']
    city_aliases = normalized['city_aliases']
    
    result = _get_incidents_from_fallback(norm_city, norm_country, days, city_aliases)
    result['fetched_at'] = datetime.now().isoformat()
    
    if use_cache and result.get('success'):
        cache.set(cache_key, result)
    
    return result


def _get_incidents_from_fallback(city: str, country: str, days: int,
                                  city_aliases: List[str] = None) -> Dict:
    """
    Fallback: Get incidents from news sources.
    
    Priority: MediaStack (if configured) -> GDELT + RSS (free)
    """
    all_articles = []
    source_name = None
    
    if is_mediastack_available():
        try:
            mediastack = MediaStackProvider()
            ms_result = mediastack.get_incident_articles(city, country)
            if ms_result.get('success') and ms_result.get('articles'):
                all_articles.extend(ms_result.get('articles', []))
                source_name = 'MediaStack'
                logger.info(f"MediaStack returned {len(ms_result.get('articles', []))} incident articles")
        except Exception as e:
            logger.warning(f"MediaStack failed: {e}")
    
    if not all_articles:
        gdelt = GDELTProvider()
        gdelt_result = gdelt.get_homicide_articles(city, country, days, city_aliases=city_aliases)
        
        if gdelt_result.get('success'):
            all_articles.extend(gdelt_result.get('articles', []))
        
        try:
            rss = RSSProvider()
            rss_result = rss.get_homicide_articles(city, country, days)
            if rss_result.get('success'):
                all_articles.extend(rss_result.get('articles', []))
        except Exception:
            pass
        
        source_name = 'GDELT+RSS'
    
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        url = article.get('url', '')
        if url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    
    incidents = []
    for article in unique_articles[:15]:
        incidents.append({
            'date': article.get('date', ''),
            'event_type': 'News-based incident',
            'location': city,
            'admin1': '',
            'fatalities': 0,
            'notes': (article.get('title') or article.get('description', ''))[:200],
            'source': article.get('source', ''),
            'url': article.get('url', '')
        })
    
    city_matches = sum(1 for a in unique_articles if city.lower() in f"{a.get('title', '')} {a.get('description', '')}".lower())
    if city_matches > len(unique_articles) * 0.3:
        scope = 'City'
    else:
        scope = 'Country (news-based)'
    
    return {
        'success': True,
        'incidents': incidents,
        'total_incidents': len(unique_articles),
        'total_fatalities': 0,
        'trend': 'unknown',
        'scope': scope,
        'source': source_name or 'GDELT+RSS',
        'disclaimer': 'News-based count (not official statistics)'
    }


def get_demonstrations(city: str, country: str, days: int = 14,
                        use_cache: bool = True,
                        offline_mode: bool = False) -> Dict:
    """
    Get demonstrations and protests for a location.
    
    Uses ACLED as primary source, falls back to GDELT if not configured.
    
    Args:
        city: City name
        country: Country name
        days: Number of days to look back (default 14)
        use_cache: Whether to use cached data (default True)
        offline_mode: Only use cached data, don't fetch (default False)
    
    Returns:
        Dict with demonstrations list, counts, scope
    """
    cache = SecurityIntelCache()
    cache_key = f"demos_v2_{city}_{country}_{days}"
    
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            cached['from_cache'] = True
            return cached
    
    if offline_mode:
        return {
            'success': False,
            'demonstrations': [],
            'total_count': 0,
            'protests_count': 0,
            'riots_count': 0,
            'scope': 'N/A',
            'source': 'offline',
            'offline': True,
            'message': 'Offline mode - no cached data available'
        }
    
    acled = ACLEDProvider()
    if acled.is_configured():
        result = acled.get_demonstrations(country, city, days)
        if result['success']:
            result['source'] = 'ACLED'
            result['fetched_at'] = datetime.now().isoformat()
            if use_cache:
                cache.set(cache_key, result)
            return result
        else:
            logger.warning(f"ACLED demos failed: {result.get('error')}, falling back to news sources")
    
    normalized = normalize_city_country(city, country)
    norm_city = normalized['city']
    norm_country = normalized['country']
    city_aliases = normalized['city_aliases']
    
    result = _get_demos_from_fallback(norm_city, norm_country, days, city_aliases)
    result['fetched_at'] = datetime.now().isoformat()
    
    if use_cache and result.get('success'):
        cache.set(cache_key, result)
    
    return result


def _get_demos_from_fallback(city: str, country: str, days: int,
                              city_aliases: List[str] = None) -> Dict:
    """
    Fallback: Get demonstrations from news sources.
    
    Priority: MediaStack (if configured) -> GDELT + RSS (free)
    """
    all_articles = []
    source_name = None
    
    if is_mediastack_available():
        try:
            mediastack = MediaStackProvider()
            ms_result = mediastack.get_demonstration_articles(city, country)
            if ms_result.get('success') and ms_result.get('articles'):
                all_articles.extend(ms_result.get('articles', []))
                source_name = 'MediaStack'
                logger.info(f"MediaStack returned {len(ms_result.get('articles', []))} demonstration articles")
        except Exception as e:
            logger.warning(f"MediaStack failed for demos: {e}")
    
    if not all_articles:
        gdelt = GDELTProvider()
        gdelt_result = gdelt.get_demonstration_articles(city, country, days, city_aliases=city_aliases)
        
        if gdelt_result.get('success'):
            all_articles.extend(gdelt_result.get('articles', []))
        
        try:
            rss = RSSProvider()
            rss_result = rss.get_demonstration_articles(city, country, days)
            if rss_result.get('success'):
                all_articles.extend(rss_result.get('articles', []))
        except Exception:
            pass
        
        source_name = 'GDELT+RSS'
    
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        url = article.get('url', '')
        if url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    
    demonstrations = []
    for article in unique_articles[:10]:
        demonstrations.append({
            'date': article.get('date', ''),
            'event_type': 'Protest (news-based)',
            'location': city,
            'admin1': '',
            'fatalities': 0,
            'notes': (article.get('title') or article.get('description', ''))[:200],
            'source': article.get('source', ''),
            'url': article.get('url', '')
        })
    
    city_matches = sum(1 for a in unique_articles if city.lower() in f"{a.get('title', '')} {a.get('description', '')}".lower())
    if city_matches > len(unique_articles) * 0.3:
        scope = 'City'
    else:
        scope = 'Country (news-based)'
    
    return {
        'success': True,
        'demonstrations': demonstrations,
        'total_count': len(unique_articles),
        'protests_count': len(unique_articles),
        'riots_count': 0,
        'scope': scope,
        'source': source_name or 'GDELT+RSS',
        'disclaimer': 'News-based count (not official statistics)'
    }


def build_risk_assessment(incidents: Dict, demonstrations: Dict) -> Dict:
    """
    Build a deterministic risk assessment based on collected data.
    
    Risk scoring:
    - Unknown: No data or insufficient data to assess
    - High risk: Many incidents with fatalities AND active demonstrations
    - Medium risk: Some incidents OR active demonstrations
    - Low risk: Verified low activity with good data coverage
    
    Args:
        incidents: Result from get_violent_incidents()
        demonstrations: Result from get_demonstrations()
    
    Returns:
        Dict with overall_risk, risk_score, drivers, operational_notes, confidence, warnings
    """
    incident_count = incidents.get('total_incidents', 0)
    fatality_count = incidents.get('total_fatalities', 0)
    demo_count = demonstrations.get('total_count', 0)
    riots_count = demonstrations.get('riots_count', 0)
    trend = incidents.get('trend', 'unknown')
    
    incidents_source = incidents.get('source', 'Unknown')
    demos_source = demonstrations.get('source', 'Unknown')
    incidents_success = incidents.get('success', False)
    demos_success = demonstrations.get('success', False)
    
    warnings = []
    
    has_acled = incidents_source == 'ACLED' or demos_source == 'ACLED'
    has_any_data = incident_count > 0 or demo_count > 0
    both_failed = not incidents_success and not demos_success
    
    risk_score = 0
    
    if incident_count >= 50:
        risk_score += 40
    elif incident_count >= 20:
        risk_score += 30
    elif incident_count >= 5:
        risk_score += 20
    elif incident_count >= 1:
        risk_score += 10
    
    if fatality_count >= 50:
        risk_score += 25
    elif fatality_count >= 20:
        risk_score += 15
    elif fatality_count >= 5:
        risk_score += 10
    elif fatality_count >= 1:
        risk_score += 5
    
    if demo_count >= 20:
        risk_score += 20
    elif demo_count >= 5:
        risk_score += 15
    elif demo_count >= 1:
        risk_score += 10
    
    if riots_count >= 5:
        risk_score += 15
    elif riots_count >= 1:
        risk_score += 10
    
    if trend == 'increasing':
        risk_score += 10
    elif trend == 'decreasing':
        risk_score -= 5
    
    if both_failed:
        overall_risk = "Unknown"
        confidence = "Low"
        warnings.append("Data sources unavailable - unable to assess risk")
    elif not has_acled and not has_any_data:
        overall_risk = "Unknown"
        confidence = "Low"
        warnings.append("Insufficient data coverage - risk cannot be determined")
    elif risk_score >= 60:
        overall_risk = "High"
        confidence = "High" if has_acled else "Medium"
    elif risk_score >= 30:
        overall_risk = "Medium"
        confidence = "High" if has_acled else "Medium"
    else:
        if has_acled:
            overall_risk = "Low"
            confidence = "High"
        elif has_any_data:
            overall_risk = "Low"
            confidence = "Medium"
            warnings.append("Low risk based on limited data sources")
        else:
            overall_risk = "Unknown"
            confidence = "Low"
            warnings.append("No verified data available for this location")
    
    drivers = []
    
    if incident_count > 0:
        driver_text = f"{incident_count} violent incident(s) recorded"
        if fatality_count > 0:
            driver_text += f" with {fatality_count} fatalities"
        driver_text += f" (past 30 days)"
        drivers.append(driver_text)
    
    if demo_count > 0:
        demo_text = f"{demo_count} demonstration(s) recorded"
        if riots_count > 0:
            demo_text += f" including {riots_count} riot(s)"
        demo_text += f" (past 14 days)"
        drivers.append(demo_text)
    
    if trend in ['increasing', 'decreasing']:
        drivers.append(f"Trend: {trend.capitalize()} incident activity")
    
    if not drivers:
        if overall_risk == "Unknown":
            drivers.append("Insufficient data to identify threats")
        else:
            drivers.append("No significant security incidents recorded")
    
    drivers = drivers[:3]
    
    operational_notes = []
    
    if overall_risk == "Unknown":
        operational_notes.append("Exercise standard precautions - data coverage limited")
        operational_notes.append("Consult local sources for current conditions")
    else:
        if fatality_count > 0:
            operational_notes.append("Heightened awareness recommended, especially in evening hours")
        
        if demo_count > 0:
            operational_notes.append("Monitor local news for demonstration routes and timing")
            if riots_count > 0:
                operational_notes.append("Avoid areas with reported unrest")
        
        if trend == 'increasing':
            operational_notes.append("Security situation deteriorating - plan contingencies")
        
        if not operational_notes:
            operational_notes.append("Standard security precautions recommended")
            operational_notes.append("Keep emergency contacts readily available")
    
    operational_notes = operational_notes[:4]
    
    return {
        'overall_risk': overall_risk,
        'risk_score': risk_score,
        'trend': trend,
        'drivers': drivers,
        'operational_notes': operational_notes,
        'confidence': confidence,
        'warnings': warnings,
        'data_sources': {
            'incidents': incidents_source,
            'demonstrations': demos_source
        },
        'disclaimer': 'Assessment based on recorded events data'
    }


def _get_news_context(city: str, country: str, primary_source: str) -> List[Dict]:
    """
    Fetch news context for a location from MediaStack or fallback sources.
    
    Returns list of news articles with title, source, url, date, description.
    """
    news_items = []
    
    try:
        if is_mediastack_available():
            provider = MediaStackProvider()
            result = provider.get_security_articles(city, country, limit=10)
            if result.get('success') and result.get('articles'):
                for article in result['articles'][:10]:
                    news_items.append({
                        'title': article.get('title', ''),
                        'source': article.get('source', 'MediaStack'),
                        'url': article.get('url', ''),
                        'date': article.get('date', ''),
                        'description': article.get('description', '')[:150] if article.get('description') else '',
                        'category': article.get('category', 'general')
                    })
                return news_items
        
        gdelt = GDELTProvider()
        gdelt_result = gdelt.get_crime_articles(city, country, days=7)
        gdelt_articles = gdelt_result.get('articles', []) if gdelt_result.get('success') else []
        for article in gdelt_articles[:10]:
            news_items.append({
                'title': article.get('title', ''),
                'source': article.get('source', 'GDELT'),
                'url': article.get('url', ''),
                'date': article.get('seendate', ''),
                'description': '',
                'category': 'news'
            })
        
    except Exception as e:
        logger.warning(f"Error fetching news context: {e}")
    
    return news_items


def _detect_planned_demonstrations(news_items: List[Dict]) -> List[Dict]:
    """
    Detect planned/announced demonstrations from news articles.
    
    Uses keyword matching to find future-oriented language indicating
    upcoming protests, strikes, or rallies.
    """
    import re
    
    FUTURE_KEYWORDS = [
        'planned', 'announced', 'scheduled', 'upcoming', 'will be held',
        'set to', 'expected to', 'due to take place', 'organizers say',
        'calling for', 'march on', 'strike on', 'protest on', 'rally on',
        'will gather', 'to protest', 'to demonstrate'
    ]
    
    EVENT_KEYWORDS = [
        'protest', 'demonstration', 'rally', 'march', 'strike', 'blockade',
        'sit-in', 'walkout', 'occupation', 'gathering'
    ]
    
    DATE_PATTERN = re.compile(
        r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*(?:\d{4})?)|'
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?)|'
        r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)|'
        r'(tomorrow|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week))',
        re.IGNORECASE
    )
    
    planned_demos = []
    
    for item in news_items:
        text = f"{item.get('title', '')} {item.get('description', '')}".lower()
        
        has_future = any(kw in text for kw in FUTURE_KEYWORDS)
        has_event = any(kw in text for kw in EVENT_KEYWORDS)
        
        if has_future and has_event:
            full_text = f"{item.get('title', '')} {item.get('description', '')}"
            date_match = DATE_PATTERN.search(full_text)
            extracted_date = date_match.group(0) if date_match else 'date TBD'
            
            planned_demos.append({
                'title': item.get('title', ''),
                'source': item.get('source', 'unknown'),
                'url': item.get('url', ''),
                'extracted_date': extracted_date,
                'label': 'media-announced (unverified)',
                'confidence': 'low'
            })
    
    return planned_demos[:5]


def _geocode_city(city: str, country: str) -> tuple:
    """Geocode a city to get lat/lon coordinates using Nominatim."""
    import requests
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{city}, {country}",
            'format': 'json',
            'limit': 1
        }
        headers = {'User-Agent': 'ResponseReportGenerator/1.0'}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0].get('lat', 0)), float(data[0].get('lon', 0))
    except Exception as e:
        logger.warning(f"Geocoding failed for {city}, {country}: {e}")
    return None, None


def get_full_security_intel(city: str, country: str,
                             incident_days: int = 30,
                             demo_days: int = 14,
                             use_cache: bool = True,
                             offline_mode: bool = False) -> Dict:
    """
    Get complete security intelligence for a location.
    
    This is the main entry point combining all analysis.
    
    Args:
        city: City name
        country: Country name (or ISO2 code)
        incident_days: Days to look back for incidents (default 30)
        demo_days: Days to look for demonstrations (default 14)
        use_cache: Use cached data (default True)
        offline_mode: Only use cache, don't fetch (default False)
    
    Returns:
        Complete security intel JSON matching the API spec:
        - meta
        - incidents_30d
        - demonstrations_14d
        - risk_assessment
        - news_context
    """
    country = convert_iso2_to_country(country)
    
    user_lat, user_lon = _geocode_city(city, country)
    
    incidents = get_violent_incidents(city, country, incident_days, use_cache, offline_mode)
    demonstrations = get_demonstrations(city, country, demo_days, use_cache, offline_mode)
    risk_assessment = build_risk_assessment(incidents, demonstrations)
    
    scope_used = incidents.get('scope', 'Unknown')
    source_used = incidents.get('source', 'Unknown')
    
    if source_used == 'ACLED':
        overall_confidence = "High"
    elif incidents.get('success') and demonstrations.get('success'):
        overall_confidence = "Medium"
    else:
        overall_confidence = "Low"
    
    incident_items = []
    raw_incidents = incidents.get('incidents', [])[:10]
    for inc in raw_incidents:
        inc['source'] = inc.get('source') or source_used
        enriched = enrich_incident(inc, user_lat, user_lon) if user_lat and user_lon else inc
        incident_items.append({
            'date': enriched.get('date', ''),
            'datetime': enriched.get('date', ''),
            'event_type': enriched.get('event_type', ''),
            'sub_event_type': enriched.get('sub_event_type', ''),
            'location': enriched.get('location', ''),
            'admin1': enriched.get('admin1', ''),
            'fatalities': enriched.get('fatalities', 0),
            'summary': enriched.get('notes', '')[:100] if enriched.get('notes') else '',
            'source': enriched.get('source', ''),
            'latitude': enriched.get('latitude', ''),
            'longitude': enriched.get('longitude', ''),
            'category': enriched.get('category', 'SERIOUS ACCIDENT'),
            'distance_km': enriched.get('distance_km'),
            'confidence': enriched.get('confidence', 0.6),
            'risk_level': enriched.get('risk_level', 'UNKNOWN')
        })
    incident_items = sort_events(incident_items)
    
    demo_items = []
    raw_demos = demonstrations.get('demonstrations', [])[:10]
    demo_source = demonstrations.get('source', 'Unknown')
    for demo in raw_demos:
        demo['source'] = demo.get('source') or demo_source
        enriched = enrich_incident(demo, user_lat, user_lon) if user_lat and user_lon else demo
        cat = 'PROTEST'
        if demo.get('event_type', '').lower().find('riot') >= 0:
            cat = 'RIOT'
        demo_items.append({
            'date': enriched.get('date', ''),
            'datetime': enriched.get('date', ''),
            'event_type': enriched.get('event_type', ''),
            'location': enriched.get('location', ''),
            'admin1': enriched.get('admin1', ''),
            'fatalities': enriched.get('fatalities', 0),
            'summary': enriched.get('notes', '')[:100] if enriched.get('notes') else '',
            'source': enriched.get('source', ''),
            'actor': enriched.get('actor1', ''),
            'latitude': enriched.get('latitude', ''),
            'longitude': enriched.get('longitude', ''),
            'category': cat,
            'distance_km': enriched.get('distance_km'),
            'confidence': enriched.get('confidence', 0.6),
            'risk_level': enriched.get('risk_level', 'UNKNOWN')
        })
    demo_items = sort_events(demo_items)
    
    incidents_source = incidents.get('source', 'Unknown')
    demos_source_name = demonstrations.get('source', 'Unknown')
    
    is_news_based = incidents_source not in ['ACLED']
    data_sources_list = []
    if incidents_source == 'ACLED':
        data_sources_list.append('ACLED')
    elif incidents_source == 'MediaStack':
        data_sources_list.append('MediaStack')
    elif incidents_source == 'GDELT' or incidents_source == 'GDELT+RSS':
        data_sources_list.append('GDELT')
    if demos_source_name == 'MediaStack':
        if 'MediaStack' not in data_sources_list:
            data_sources_list.append('MediaStack')
    elif demos_source_name == 'GDELT' or demos_source_name == 'GDELT+RSS':
        if 'GDELT' not in data_sources_list:
            data_sources_list.append('GDELT')
    if incidents.get('rss_used') or demonstrations.get('rss_used'):
        data_sources_list.append('RSS')
    if not data_sources_list:
        data_sources_list.append(incidents_source or 'Unknown')
    
    data_sources_display = '+'.join(data_sources_list)
    if is_news_based and 'ACLED' not in data_sources_list:
        data_sources_display += ' (news-based)'
    
    disclaimer_text = ''
    if is_news_based:
        disclaimer_text = 'Data is aggregated from news sources and may not reflect official statistics. Events are filtered by keyword matching and may include false positives.'
    
    news_context_items = _get_news_context(city, country, source_used)
    planned_demos = _detect_planned_demonstrations(news_context_items)
    
    return {
        'meta': {
            'updated_at': datetime.now().isoformat(),
            'fetched_at': datetime.now().isoformat(),
            'scope_used': scope_used,
            'confidence': overall_confidence,
            'city': city,
            'country': country,
            'user_lat': user_lat,
            'user_lon': user_lon,
            'offline_mode': offline_mode,
            'primary_source': source_used,
            'acled_available': is_acled_available(),
            'data_sources': data_sources_list,
            'data_sources_display': data_sources_display,
            'is_news_based': is_news_based,
            'disclaimer': disclaimer_text
        },
        'incidents_30d': {
            'total_count': incidents.get('total_incidents', 0),
            'total_fatalities': incidents.get('total_fatalities', 0),
            'trend': incidents.get('trend', 'unknown'),
            'summary': f"{incidents.get('total_incidents', 0)} incident(s), {incidents.get('total_fatalities', 0)} fatalities",
            'items': incident_items,
            'scope': incidents.get('scope', 'Unknown'),
            'source': source_used,
            'disclaimer': incidents.get('disclaimer', '')
        },
        'risk_assessment': risk_assessment,
        'demonstrations_14d': {
            'total_count': demonstrations.get('total_count', 0),
            'protests_count': demonstrations.get('protests_count', 0),
            'riots_count': demonstrations.get('riots_count', 0),
            'summary': f"{demonstrations.get('total_count', 0)} demonstration(s)",
            'items': demo_items,
            'planned_demos': planned_demos,
            'scope': demonstrations.get('scope', 'Unknown'),
            'source': demonstrations.get('source', 'Unknown')
        },
        'news_context': {
            'items': news_context_items[:5],
            'total_count': len(news_context_items),
            'source': 'MediaStack' if is_mediastack_available() else 'GDELT+RSS'
        }
    }


def is_security_intel_v2_available() -> bool:
    """Check if the V2 security intelligence module is available."""
    return True
