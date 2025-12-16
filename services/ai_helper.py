import os
import json
import requests

AI_INTEGRATIONS_OPENAI_API_KEY = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
AI_INTEGRATIONS_OPENAI_BASE_URL = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

openai_client = None

try:
    from openai import OpenAI
    if AI_INTEGRATIONS_OPENAI_API_KEY and AI_INTEGRATIONS_OPENAI_BASE_URL:
        openai_client = OpenAI(
            api_key=AI_INTEGRATIONS_OPENAI_API_KEY,
            base_url=AI_INTEGRATIONS_OPENAI_BASE_URL
        )
    elif OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
except Exception:
    openai_client = None

SEARCH_API_KEY = os.environ.get('SEARCH_API_KEY', '')


def is_ai_available():
    return openai_client is not None


def web_search(query, num_results=5):
    if not SEARCH_API_KEY:
        return []
    
    try:
        url = "https://serpapi.com/search"
        params = {
            'q': query,
            'api_key': SEARCH_API_KEY,
            'num': num_results
        }
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = []
        
        for item in data.get('organic_results', [])[:num_results]:
            results.append({
                'title': item.get('title', ''),
                'snippet': item.get('snippet', ''),
                'link': item.get('link', '')
            })
        
        return results
    except Exception:
        return []


def build_hotel_context(name, address, search_results):
    context = f"Hotel: {name}" if name else ""
    if address:
        context += f", Address: {address}" if context else f"Address: {address}"
    
    if search_results:
        context += "\n\nWeb search results:\n"
        for i, result in enumerate(search_results, 1):
            context += f"\n{i}. {result.get('title', '')}\n"
            context += f"   {result.get('snippet', '')}\n"
    
    return context


def build_venue_context(name, address, search_results):
    context = f"Venue: {name}" if name else ""
    if address:
        context += f", Address: {address}" if context else f"Address: {address}"
    
    if search_results:
        context += "\n\nWeb search results:\n"
        for i, result in enumerate(search_results, 1):
            context += f"\n{i}. {result.get('title', '')}\n"
            context += f"   {result.get('snippet', '')}\n"
    
    return context


def ai_assist_hotel(name, address, venue_address=None):
    if not is_ai_available():
        return {
            'success': False,
            'message': 'AI assistant not configured.',
            'data': {}
        }
    
    query = f"{name} {address}".strip() if name or address else ""
    if not query:
        return {
            'success': False,
            'message': 'Please enter a hotel name or address first.',
            'data': {}
        }
    
    search_results = web_search(f"{query} hotel information facilities amenities rooms parking")
    context = build_hotel_context(name, address, search_results)
    
    venue_context = ""
    if venue_address:
        venue_context = f"\nVenue address (for distance calculation): {venue_address}"
    
    prompt = f"""You are a hotel data assistant used in a logistics application for an international touring show.

Your mission:
- Search and provide information about this hotel in ENGLISH.
- If you are not sure about a value, leave the field empty "".
- Prioritize official sources (hotel website, booking.com, google maps, etc.).

Context:
{context}{venue_context}

Respond ONLY with a valid JSON object containing these fields:
- "rooms_floors": Number of rooms and floors (e.g., "200 rooms, 12 floors")
- "distance_venue": Distance and travel time to the venue if known (e.g., "5 km, 15 min by car")
- "facilities": Hotel amenities (gym, restaurants, pool, spa, etc.)
- "wifi": WiFi availability (free/paid, coverage)
- "surrounding": Immediate surroundings (banks, shops, cafes, transportation)
- "safety": General security assessment of the area
- "security_staff": Security staff presence (24/7, night reception, etc.)
- "entrances": Number and position of entrances (main, service, parking)
- "carpark": Car and bus parking (number of spaces, free/paid)
- "cctv_access": CCTV and access control (key cards, cameras in common areas)
- "condition": General condition of the property (modern, recently renovated, etc.)
- "overlapping": Known concurrent events (conferences, weddings, etc.)

Respond ONLY with a valid JSON object, no additional text."""

    try:
        if openai_client is None:
            return {
                'success': False,
                'message': 'AI assistant not configured.',
                'data': {}
            }
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=2048
        )
        
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        
        clean_data = {}
        for key in ['rooms_floors', 'distance_venue', 'facilities', 'wifi', 'surrounding', 'safety', 
                    'security_staff', 'entrances', 'carpark', 'cctv_access', 'condition', 'overlapping']:
            clean_data[key] = data.get(key, '') or ''
        
        has_data = any(v for v in clean_data.values() if v)
        
        if has_data:
            source_msg = "via web search and AI" if search_results else "via AI analysis"
            return {
                'success': True,
                'message': f'Hotel information retrieved {source_msg}.',
                'data': clean_data
            }
        else:
            return {
                'success': True,
                'message': 'No detailed information found. Please fill in manually.',
                'data': clean_data
            }
            
    except json.JSONDecodeError:
        return {
            'success': False,
            'message': 'Error parsing AI response. Please try again.',
            'data': {}
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'AI assistant error: {str(e)}',
            'data': {}
        }


def ai_assist_venue(name, address):
    if not is_ai_available():
        return {
            'success': False,
            'message': 'AI assistant not configured.',
            'data': {}
        }
    
    query = f"{name} {address}".strip() if name or address else ""
    if not query:
        return {
            'success': False,
            'message': 'Please enter a venue name or address first.',
            'data': {}
        }
    
    search_results = web_search(f"{query} venue arena stadium capacity seating")
    context = build_venue_context(name, address, search_results)
    
    prompt = f"""You are an assistant helping to gather information about an event venue for a security and event management report.

Based on the following context, provide information about this venue. If you cannot find reliable information for a field, leave it as an empty string "".

Context:
{context}

Please respond with a JSON object containing these fields:
- "description": Description of venue and surrounding area
- "parking": Car parking, coach parking, loading area information
- "entrance_access": Description of entrance area and access control
- "branding": Branding in arena/venue and surrounding area
- "tv_advertising": Any TV commercials, media advertising, billboards
- "bowl_seating": Bowl and seating area description
- "covid_provisions": Any specific COVID-19 provisions
- "backstage": Backstage, accreditation, storage, operations info
- "security_provisions": Security provisions, access control, CCTV

Respond ONLY with a valid JSON object, no additional text."""

    try:
        if openai_client is None:
            return {
                'success': False,
                'message': 'AI assistant not configured.',
                'data': {}
            }
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=2048
        )
        
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        
        clean_data = {}
        for key in ['description', 'parking', 'entrance_access', 'branding', 
                    'tv_advertising', 'bowl_seating', 'covid_provisions', 'backstage', 'security_provisions']:
            clean_data[key] = data.get(key, '') or ''
        
        has_data = any(v for v in clean_data.values() if v)
        
        if has_data:
            source_msg = "from web search and AI" if search_results else "from AI analysis"
            return {
                'success': True,
                'message': f'Venue information retrieved {source_msg}.',
                'data': clean_data
            }
        else:
            return {
                'success': True,
                'message': 'No detailed information found. Please fill in manually.',
                'data': clean_data
            }
            
    except json.JSONDecodeError:
        return {
            'success': False,
            'message': 'Error parsing AI response. Please try again.',
            'data': {}
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'AI assistant error: {str(e)}',
            'data': {}
        }


