"""
Form Utilities Module

Shared utilities for form processing, data structures, and filename generation.
Reduces code duplication across routes.
"""

import re
from typing import Dict, List, Tuple


SECURITY_ITEMS: List[Tuple[str, str]] = [
    ('supervisors', 'Supervisors'),
    ('venue_security', 'Venue Security'),
    ('traffic_management', 'Traffic Management'),
    ('ticket_checkers', 'Ticket Checkers'),
    ('ushers', 'Ushers'),
    ('medics', 'Medics'),
    ('other', 'Other'),
    ('barriers', 'Barriers'),
    ('k9', 'K9'),
    ('sweeps', 'Sweeps'),
    ('vehicle_check', 'Vehicle Check'),
    ('magnetometers', 'Magnetometers'),
    ('bag_checks', 'Bag Checks'),
    ('screening', 'Screening')
]


def get_empty_hotel_data() -> Dict[str, str]:
    """Return empty data structure for hotel fields."""
    return {
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


def get_empty_hotel_ai_data() -> Dict[str, str]:
    """Return empty data structure for AI hotel assist (excludes distance_venue)."""
    return {
        'rooms_floors': '',
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


def get_empty_venue_data() -> Dict[str, str]:
    """Return empty data structure for venue fields."""
    return {
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


def get_empty_venue_ai_data() -> Dict[str, str]:
    """Return empty data structure for AI venue assist (subset of fields)."""
    return {
        'description': '',
        'parking': '',
        'entrance_access': '',
        'branding': '',
        'tv_advertising': '',
        'bowl_seating': '',
        'covid_provisions': '',
        'backstage': '',
        'security_provisions': ''
    }


def get_default_form_data() -> Dict:
    """
    Get default form data structure with all fields initialized.
    
    Returns:
        Dictionary with all form fields set to empty/default values.
    """
    data = {
        'has_two_hotels': False,
        'event_start_date': '',
        'event_end_date': '',
        'event_type': 'Disney On Ice',
        'event_city': '',
        'event_country': '',
        'hotel1_name': '',
        'hotel1_address': '',
        'hotel1_name_address': '',
        'hotel1_rooms_floors': '',
        'hotel1_distance_venue': '',
        'hotel1_facilities': '',
        'hotel1_wifi': '',
        'hotel1_surrounding': '',
        'hotel1_safety': '',
        'hotel1_security_staff': '',
        'hotel1_entrances': '',
        'hotel1_carpark': '',
        'hotel1_cctv_access': '',
        'hotel1_condition': '',
        'hotel1_overlapping': '',
        'hotel2_name': '',
        'hotel2_address': '',
        'hotel2_name_address': '',
        'hotel2_rooms_floors': '',
        'hotel2_distance_venue': '',
        'hotel2_facilities': '',
        'hotel2_wifi': '',
        'hotel2_surrounding': '',
        'hotel2_safety': '',
        'hotel2_security_staff': '',
        'hotel2_entrances': '',
        'hotel2_carpark': '',
        'hotel2_cctv_access': '',
        'hotel2_condition': '',
        'hotel2_overlapping': '',
        'venue_name': '',
        'venue_address': '',
        'venue_name_address': '',
        'venue_expected_capacity': '',
        'venue_description': '',
        'venue_photos_video': '',
        'venue_parking': '',
        'venue_entrance_access': '',
        'venue_branding': '',
        'venue_tv_advertising': '',
        'venue_bowl_seating': '',
        'venue_covid_provisions': '',
        'venue_backstage': '',
        'venue_response_k9': '',
        'venue_fcp_bootleggers': '',
        'venue_recommendations': '',
        'venue_security_provisions': '',
        'transport_airport': '',
        'transport_description': '',
    }
    
    for key, _ in SECURITY_ITEMS:
        data[f'security_{key}_count'] = ''
        data[f'security_{key}_comment'] = ''
    
    return data


def build_name_address_fields(form_data: Dict) -> Dict:
    """
    Build combined name_address fields for hotels and venue.
    Modifies and returns the form_data dict.
    
    Args:
        form_data: Form data dictionary to update.
        
    Returns:
        Updated form data with name_address fields populated.
    """
    if form_data.get('hotel1_name') or form_data.get('hotel1_address'):
        form_data['hotel1_name_address'] = f"{form_data.get('hotel1_name', '')} {form_data.get('hotel1_address', '')}".strip()
    
    if form_data.get('hotel2_name') or form_data.get('hotel2_address'):
        form_data['hotel2_name_address'] = f"{form_data.get('hotel2_name', '')} {form_data.get('hotel2_address', '')}".strip()
    
    if form_data.get('venue_name') or form_data.get('venue_address'):
        form_data['venue_name_address'] = f"{form_data.get('venue_name', '')} {form_data.get('venue_address', '')}".strip()
    
    return form_data


def build_security_data(form_data: Dict) -> Dict:
    """
    Build security data structure from form data.
    
    Args:
        form_data: Form data dictionary containing security fields.
        
    Returns:
        Dictionary with security item data organized by key.
    """
    security_data = {}
    for key, label in SECURITY_ITEMS:
        security_data[key] = {
            'label': label,
            'count': form_data.get(f'security_{key}_count', ''),
            'comment': form_data.get(f'security_{key}_comment', '')
        }
    return security_data


def generate_safe_filename(venue_name: str, extension: str = 'pdf') -> str:
    """
    Generate a safe filename from venue name.
    
    Args:
        venue_name: The venue name to use in the filename.
        extension: File extension without the dot (default: 'pdf').
        
    Returns:
        Safe filename string.
    """
    safe_name = re.sub(r'[^\w\s-]', '', venue_name or '').strip().replace(' ', '_')
    if not safe_name:
        safe_name = 'Report'
    return f"REPORT_LISTING_{safe_name}.{extension}"
