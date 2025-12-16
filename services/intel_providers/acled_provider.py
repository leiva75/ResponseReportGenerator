"""
ACLED API Provider - Primary source for security intelligence.

ACLED (Armed Conflict Location & Event Data) provides:
- Violent events (battles, explosions, violence against civilians)
- Fatalities count
- Demonstrations and protests
- Geo-coordinates

Requires free registration at developer.acleddata.com
Set ACLED_EMAIL and ACLED_API_KEY environment variables.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

ACLED_BASE_URL = "https://api.acleddata.com/acled/read"

EVENT_TYPES = {
    'violent': ['Battles', 'Explosions/Remote violence', 'Violence against civilians'],
    'demonstrations': ['Protests', 'Riots'],
    'strategic': ['Strategic developments']
}

DISORDER_TYPES = {
    'political_violence': 'Political violence',
    'demonstrations': 'Demonstrations'
}


class ACLEDProvider:
    """Provider for ACLED conflict event data."""
    
    def __init__(self):
        self.email = os.environ.get('ACLED_EMAIL', '')
        self.api_key = os.environ.get('ACLED_API_KEY', '')
        self.base_url = ACLED_BASE_URL
        self.timeout = 30
    
    def is_configured(self) -> bool:
        """Check if ACLED credentials are configured."""
        return bool(self.email and self.api_key)
    
    def _make_request(self, params: Dict) -> Dict:
        """Make request to ACLED API."""
        if not self.is_configured():
            return {
                'success': False,
                'error': 'ACLED API not configured. Set ACLED_EMAIL and ACLED_API_KEY.',
                'data': []
            }
        
        params['email'] = self.email
        params['key'] = self.api_key
        params['_format'] = 'json'
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success', True):
                    return {
                        'success': True,
                        'data': data.get('data', []),
                        'count': data.get('count', 0)
                    }
                else:
                    return {
                        'success': False,
                        'error': data.get('error', 'Unknown ACLED error'),
                        'data': []
                    }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': 'ACLED authentication failed. Check your API key.',
                    'data': []
                }
            elif response.status_code == 429:
                return {
                    'success': False,
                    'error': 'ACLED rate limit exceeded.',
                    'data': []
                }
            else:
                return {
                    'success': False,
                    'error': f'ACLED API error: {response.status_code}',
                    'data': []
                }
                
        except requests.Timeout:
            return {
                'success': False,
                'error': 'ACLED API timeout',
                'data': []
            }
        except requests.RequestException as e:
            logger.error(f'ACLED request error: {e}')
            return {
                'success': False,
                'error': str(e),
                'data': []
            }
    
    def get_violent_incidents(self, country: str, city: Optional[str] = None,
                               days: int = 30) -> Dict:
        """
        Get violent incidents from ACLED.
        
        Args:
            country: Country name
            city: Optional city/admin1 name for filtering
            days: Number of days to look back (default 30)
        
        Returns:
            Dict with success, incidents list, fatalities, and metadata
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            'country': country,
            'event_date_where': 'BETWEEN',
            'event_date': f'{start_date.strftime("%Y-%m-%d")}:{end_date.strftime("%Y-%m-%d")}',
            'event_type': '|'.join(EVENT_TYPES['violent']),
            'limit': 500
        }
        
        result = self._make_request(params)
        
        if not result['success']:
            return {
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'incidents': [],
                'total_fatalities': 0,
                'total_incidents': 0,
                'scope': 'N/A'
            }
        
        events = result.get('data', [])
        
        if city:
            city_lower = city.lower()
            city_events = [
                e for e in events 
                if city_lower in e.get('admin1', '').lower() or
                   city_lower in e.get('admin2', '').lower() or
                   city_lower in e.get('admin3', '').lower() or
                   city_lower in e.get('location', '').lower()
            ]
            if city_events:
                events = city_events
                scope = 'City'
            else:
                scope = 'Country (city-level data not available)'
        else:
            scope = 'Country'
        
        total_fatalities = sum(int(e.get('fatalities', 0) or 0) for e in events)
        
        incidents = []
        for event in events[:20]:
            incidents.append({
                'event_id': event.get('event_id_cnty', ''),
                'date': event.get('event_date', ''),
                'event_type': event.get('event_type', ''),
                'sub_event_type': event.get('sub_event_type', ''),
                'location': event.get('location', ''),
                'admin1': event.get('admin1', ''),
                'admin2': event.get('admin2', ''),
                'fatalities': int(event.get('fatalities', 0) or 0),
                'notes': event.get('notes', '')[:200] if event.get('notes') else '',
                'source': event.get('source', ''),
                'source_scale': event.get('source_scale', ''),
                'latitude': event.get('latitude', ''),
                'longitude': event.get('longitude', ''),
                'actor1': event.get('actor1', ''),
                'actor2': event.get('actor2', '')
            })
        
        trend = self._calculate_trend(events, days)
        
        return {
            'success': True,
            'incidents': incidents,
            'total_incidents': len(events),
            'total_fatalities': total_fatalities,
            'scope': scope,
            'trend': trend,
            'period_days': days,
            'source': 'ACLED'
        }
    
    def get_demonstrations(self, country: str, city: Optional[str] = None,
                            days: int = 14) -> Dict:
        """
        Get demonstrations and protests from ACLED.
        
        Args:
            country: Country name
            city: Optional city/admin1 name for filtering
            days: Number of days to look back (default 14)
        
        Returns:
            Dict with success, demonstrations list, and metadata
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            'country': country,
            'event_date_where': 'BETWEEN',
            'event_date': f'{start_date.strftime("%Y-%m-%d")}:{end_date.strftime("%Y-%m-%d")}',
            'event_type': '|'.join(EVENT_TYPES['demonstrations']),
            'limit': 500
        }
        
        result = self._make_request(params)
        
        if not result['success']:
            return {
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'demonstrations': [],
                'total_count': 0,
                'scope': 'N/A'
            }
        
        events = result.get('data', [])
        
        if city:
            city_lower = city.lower()
            city_events = [
                e for e in events 
                if city_lower in e.get('admin1', '').lower() or
                   city_lower in e.get('admin2', '').lower() or
                   city_lower in e.get('admin3', '').lower() or
                   city_lower in e.get('location', '').lower()
            ]
            if city_events:
                events = city_events
                scope = 'City'
            else:
                scope = 'Country (city-level data not available)'
        else:
            scope = 'Country'
        
        demonstrations = []
        for event in events[:15]:
            demonstrations.append({
                'event_id': event.get('event_id_cnty', ''),
                'date': event.get('event_date', ''),
                'event_type': event.get('event_type', ''),
                'sub_event_type': event.get('sub_event_type', ''),
                'location': event.get('location', ''),
                'admin1': event.get('admin1', ''),
                'fatalities': int(event.get('fatalities', 0) or 0),
                'notes': event.get('notes', '')[:200] if event.get('notes') else '',
                'source': event.get('source', ''),
                'latitude': event.get('latitude', ''),
                'longitude': event.get('longitude', ''),
                'actor1': event.get('actor1', '')
            })
        
        protests = [e for e in events if e.get('event_type') == 'Protests']
        riots = [e for e in events if e.get('event_type') == 'Riots']
        
        return {
            'success': True,
            'demonstrations': demonstrations,
            'total_count': len(events),
            'protests_count': len(protests),
            'riots_count': len(riots),
            'scope': scope,
            'period_days': days,
            'source': 'ACLED'
        }
    
    def _calculate_trend(self, events: List[Dict], days: int) -> str:
        """Calculate trend by comparing first half to second half of period."""
        if len(events) < 2:
            return 'stable'
        
        mid_date = datetime.now() - timedelta(days=days // 2)
        
        first_half = 0
        second_half = 0
        
        for event in events:
            try:
                event_date = datetime.strptime(event.get('event_date', ''), '%Y-%m-%d')
                if event_date >= mid_date:
                    second_half += 1
                else:
                    first_half += 1
            except ValueError:
                continue
        
        if first_half == 0:
            return 'increasing' if second_half > 0 else 'stable'
        
        ratio = second_half / first_half
        
        if ratio > 1.3:
            return 'increasing'
        elif ratio < 0.7:
            return 'decreasing'
        else:
            return 'stable'
    
    def get_country_summary(self, country: str) -> Dict:
        """Get summary statistics for a country."""
        incidents = self.get_violent_incidents(country, days=30)
        demos = self.get_demonstrations(country, days=14)
        
        return {
            'country': country,
            'violent_incidents_30d': incidents.get('total_incidents', 0),
            'fatalities_30d': incidents.get('total_fatalities', 0),
            'demonstrations_14d': demos.get('total_count', 0),
            'trend': incidents.get('trend', 'unknown'),
            'acled_available': incidents.get('success', False)
        }


def is_acled_available() -> bool:
    """Check if ACLED API credentials are configured."""
    provider = ACLEDProvider()
    return provider.is_configured()
