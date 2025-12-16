"""
Security Intelligence Assistant Module

This module provides AI-powered security briefs for hotels and venues.
The generate_security_brief() function is the main entry point.

To connect your own AI API:
1. Replace the openai_client calls with your preferred AI provider
2. Modify the prompt as needed for your use case
3. The function signature and return format should remain the same
"""

import os
import requests
from datetime import datetime

AI_INTEGRATIONS_OPENAI_API_KEY = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
AI_INTEGRATIONS_OPENAI_BASE_URL = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SEARCH_API_KEY = os.environ.get('SEARCH_API_KEY', '')

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


def is_security_ai_available():
    """Check if the Security Intelligence AI is available."""
    return openai_client is not None


def web_search_security(query, num_results=5):
    """
    Perform web search to gather security-relevant context.
    Uses SerpAPI if SEARCH_API_KEY is configured.
    
    Args:
        query: Search query string
        num_results: Maximum number of results to return
    
    Returns:
        List of search result dictionaries with title, snippet, link
    """
    if not SEARCH_API_KEY:
        return []
    
    try:
        url = "https://serpapi.com/search"
        params = {
            'q': query,
            'api_key': SEARCH_API_KEY,
            'num': num_results,
            'tbs': 'qdr:y'
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
                'link': item.get('link', ''),
                'date': item.get('date', '')
            })
        
        return results
    except Exception:
        return []


def gather_security_intelligence(location_name, location_address, city, location_type='venue'):
    """
    Gather comprehensive security intelligence from multiple search queries.
    Performs targeted searches for recent incidents, crime data, and area news.
    
    Args:
        location_name: Name of the venue/hotel
        location_address: Address of the location
        city: City name
        location_type: Either 'venue' or 'hotel'
    
    Returns:
        Dictionary with categorized search results
    """
    if not SEARCH_API_KEY:
        return {'has_search_data': False, 'context': ''}
    
    all_results = {
        'recent_incidents': [],
        'crime_safety': [],
        'local_news': [],
        'venue_info': []
    }
    
    base_location = f"{location_name} {city}".strip()
    
    search_queries = [
        (f'"{location_name}" {city} incident OR security OR problem 2024 2025', 'recent_incidents'),
        (f'{city} crime rate safety neighborhood 2024 2025', 'crime_safety'),
        (f'{city} news events security concerns', 'local_news'),
        (f'{location_name} {location_address} {city} {location_type} reviews', 'venue_info')
    ]
    
    for query, category in search_queries:
        results = web_search_security(query, num_results=3)
        all_results[category].extend(results)
    
    return build_comprehensive_context(all_results)


def build_comprehensive_context(categorized_results):
    """Build a comprehensive context string from categorized search results."""
    context_parts = []
    has_data = False
    
    if categorized_results.get('recent_incidents'):
        has_data = True
        context_parts.append("\n### Recent Incidents & Security Events:")
        for i, r in enumerate(categorized_results['recent_incidents'][:3], 1):
            date_str = f" ({r['date']})" if r.get('date') else ""
            context_parts.append(f"{i}. {r['title']}{date_str}")
            context_parts.append(f"   {r['snippet']}")
    
    if categorized_results.get('crime_safety'):
        has_data = True
        context_parts.append("\n### Area Crime & Safety Data:")
        for i, r in enumerate(categorized_results['crime_safety'][:3], 1):
            date_str = f" ({r['date']})" if r.get('date') else ""
            context_parts.append(f"{i}. {r['title']}{date_str}")
            context_parts.append(f"   {r['snippet']}")
    
    if categorized_results.get('local_news'):
        has_data = True
        context_parts.append("\n### Local News & Events:")
        for i, r in enumerate(categorized_results['local_news'][:3], 1):
            date_str = f" ({r['date']})" if r.get('date') else ""
            context_parts.append(f"{i}. {r['title']}{date_str}")
            context_parts.append(f"   {r['snippet']}")
    
    if categorized_results.get('venue_info'):
        has_data = True
        context_parts.append("\n### Venue/Location Information:")
        for i, r in enumerate(categorized_results['venue_info'][:3], 1):
            context_parts.append(f"{i}. {r['title']}")
            context_parts.append(f"   {r['snippet']}")
    
    if has_data:
        return {
            'has_search_data': True,
            'context': "\n\n## REAL-TIME INTELLIGENCE DATA (from web search):\n" + "\n".join(context_parts)
        }
    
    return {'has_search_data': False, 'context': ''}


def build_search_context(search_results):
    """Build context string from search results."""
    if not search_results:
        return ""
    
    context = "\n\nWeb search results for security context:\n"
    for i, result in enumerate(search_results, 1):
        context += f"\n{i}. {result.get('title', '')}\n"
        context += f"   {result.get('snippet', '')}\n"
    
    return context


def generate_security_brief_hotel(data):
    """
    Generate a security-oriented brief for a hotel.
    
    THIS IS THE MAIN ENTRY POINT FOR HOTEL SECURITY BRIEFS.
    
    Args:
        data: Dictionary containing:
            - hotel_name: Name of the hotel
            - hotel_address: Address of the hotel
            - city: City where the hotel is located
            - event_date: Date of the event (optional)
            - event_type: Type of event (optional)
            - additional_context: Any additional context (optional)
    
    Returns:
        Dictionary with:
            - success: Boolean indicating success/failure
            - message: Status message
            - brief: The security brief in Markdown format
    """
    if not is_security_ai_available():
        return {
            'success': False,
            'message': 'Security Intelligence AI not configured. Please set up an OpenAI API key.',
            'brief': ''
        }
    
    hotel_name = data.get('hotel_name', '').strip()
    hotel_address = data.get('hotel_address', '').strip()
    city = data.get('city', '').strip()
    event_date = data.get('event_date', '').strip()
    event_type = data.get('event_type', '').strip()
    additional_context = data.get('additional_context', '').strip()
    
    if not hotel_name and not hotel_address:
        return {
            'success': False,
            'message': 'Please enter a hotel name or address first.',
            'brief': ''
        }
    
    intel_data = gather_security_intelligence(hotel_name, hotel_address, city, 'hotel')
    search_context = intel_data.get('context', '')
    has_search_data = intel_data.get('has_search_data', False)
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_year = datetime.now().year
    
    location_info = f"Hotel: {hotel_name}" if hotel_name else ""
    if hotel_address:
        location_info += f"\nAddress: {hotel_address}"
    if city:
        location_info += f"\nCity: {city}"
    if event_date:
        location_info += f"\nEvent Date: {event_date}"
    if event_type:
        location_info += f"\nEvent Type: {event_type}"
    if additional_context:
        location_info += f"\nAdditional Context: {additional_context}"
    
    prompt = f"""You are a professional security operations consultant specializing in event security, VIP protection, and tour logistics. Your role is to provide security-oriented intelligence briefs that help operations teams anticipate and mitigate risks.

CURRENT DATE: {current_date}

LOCATION INFORMATION:
{location_info}
{search_context}

CRITICAL INSTRUCTION - UP-TO-DATE ANALYSIS:
This brief must reflect the CURRENT security situation as of {current_date}. Your analysis must:
- Consider any recent incidents or changes in the area (past 12 months)
- Account for current crime trends and safety conditions
- Reference any recent news or events that impact security
- If web search data is provided above, prioritize that information
- If no recent data is available, clearly state that verification of current conditions is required

INSTRUCTIONS:
Generate a comprehensive SECURITY BRIEF for this hotel location. Your analysis must be:
- Factual but security-focused
- Biased toward identifying risks and vulnerabilities
- Professional and actionable
- Honest about uncertainties (treat unknowns as potential risks)

Your response MUST follow this exact Markdown structure:

## Summary
(1-3 lines: Overall risk assessment and key security concerns)

## Context & Facts
(Factual description of the hotel and surrounding area:)
- Type of establishment and star rating if known
- Exact location and neighborhood context
- Main access routes, proximity to airport/train station
- Parking availability and access points
- General area characteristics (commercial, residential, industrial, tourist area)

## Risk Analysis
(Security-oriented analysis with bullet points:)
- **Crime & Safety**: Local crime levels, known incidents, areas to avoid
- **Crowd & Traffic**: Potential crowd density, traffic saturation, emergency vehicle access
- **Physical Vulnerabilities**: Building layout concerns (single access, glass facades, blind spots, underground parking)
- **Operational Constraints**: Load-in/load-out challenges, bus parking, luggage handling, night arrivals
- **Privacy & Exposure**: Separation between guests and public, media exposure risks

## Recommendations
(Numbered, prioritized operational actions:)
1. **Pre-arrival** - What to organize before arrival
2. **On-site procedures** - Security positioning, flow management, vehicle placement
3. **Rendez-vous points** - Where to establish meeting points
4. **Emergency protocols** - Evacuation routes, emergency contacts

## Points to Verify / Unknowns
(List missing or uncertain elements that require on-site verification:)
- Information that could not be confirmed
- Elements requiring physical reconnaissance
- Questions to ask hotel management

IMPORTANT: 
- If information is incomplete or ambiguous, explicitly state this and treat it as a potential risk
- Do not make up facts - acknowledge what is unknown
- Always include a "Last Updated" note at the end indicating this brief was generated on {current_date}
- If the situation may have changed since your knowledge cutoff, recommend verification"""

    try:
        if openai_client is None:
            return {
                'success': False,
                'message': 'Security Intelligence AI not configured.',
                'brief': ''
            }
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=4096
        )
        
        brief = response.choices[0].message.content or ""
        
        if brief:
            source_msg = "with real-time intelligence data" if has_search_data else "based on available information (configure SEARCH_API_KEY for real-time data)"
            return {
                'success': True,
                'message': f'Security brief generated {source_msg}.',
                'brief': brief
            }
        else:
            return {
                'success': False,
                'message': 'AI returned empty response. Please try again.',
                'brief': ''
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Security AI error: {str(e)}',
            'brief': ''
        }


def generate_security_brief_venue(data):
    """
    Generate a security-oriented brief for a venue.
    
    THIS IS THE MAIN ENTRY POINT FOR VENUE SECURITY BRIEFS.
    
    Args:
        data: Dictionary containing:
            - venue_name: Name of the venue
            - venue_address: Address of the venue
            - city: City where the venue is located
            - event_date: Date of the event (optional)
            - event_type: Type of event (optional)
            - expected_capacity: Expected attendance (optional)
            - additional_context: Any additional context (optional)
    
    Returns:
        Dictionary with:
            - success: Boolean indicating success/failure
            - message: Status message
            - brief: The security brief in Markdown format
    """
    if not is_security_ai_available():
        return {
            'success': False,
            'message': 'Security Intelligence AI not configured. Please set up an OpenAI API key.',
            'brief': ''
        }
    
    venue_name = data.get('venue_name', '').strip()
    venue_address = data.get('venue_address', '').strip()
    city = data.get('city', '').strip()
    event_date = data.get('event_date', '').strip()
    event_type = data.get('event_type', '').strip()
    expected_capacity = data.get('expected_capacity', '').strip()
    additional_context = data.get('additional_context', '').strip()
    
    if not venue_name and not venue_address:
        return {
            'success': False,
            'message': 'Please enter a venue name or address first.',
            'brief': ''
        }
    
    intel_data = gather_security_intelligence(venue_name, venue_address, city, 'venue')
    search_context = intel_data.get('context', '')
    has_search_data = intel_data.get('has_search_data', False)
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_year = datetime.now().year
    
    location_info = f"Venue: {venue_name}" if venue_name else ""
    if venue_address:
        location_info += f"\nAddress: {venue_address}"
    if city:
        location_info += f"\nCity: {city}"
    if event_date:
        location_info += f"\nEvent Date: {event_date}"
    if event_type:
        location_info += f"\nEvent Type: {event_type}"
    if expected_capacity:
        location_info += f"\nExpected Capacity: {expected_capacity}"
    if additional_context:
        location_info += f"\nAdditional Context: {additional_context}"
    
    prompt = f"""You are a professional security operations consultant specializing in event security, crowd management, and venue operations. Your role is to provide security-oriented intelligence briefs that help operations teams anticipate and mitigate risks at event venues.

CURRENT DATE: {current_date}

VENUE INFORMATION:
{location_info}
{search_context}

CRITICAL INSTRUCTION - UP-TO-DATE ANALYSIS:
This brief must reflect the CURRENT security situation as of {current_date}. Your analysis must:
- Consider any recent incidents or changes at this venue or in the surrounding area (past 12 months)
- Account for current crime trends and safety conditions in the neighborhood
- Reference any recent news, renovations, or events that impact security
- If web search data is provided above, prioritize that information
- If no recent data is available, clearly state that verification of current conditions is required

INSTRUCTIONS:
Generate a comprehensive SECURITY BRIEF for this venue. Your analysis must be:
- Factual but security-focused
- Biased toward identifying risks and vulnerabilities
- Professional and actionable
- Honest about uncertainties (treat unknowns as potential risks)

Your response MUST follow this exact Markdown structure:

## Summary
(1-3 lines: Overall risk assessment, venue type, key security concerns)

## Context & Facts
(Factual description of the venue and surrounding area:)
- Venue type (arena, theater, stadium, outdoor, etc.) and capacity
- Exact location and neighborhood context
- Main access routes and public transport links
- Parking facilities (public, VIP, production, coach parking)
- Load-in/load-out areas and production access
- Surrounding businesses, residential areas, gathering spots

## Risk Analysis
(Security-oriented analysis with bullet points:)
- **Crowd Management**: Entry/exit flow, bottlenecks, crowd density risks
- **Perimeter Security**: Access control points, fence lines, public/private separation
- **Physical Vulnerabilities**: Building design concerns, blind spots, single access points
- **Traffic & Access**: Vehicle flow, emergency access, production logistics
- **Historical Concerns**: Past incidents, known issues, fan behavior patterns
- **External Threats**: Scalpers, bootleggers, protesters, media access

## Recommendations
(Numbered, prioritized operational actions:)
1. **Pre-event setup** - Security positioning, barrier placement, signage
2. **Entry management** - Bag checks, magnetometer placement, queue management
3. **During event** - Patrol routes, crowd monitoring, communication points
4. **Egress procedures** - Controlled exit, vehicle staging, artist departure
5. **Emergency protocols** - Evacuation routes, rally points, medical access

## Points to Verify / Unknowns
(List missing or uncertain elements requiring on-site reconnaissance:)
- Information that could not be confirmed
- Elements requiring physical site survey
- Questions to ask venue management
- Local authority contacts to establish

IMPORTANT: 
- If information is incomplete or ambiguous, explicitly state this and treat it as a potential risk
- Do not make up facts - acknowledge what is unknown
- Always include a "Last Updated" note at the end indicating this brief was generated on {current_date}
- If the situation may have changed since your knowledge cutoff, recommend verification"""

    try:
        if openai_client is None:
            return {
                'success': False,
                'message': 'Security Intelligence AI not configured.',
                'brief': ''
            }
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=4096
        )
        
        brief = response.choices[0].message.content or ""
        
        if brief:
            source_msg = "with real-time intelligence data" if has_search_data else "based on available information (configure SEARCH_API_KEY for real-time data)"
            return {
                'success': True,
                'message': f'Security brief generated {source_msg}.',
                'brief': brief
            }
        else:
            return {
                'success': False,
                'message': 'AI returned empty response. Please try again.',
                'brief': ''
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Security AI error: {str(e)}',
            'brief': ''
        }


def generate_security_brief(data, brief_type='hotel'):
    """
    Unified entry point for generating security briefs.
    
    This is the main function to call from your application.
    
    Args:
        data: Dictionary with location and context information
        brief_type: Either 'hotel' or 'venue'
    
    Returns:
        Dictionary with success, message, and brief fields
    
    TO CONNECT YOUR OWN AI API:
    1. Modify the openai_client initialization at the top of this file
    2. Or replace the API call in generate_security_brief_hotel/venue
    3. Keep the same return format for compatibility with the frontend
    """
    if brief_type == 'venue':
        return generate_security_brief_venue(data)
    else:
        return generate_security_brief_hotel(data)
