"""
Utility functions for security intelligence formatting and calculations.
"""

import math
from datetime import datetime
from typing import Dict, List, Optional


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def risk_level(distance_km: Optional[float]) -> str:
    """Determine risk level based on distance."""
    if distance_km is None:
        return "UNKNOWN"
    if distance_km < 1:
        return "IMMEDIATE"
    elif distance_km < 5:
        return "NEARBY"
    elif distance_km < 15:
        return "LOCAL"
    else:
        return "DISTANT"


def sort_events(events: List[Dict]) -> List[Dict]:
    """Sort events by distance (closest first), then by date (most recent first)."""
    def key(e: Dict):
        d = e.get("distance_km")
        dist_key = d if d is not None else 10**9
        dt = e.get("datetime") or e.get("date")
        try:
            ts = datetime.fromisoformat(str(dt)).timestamp()
        except Exception:
            ts = 0
        return (dist_key, -ts)

    return sorted(events, key=key)


def format_event_block(e: Dict) -> str:
    """Format an event as a compact operational block (4 lines max)."""
    cat = e.get("category", "UNKNOWN")
    loc = e.get("location", "unknown")
    dt = e.get("datetime") or e.get("date", "unknown")
    src = e.get("source", "-")
    conf = e.get("confidence", 0.0)

    dist = e.get("distance_km")
    dist_txt = f"{dist:.1f} km" if isinstance(dist, (int, float)) else "unknown"

    lvl = risk_level(dist)

    return "\n".join([
        f"{cat} — {loc} [{lvl}]",
        f"Distance: {dist_txt} from your position",
        f"Date: {dt}",
        f"Source: {src} — confidence {conf:.2f}"
    ])


def map_event_type_to_category(event_type: str, fatalities: int = 0) -> str:
    """Map ACLED/GDELT event types to operational categories."""
    if not event_type:
        return "SERIOUS ACCIDENT"
    
    t = event_type.lower()
    
    if any(kw in t for kw in ['homicide', 'murder', 'killing', 'violence against civilians']):
        return "HOMICIDE"
    if fatalities > 0:
        return "HOMICIDE"
    if any(kw in t for kw in ['protest', 'demonstration', 'riot', 'strike']):
        return "PROTEST"
    if any(kw in t for kw in ['explosion', 'battle', 'attack', 'armed']):
        return "SERIOUS ACCIDENT"
    
    return "SERIOUS ACCIDENT"


def get_confidence_score(source: str) -> float:
    """Return confidence score based on data source."""
    if not source:
        return 0.5
    src = source.upper()
    if src == 'ACLED':
        return 0.9
    if 'GDELT' in src:
        return 0.7
    if 'RSS' in src:
        return 0.5
    if 'POLICE' in src or 'GOV' in src:
        return 0.85
    return 0.6


def enrich_incident(incident: Dict, user_lat: float, user_lon: float) -> Dict:
    """Enrich an incident with distance, category, and confidence."""
    enriched = incident.copy()
    
    inc_lat = incident.get('latitude')
    inc_lon = incident.get('longitude')
    
    if inc_lat and inc_lon and user_lat and user_lon:
        try:
            enriched['distance_km'] = haversine_km(user_lat, user_lon, float(inc_lat), float(inc_lon))
        except (ValueError, TypeError):
            enriched['distance_km'] = None
    else:
        enriched['distance_km'] = None
    
    enriched['category'] = map_event_type_to_category(
        incident.get('event_type', ''),
        incident.get('fatalities', 0)
    )
    
    enriched['confidence'] = get_confidence_score(incident.get('source', ''))
    
    enriched['risk_level'] = risk_level(enriched.get('distance_km'))
    
    return enriched
