import os
import re
import unicodedata
import requests
import logging

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')


def normalize_text(text):
    """
    Normalize text for search comparison:
    - Convert to lowercase
    - Remove accents (é -> e, ü -> u, etc.)
    - Trim whitespace
    - Collapse multiple spaces
    """
    if not text:
        return ''
    
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'\s+', ' ', text)
    
    return text


def fuzzy_match(query, target, threshold=0.6):
    """
    Simple fuzzy matching: check if query terms are found in target.
    Returns True if match score exceeds threshold.
    """
    query_norm = normalize_text(query)
    target_norm = normalize_text(target)
    
    if not query_norm or not target_norm:
        return False
    
    if query_norm in target_norm:
        return True
    
    query_words = query_norm.split()
    target_words = target_norm.split()
    
    if not query_words:
        return False
    
    matches = 0
    for q_word in query_words:
        if len(q_word) < 2:
            matches += 1
            continue
        for t_word in target_words:
            if q_word in t_word or t_word in q_word:
                matches += 1
                break
            if len(q_word) >= 3 and len(t_word) >= 3:
                if q_word[:3] == t_word[:3]:
                    matches += 1
                    break
    
    score = matches / len(query_words)
    return score >= threshold


def search_hotels(query, city='', address='', country='', limit=10):
    """
    Search for hotels matching the query in the specified city/country.
    Robust search with:
    - Text normalization (accents, case)
    - Multiple API fallbacks (Photon -> Xotelo -> Google -> OpenStreetMap)
    - Search by name, address, city, country
    - Fuzzy matching for better results
    
    Args:
        query: Hotel name or partial name
        city: City name (optional but recommended)
        address: Address or partial address (optional)
        country: Country name (optional, improves accuracy)
        limit: Maximum number of results
    
    Returns:
        List of hotel suggestions with name and address
    """
    query = (query or '').strip()
    city = (city or '').strip()
    address = (address or '').strip()
    country = (country or '').strip()
    
    if not query and not city and not address:
        logger.debug("Hotel search: empty query, returning empty results")
        return []
    
    search_terms = []
    if query:
        search_terms.append(query)
    if city:
        search_terms.append(city)
    if country:
        search_terms.append(country)
    if address:
        search_terms.append(address)
    
    search_query = ' '.join(search_terms)
    
    logger.info(f"Hotel search: query='{query}', city='{city}', country='{country}', address='{address}'")
    
    results = _photon_search_hotels(search_query, limit * 2)
    if results:
        filtered = _filter_results(results, query, city, address, limit)
        if filtered:
            logger.info(f"Hotel search: found {len(filtered)} results via Photon")
            return filtered
        if results:
            logger.info(f"Hotel search: returning {len(results[:limit])} unfiltered Photon results")
            return results[:limit]
    
    results = _xotelo_search_hotels(search_query, limit * 2)
    if results:
        filtered = _filter_results(results, query, city, address, limit)
        if filtered:
            logger.info(f"Hotel search: found {len(filtered)} results via Xotelo")
            return filtered
        if results:
            logger.info(f"Hotel search: returning {len(results[:limit])} unfiltered Xotelo results")
            return results[:limit]
    
    if GOOGLE_MAPS_API_KEY:
        google_query = f"{query} hotel {city} {country}".strip() if city else f"{query} hotel"
        results = _google_search_places(google_query, 'lodging', limit * 2)
        if results:
            filtered = _filter_results(results, query, city, address, limit)
            if filtered:
                logger.info(f"Hotel search: found {len(filtered)} results via Google")
                return filtered
            logger.info(f"Hotel search: returning {len(results[:limit])} unfiltered Google results")
            return results[:limit]
    
    results = _nominatim_search_hotels(query, city, limit * 2, country)
    if results:
        filtered = _filter_results(results, query, city, address, limit)
        if filtered:
            logger.info(f"Hotel search: found {len(filtered)} results via Nominatim")
            return filtered
        logger.info(f"Hotel search: returning {len(results[:limit])} unfiltered Nominatim results")
        return results[:limit]
    
    if address and not query:
        logger.info("Hotel search: trying address-only search")
        results = _nominatim_search_by_address(address, city, limit)
        if results:
            return results
    
    logger.warning(f"Hotel search: no results found for query='{query}', city='{city}', country='{country}'")
    return []


def _filter_results(results, query, city, address, limit):
    """
    Filter results using fuzzy matching to improve relevance.
    """
    if not results:
        return []
    
    if not query and not address:
        return results[:limit]
    
    scored_results = []
    
    for item in results:
        item_name = item.get('name', '')
        item_address = item.get('address', '')
        score = 0
        
        if query:
            if fuzzy_match(query, item_name, 0.5):
                score += 2
            elif fuzzy_match(query, item_address, 0.5):
                score += 1
        
        if address:
            if fuzzy_match(address, item_address, 0.5):
                score += 2
        
        if city:
            if normalize_text(city) in normalize_text(item_address):
                score += 1
        
        if score > 0:
            scored_results.append((score, item))
    
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    return [item for _, item in scored_results[:limit]]


def _nominatim_search_by_address(address, city='', limit=10):
    """Search by address when name search fails."""
    try:
        search_query = f"{address} {city}".strip() if city else address
        
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': search_query,
            'format': 'json',
            'addressdetails': 1,
            'limit': limit
        }
        headers = {
            'User-Agent': 'ReportListingApp/1.0 (security-report-generator)',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = []
        
        for place in data:
            place_type = place.get('type', '')
            place_class = place.get('class', '')
            
            if place_class in ['tourism', 'building'] or place_type in ['hotel', 'hostel', 'guest_house', 'motel']:
                name = place.get('name', '') or place.get('display_name', '').split(',')[0]
                display_name = place.get('display_name', '')
                
                address_parts = display_name.split(',')[1:4] if ',' in display_name else []
                addr = ', '.join(p.strip() for p in address_parts) if address_parts else display_name
                
                if name:
                    results.append({
                        'name': name,
                        'address': addr,
                        'place_id': str(place.get('place_id', ''))
                    })
        
        return results
        
    except Exception as e:
        logger.error(f"Nominatim address search error: {e}")
        return []


def search_venues(query, city='', address='', limit=10):
    """
    Search for venues matching the query in the specified city.
    Robust search with text normalization and multiple fallbacks.
    
    Args:
        query: Venue name or partial name
        city: City name (optional but recommended)
        address: Address or partial address (optional)
        limit: Maximum number of results
    
    Returns:
        List of venue suggestions with name and address
    """
    query = (query or '').strip()
    city = (city or '').strip()
    address = (address or '').strip()
    
    if not query and not city and not address:
        logger.debug("Venue search: empty query, returning empty results")
        return []
    
    search_terms = []
    if query:
        search_terms.append(query)
    if address:
        search_terms.append(address)
    if city:
        search_terms.append(city)
    
    search_query = ' '.join(search_terms)
    
    logger.info(f"Venue search: query='{query}', city='{city}', address='{address}'")
    
    if GOOGLE_MAPS_API_KEY:
        results = _google_search_places(search_query, None, limit * 2)
        if results:
            filtered = _filter_results(results, query, city, address, limit)
            if filtered:
                logger.info(f"Venue search: found {len(filtered)} results via Google")
                return filtered
            logger.info(f"Venue search: returning {len(results[:limit])} unfiltered Google results")
            return results[:limit]
    
    results = _nominatim_search_venues(query, city, limit * 2)
    if results:
        filtered = _filter_results(results, query, city, address, limit)
        if filtered:
            logger.info(f"Venue search: found {len(filtered)} results via Nominatim")
            return filtered
        logger.info(f"Venue search: returning {len(results[:limit])} unfiltered Nominatim results")
        return results[:limit]
    
    logger.warning(f"Venue search: no results found for query='{query}', city='{city}'")
    return []


def _photon_search_hotels(query, limit=10):
    """Search for hotels using Photon API (powered by OpenStreetMap)."""
    try:
        url = "https://photon.komoot.io/api/"
        params = {
            'q': f"{query} hotel",
            'limit': limit,
            'osm_tag': 'tourism:hotel'
        }
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'ReportListingApp/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"Photon API returned status {response.status_code}")
            return []
        
        data = response.json()
        results = []
        
        for feature in data.get('features', [])[:limit]:
            props = feature.get('properties', {})
            name = props.get('name', '')
            
            coords = feature.get('geometry', {}).get('coordinates', [])
            lon = coords[0] if len(coords) > 0 else None
            lat = coords[1] if len(coords) > 1 else None
            
            address_parts = []
            if props.get('street'):
                addr_str = props.get('street')
                if props.get('housenumber'):
                    addr_str = f"{props.get('housenumber')} {addr_str}"
                address_parts.append(addr_str)
            if props.get('city') or props.get('town') or props.get('village'):
                address_parts.append(props.get('city') or props.get('town') or props.get('village'))
            if props.get('country'):
                address_parts.append(props.get('country'))
            
            address = ', '.join(address_parts) if address_parts else props.get('state', '')
            
            if name:
                results.append({
                    'name': name,
                    'address': address,
                    'place_id': str(props.get('osm_id', '')),
                    'lat': lat,
                    'lon': lon
                })
        
        return results
        
    except requests.exceptions.Timeout:
        logger.warning("Photon API timeout")
        return []
    except requests.exceptions.RequestException as e:
        logger.warning(f"Photon API request error: {e}")
        return []
    except Exception as e:
        logger.error(f"Photon search error: {e}")
        return []


def _xotelo_search_hotels(query, limit=10):
    """Search for hotels using Xotelo free API."""
    try:
        url = "https://data.xotelo.com/api/search"
        params = {'query': query}
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'ReportListingApp/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"Xotelo API returned status {response.status_code}")
            return []
        
        data = response.json()
        if not data:
            return []
        
        results = []
        
        result_data = data.get('result')
        if not result_data:
            return []
        
        hotel_list = result_data.get('list', []) if isinstance(result_data, dict) else []
        
        for hotel in hotel_list[:limit]:
            name = hotel.get('name', '')
            place_name = hotel.get('place_name', '')
            
            if name:
                results.append({
                    'name': name,
                    'address': place_name or '',
                    'place_id': hotel.get('key', '')
                })
        
        return results
        
    except requests.exceptions.Timeout:
        logger.warning("Xotelo API timeout")
        return []
    except requests.exceptions.RequestException as e:
        logger.warning(f"Xotelo API request error: {e}")
        return []
    except Exception as e:
        logger.error(f"Xotelo search error: {e}")
        return []


def _nominatim_search_hotels(query, city='', limit=10, country=''):
    """Search for hotels using OpenStreetMap Nominatim with hotel-specific query."""
    try:
        search_parts = []
        if query:
            search_parts.append(query)
        if city:
            search_parts.append(city)
        if country:
            search_parts.append(country)
        
        search_query = ' '.join(search_parts) + ' hotel'
        
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': search_query,
            'format': 'json',
            'addressdetails': 1,
            'limit': limit
        }
        headers = {
            'User-Agent': 'ReportListingApp/1.0 (security-report-generator)',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = []
        
        for place in data:
            name = place.get('name', '') or place.get('display_name', '').split(',')[0]
            display_name = place.get('display_name', '')
            
            lat = float(place.get('lat')) if place.get('lat') else None
            lon = float(place.get('lon')) if place.get('lon') else None
            
            address_parts = display_name.split(',')[1:4] if ',' in display_name else []
            address = ', '.join(p.strip() for p in address_parts) if address_parts else display_name
            
            if name:
                results.append({
                    'name': name,
                    'address': address,
                    'place_id': str(place.get('place_id', '')),
                    'lat': lat,
                    'lon': lon
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Nominatim hotel search error: {e}")
        return []


def _correct_city_name(city):
    """Correct common city name typos."""
    if not city:
        return city
    
    city_corrections = {
        'ultrecht': 'Utrecht',
        'utrech': 'Utrecht',
        'amsterdm': 'Amsterdam',
        'amstredam': 'Amsterdam',
        'roterdam': 'Rotterdam',
        'roterdm': 'Rotterdam',
        'brussel': 'Brussels',
        'bruxelle': 'Bruxelles',
        'pari': 'Paris',
        'londre': 'Londres',
        'londen': 'London',
        'berlin': 'Berlin',
        'munchen': 'München',
        'munich': 'Munich',
        'frankfort': 'Frankfurt',
        'frankfrt': 'Frankfurt',
        'dusseldorf': 'Düsseldorf',
        'dusseldrf': 'Düsseldorf',
        'colone': 'Cologne',
        'koln': 'Köln',
        'viena': 'Vienna',
        'vienne': 'Vienne',
        'geneve': 'Genève',
        'geneva': 'Geneva',
        'zuric': 'Zurich',
        'barcelone': 'Barcelona',
        'madri': 'Madrid',
        'lisbonne': 'Lisbon',
        'lisbone': 'Lisbon',
        'copenhague': 'Copenhagen',
        'copenhage': 'Copenhagen',
        'stockhol': 'Stockholm',
        'varsovie': 'Warsaw',
        'warszaw': 'Warsaw',
        'pragua': 'Prague',
        'praga': 'Prague',
        'oberhause': 'Oberhausen',
        'oberhausn': 'Oberhausen',
    }
    
    city_lower = normalize_text(city).split(',')[0].strip()
    
    for typo, correction in city_corrections.items():
        if typo in city_lower or city_lower in typo:
            if len(city_lower) >= len(typo) - 2:
                logger.info(f"City correction: '{city}' -> using correction hint '{correction}'")
                return city.replace(city.split(',')[0].strip(), correction)
    
    return city


def _get_venue_type_label(place_type, place_class):
    """Get a human-readable label for venue type."""
    type_labels = {
        'stadium': 'Stadium',
        'sports_centre': 'Sports Center',
        'sports_hall': 'Sports Hall',
        'ice_rink': 'Ice Rink',
        'theatre': 'Theatre',
        'cinema': 'Cinema',
        'concert_hall': 'Concert Hall',
        'conference_centre': 'Conference Center',
        'convention_center': 'Convention Center',
        'exhibition_centre': 'Exhibition Center',
        'events_venue': 'Events Venue',
        'community_centre': 'Community Center',
        'arts_centre': 'Arts Center',
        'music_venue': 'Music Venue',
        'nightclub': 'Nightclub',
        'auditorium': 'Auditorium',
        'arena': 'Arena',
        'pavilion': 'Pavilion',
        'hall': 'Hall',
        'amphitheatre': 'Amphitheatre',
        'park': 'Park',
        'fairground': 'Fairground',
        'zoo': 'Zoo',
        'theme_park': 'Theme Park',
        'attraction': 'Attraction',
        'museum': 'Museum',
        'gallery': 'Gallery',
        'hotel': 'Hotel',
        'company': 'Venue',
        'commercial': 'Commercial Venue',
    }
    
    if place_type in type_labels:
        return type_labels[place_type]
    if place_class == 'leisure':
        return 'Leisure Venue'
    if place_class == 'amenity':
        return 'Venue'
    if place_class == 'tourism':
        return 'Tourism Venue'
    if place_class == 'building':
        return 'Building'
    
    return ''


def _nominatim_search_venues(query, city='', limit=10):
    """Search for venues/arenas using OpenStreetMap Nominatim."""
    try:
        corrected_city = _correct_city_name(city)
        
        search_parts = []
        if query:
            search_parts.append(query)
        if corrected_city:
            search_parts.append(corrected_city)
        
        search_query = ' '.join(search_parts)
        
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': search_query,
            'format': 'json',
            'addressdetails': 1,
            'limit': limit,
            'extratags': 1
        }
        headers = {
            'User-Agent': 'ReportListingApp/1.0 (security-report-generator)',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = []
        
        for place in data:
            name = place.get('name', '') or place.get('display_name', '').split(',')[0]
            display_name = place.get('display_name', '')
            place_type = place.get('type', '')
            place_class = place.get('class', '')
            
            lat = float(place.get('lat')) if place.get('lat') else None
            lon = float(place.get('lon')) if place.get('lon') else None
            
            address_parts = display_name.split(',')[1:4] if ',' in display_name else []
            address = ', '.join(p.strip() for p in address_parts) if address_parts else display_name
            
            venue_type = _get_venue_type_label(place_type, place_class)
            
            if name:
                results.append({
                    'name': name,
                    'address': address,
                    'place_id': str(place.get('place_id', '')),
                    'venue_type': venue_type,
                    'lat': lat,
                    'lon': lon
                })
        
        if not results and query and corrected_city:
            logger.info(f"Venue search fallback: trying query only without city")
            params['q'] = query
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                for place in data:
                    name = place.get('name', '') or place.get('display_name', '').split(',')[0]
                    display_name = place.get('display_name', '')
                    place_type = place.get('type', '')
                    place_class = place.get('class', '')
                    lat = float(place.get('lat')) if place.get('lat') else None
                    lon = float(place.get('lon')) if place.get('lon') else None
                    address_parts = display_name.split(',')[1:4] if ',' in display_name else []
                    address = ', '.join(p.strip() for p in address_parts) if address_parts else display_name
                    venue_type = _get_venue_type_label(place_type, place_class)
                    if name:
                        results.append({
                            'name': name,
                            'address': address,
                            'place_id': str(place.get('place_id', '')),
                            'venue_type': venue_type,
                            'lat': lat,
                            'lon': lon
                        })
        
        return results
        
    except Exception as e:
        logger.error(f"Nominatim venue search error: {e}")
        return []


def _google_search_places(query, place_type=None, limit=10):
    """Search using Google Places Text Search API."""
    try:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': query,
            'key': GOOGLE_MAPS_API_KEY
        }
        if place_type:
            params['type'] = place_type
        
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = []
        
        for place in data.get('results', [])[:limit]:
            location = place.get('geometry', {}).get('location', {})
            results.append({
                'name': place.get('name', ''),
                'address': place.get('formatted_address', ''),
                'place_id': place.get('place_id', ''),
                'lat': location.get('lat'),
                'lon': location.get('lng')
            })
        
        return results
    except Exception:
        return []


def _nominatim_search_places(query, place_type=None, limit=10):
    """Search using OpenStreetMap Nominatim API."""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': query,
            'format': 'json',
            'addressdetails': 1,
            'limit': limit
        }
        headers = {
            'User-Agent': 'ReportListingApp/1.0 (contact@example.com)',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = []
        
        for place in data:
            name = place.get('name', '') or place.get('display_name', '').split(',')[0]
            address = place.get('display_name', '')
            
            results.append({
                'name': name,
                'address': address,
                'place_id': str(place.get('place_id', ''))
            })
        
        return results
    except Exception:
        return []

def build_search_query(name, address):
    """
    Build a single search query string from name and/or address.
    
    Rules:
    - If both are provided: "<name>, <address>"
    - If only name is provided: use the name
    - If only address is provided: use the address
    - If neither is provided: return empty string
    """
    name = (name or '').strip()
    address = (address or '').strip()
    
    if name and address:
        return f"{name}, {address}"
    elif name:
        return name
    elif address:
        return address
    else:
        return ''


def fetch_nominatim_data(query):
    """
    Fallback: Fetch place data from OpenStreetMap Nominatim API.
    Returns a dictionary with basic place information or empty dict if not found.
    
    This is used when no Google Maps API key is configured.
    """
    if not query:
        return {}
    
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': query,
            'format': 'json',
            'addressdetails': 1,
            'extratags': 1,
            'limit': 1
        }
        headers = {
            'User-Agent': 'ReportListingApp/1.0 (contact@example.com)',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return {}
        
        data = response.json()
        
        if not data or len(data) == 0:
            return {}
        
        result = data[0]
        
        place_info = {
            'display_name': result.get('display_name', ''),
            'name': result.get('name', ''),
            'type': result.get('type', ''),
            'class': result.get('class', ''),
            'lat': result.get('lat', ''),
            'lon': result.get('lon', ''),
            'address': result.get('address', {}),
            'extratags': result.get('extratags', {})
        }
        
        return place_info
        
    except requests.exceptions.Timeout:
        return {}
    except requests.exceptions.RequestException:
        return {}
    except Exception:
        return {}


def fetch_place_details(name, address):
    """
    Fetch place details from Google Maps Places API.
    Returns a dictionary with place information or empty dict if not found.
    """
    if not GOOGLE_MAPS_API_KEY:
        return {}
    
    query = build_search_query(name, address)
    if not query:
        return {}
    
    try:
        find_place_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            'input': query,
            'inputtype': 'textquery',
            'fields': 'place_id,name,formatted_address',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(find_place_url, params=params, timeout=10)
        data = response.json()
        
        if data.get('status') != 'OK' or not data.get('candidates'):
            return {}
        
        place_id = data['candidates'][0].get('place_id')
        if not place_id:
            return {}
        
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            'place_id': place_id,
            'fields': 'name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,types,opening_hours,reviews,vicinity',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        details_response = requests.get(details_url, params=details_params, timeout=10)
        details_data = details_response.json()
        
        if details_data.get('status') != 'OK':
            return {}
        
        result = details_data.get('result', {})
        
        place_info = {
            'name': result.get('name', ''),
            'address': result.get('formatted_address', ''),
            'phone': result.get('formatted_phone_number', ''),
            'website': result.get('website', ''),
            'rating': str(result.get('rating', '')) if result.get('rating') else '',
            'total_ratings': str(result.get('user_ratings_total', '')) if result.get('user_ratings_total') else '',
            'types': ', '.join(result.get('types', [])),
            'vicinity': result.get('vicinity', ''),
        }
        
        return place_info
        
    except Exception:
        return {}


def fetch_hotel_data_google(name, address):
    """
    Fetch hotel-specific data from Google Maps API.
    Returns a dictionary with hotel fields or empty values if not found.
    """
    place_info = fetch_place_details(name, address)
    
    hotel_data = {
        'rooms_floors': '',
        'distance_venue': '',
        'facilities': '',
        'wifi': '',
        'surrounding': '',
        'safety': '',
        'security_staff': '',
        'entrances': '',
        'carpark': '',
        'cctv_access': '',
        'condition': '',
        'overlapping': ''
    }
    
    if place_info:
        facilities_parts = []
        if place_info.get('types'):
            facilities_parts.append(f"Type: {place_info['types']}")
        if place_info.get('rating'):
            facilities_parts.append(f"Rating: {place_info['rating']}/5 ({place_info.get('total_ratings', '')} reviews)")
        if place_info.get('website'):
            facilities_parts.append(f"Website: {place_info['website']}")
        
        if facilities_parts:
            hotel_data['facilities'] = '; '.join(facilities_parts)
        
        if place_info.get('vicinity'):
            hotel_data['surrounding'] = f"Located in: {place_info['vicinity']}"
    
    return hotel_data


def fetch_hotel_data_nominatim(name, address):
    """
    Fetch hotel-specific data from OpenStreetMap Nominatim (fallback).
    Returns a dictionary with hotel fields or empty values if not found.
    """
    query = build_search_query(name, address)
    place_info = fetch_nominatim_data(query)
    
    hotel_data = {
        'rooms_floors': '',
        'distance_venue': '',
        'facilities': '',
        'wifi': '',
        'surrounding': '',
        'safety': '',
        'security_staff': '',
        'entrances': '',
        'carpark': '',
        'cctv_access': '',
        'condition': '',
        'overlapping': ''
    }
    
    if place_info:
        facilities_parts = []
        
        place_type = place_info.get('type', '')
        place_class = place_info.get('class', '')
        if place_type or place_class:
            type_str = f"{place_class}: {place_type}" if place_class and place_type else (place_type or place_class)
            facilities_parts.append(f"Type: {type_str}")
        
        extratags = place_info.get('extratags', {})
        if extratags.get('stars'):
            facilities_parts.append(f"Stars: {extratags['stars']}")
        if extratags.get('rooms'):
            hotel_data['rooms_floors'] = f"Rooms: {extratags['rooms']}"
        if extratags.get('internet_access'):
            hotel_data['wifi'] = f"Internet: {extratags['internet_access']}"
        if extratags.get('website'):
            facilities_parts.append(f"Website: {extratags['website']}")
        
        if facilities_parts:
            hotel_data['facilities'] = '; '.join(facilities_parts)
        
        address_info = place_info.get('address', {})
        if address_info:
            surrounding_parts = []
            if address_info.get('suburb'):
                surrounding_parts.append(address_info['suburb'])
            if address_info.get('city') or address_info.get('town'):
                surrounding_parts.append(address_info.get('city') or address_info.get('town'))
            if address_info.get('state'):
                surrounding_parts.append(address_info['state'])
            if surrounding_parts:
                hotel_data['surrounding'] = f"Located in: {', '.join(surrounding_parts)}"
    
    return hotel_data


def fetch_hotel_data(name, address):
    """
    Fetch hotel-specific data, using Google Maps API if available,
    otherwise falling back to OpenStreetMap Nominatim.
    
    Returns a tuple: (hotel_data_dict, source_message)
    """
    if GOOGLE_MAPS_API_KEY:
        data = fetch_hotel_data_google(name, address)
        source = 'google'
    else:
        data = fetch_hotel_data_nominatim(name, address)
        source = 'nominatim'
    
    return data, source


def fetch_venue_data_google(name, address):
    """
    Fetch venue-specific data from Google Maps API.
    Returns a dictionary with venue fields or empty values if not found.
    """
    place_info = fetch_place_details(name, address)
    
    venue_data = {
        'description': '',
        'photos_video': '',
        'parking': '',
        'entrance_access': '',
        'branding': '',
        'tv_advertising': '',
        'bowl_seating': '',
        'covid_provisions': '',
        'backstage': '',
        'response_k9': '',
        'fcp_bootleggers': '',
        'recommendations': '',
        'security_provisions': ''
    }
    
    if place_info:
        description_parts = []
        if place_info.get('name'):
            description_parts.append(f"Name: {place_info['name']}")
        if place_info.get('address'):
            description_parts.append(f"Address: {place_info['address']}")
        if place_info.get('types'):
            description_parts.append(f"Type: {place_info['types']}")
        if place_info.get('rating'):
            description_parts.append(f"Rating: {place_info['rating']}/5")
        if place_info.get('website'):
            description_parts.append(f"Website: {place_info['website']}")
        
        if description_parts:
            venue_data['description'] = '\n'.join(description_parts)
    
    return venue_data


def fetch_venue_data_nominatim(name, address):
    """
    Fetch venue-specific data from OpenStreetMap Nominatim (fallback).
    Returns a dictionary with venue fields or empty values if not found.
    """
    query = build_search_query(name, address)
    place_info = fetch_nominatim_data(query)
    
    venue_data = {
        'description': '',
        'photos_video': '',
        'parking': '',
        'entrance_access': '',
        'branding': '',
        'tv_advertising': '',
        'bowl_seating': '',
        'covid_provisions': '',
        'backstage': '',
        'response_k9': '',
        'fcp_bootleggers': '',
        'recommendations': '',
        'security_provisions': ''
    }
    
    if place_info:
        description_parts = []
        
        display_name = place_info.get('display_name', '')
        if display_name:
            name_part = display_name.split(',')[0].strip()
            description_parts.append(f"Name: {name_part}")
            description_parts.append(f"Address: {display_name}")
        
        place_type = place_info.get('type', '')
        place_class = place_info.get('class', '')
        if place_type or place_class:
            type_str = f"{place_class}: {place_type}" if place_class and place_type else (place_type or place_class)
            description_parts.append(f"Type: {type_str}")
        
        extratags = place_info.get('extratags', {})
        if extratags.get('website'):
            description_parts.append(f"Website: {extratags['website']}")
        if extratags.get('capacity'):
            description_parts.append(f"Capacity: {extratags['capacity']}")
        
        if description_parts:
            venue_data['description'] = '\n'.join(description_parts)
    
    return venue_data


def fetch_venue_data(name, address):
    """
    Fetch venue-specific data, using Google Maps API if available,
    otherwise falling back to OpenStreetMap Nominatim.
    
    Returns a tuple: (venue_data_dict, source_message)
    """
    if GOOGLE_MAPS_API_KEY:
        data = fetch_venue_data_google(name, address)
        source = 'google'
    else:
        data = fetch_venue_data_nominatim(name, address)
        source = 'nominatim'
    
    return data, source


def fetch_place_photo_wikipedia(query, place_type='hotel'):
    """
    Fetch a photo for a place using Wikipedia/Wikimedia Commons API.
    This is completely FREE and requires no API key.
    
    Args:
        query: Place name (hotel name, venue name, etc.)
        place_type: Type of place ('hotel', 'venue', 'arena', etc.)
    
    Returns:
        dict with photo_url, thumbnail_url, source or None if not found
    """
    if not query:
        return None
    
    try:
        search_query = query.split(',')[0].strip()
        
        search_url = "https://en.wikipedia.org/w/api.php"
        headers = {
            'User-Agent': 'ReportListingApp/1.0 (security-report-generator)',
            'Accept': 'application/json'
        }
        
        search_params = {
            'action': 'query',
            'generator': 'search',
            'gsrsearch': search_query,
            'gsrlimit': 3,
            'prop': 'pageimages',
            'piprop': 'thumbnail',
            'pithumbsize': 800,
            'pilicense': 'any',
            'format': 'json'
        }
        
        response = requests.get(search_url, params=search_params, headers=headers, timeout=5)
        if response.status_code != 200:
            return None
        
        data = response.json()
        pages = data.get('query', {}).get('pages', {})
        
        if not pages:
            return None
        
        for page_id, page_info in pages.items():
            if page_id == '-1':
                continue
            thumbnail = page_info.get('thumbnail', {})
            if thumbnail.get('source'):
                photo_url = thumbnail['source']
                thumb_url = photo_url.replace('/800px-', '/400px-') if '/800px-' in photo_url else photo_url
                page_title = page_info.get('title', query)
                
                logger.info(f"Wikipedia: found photo for '{query}' from page '{page_title}'")
                return {
                    'photo_url': photo_url,
                    'thumbnail_url': thumb_url,
                    'source': 'wikipedia'
                }
        
        return None
        
    except requests.exceptions.Timeout:
        logger.debug(f"Wikipedia API timeout for '{query}'")
        return None
    except Exception as e:
        logger.debug(f"Wikipedia photo error: {e}")
        return None


def fetch_place_photo_google(query, place_type='hotel'):
    """
    Fetch a photo for a place using Google Places API.
    
    Steps:
    1. Use Find Place API to get place_id from query
    2. Use Place Details API to get photo_reference
    3. Build photo URL using Places Photos API
    
    Args:
        query: Place name (hotel name, venue name, etc.)
        place_type: Type of place ('hotel', 'venue', 'arena', etc.)
    
    Returns:
        dict with photo_url, thumbnail_url, source or None if not found
    """
    if not GOOGLE_MAPS_API_KEY or not query:
        return None
    
    try:
        find_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        find_params = {
            'input': query,
            'inputtype': 'textquery',
            'fields': 'place_id,name,photos',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(find_url, params=find_params, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Google Find Place API returned {response.status_code}")
            return None
        
        data = response.json()
        candidates = data.get('candidates', [])
        
        if not candidates:
            logger.debug(f"Google Find Place: no candidates for '{query}'")
            return None
        
        place = candidates[0]
        photos = place.get('photos', [])
        
        if not photos:
            place_id = place.get('place_id')
            if place_id:
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_params = {
                    'place_id': place_id,
                    'fields': 'photos',
                    'key': GOOGLE_MAPS_API_KEY
                }
                details_resp = requests.get(details_url, params=details_params, timeout=10)
                if details_resp.status_code == 200:
                    details_data = details_resp.json()
                    result = details_data.get('result', {})
                    photos = result.get('photos', [])
        
        if not photos:
            logger.debug(f"Google Places: no photos found for '{query}'")
            return None
        
        photo_ref = photos[0].get('photo_reference')
        if not photo_ref:
            return None
        
        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_ref}&key={GOOGLE_MAPS_API_KEY}"
        thumbnail_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_ref}&key={GOOGLE_MAPS_API_KEY}"
        
        logger.info(f"Google Places: found photo for '{query}'")
        return {
            'photo_url': photo_url,
            'thumbnail_url': thumbnail_url,
            'source': 'google_maps'
        }
        
    except requests.exceptions.Timeout:
        logger.warning(f"Google Places Photo API timeout for '{query}'")
        return None
    except Exception as e:
        logger.error(f"Google Places Photo error: {e}")
        return None
