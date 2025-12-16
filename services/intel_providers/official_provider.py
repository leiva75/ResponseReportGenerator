"""
Official Provider - Lightweight scraper for official government sources

This provider attempts to fetch data from official government pages when available.
If scraping fails or sources are unavailable, it gracefully falls back.

Note: Web scraping can be fragile. This provider is designed to fail gracefully
and indicate when official sources are unavailable.

Requires: requests, beautifulsoup4 (optional but recommended)
"""

import re
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


class OfficialProvider:
    """
    Official government source provider.
    
    Attempts to fetch data from official pages for demonstrations,
    traffic disruptions, and official announcements.
    
    Falls back gracefully if sources are unavailable.
    """
    
    OFFICIAL_SOURCES = {
        'FR': {
            'prefecture_base': 'https://www.prefecturedepolice.interieur.gouv.fr',
            'data_gouv': 'https://www.data.gouv.fr/api/1/datasets/',
        },
        'UK': {
            'police_uk': 'https://data.police.uk/api/',
            'gov_alerts': 'https://www.gov.uk/search/news-and-communications.json',
        },
        'DE': {
            'polizei': 'https://www.polizei.de',
        }
    }
    
    DEMONSTRATION_PATTERNS = {
        'fr': [r'manifestation', r'rassemblement', r'arrêté', r'fermeture', r'cortège'],
        'en': [r'demonstration', r'protest', r'road closure', r'public gathering'],
        'de': [r'demonstration', r'kundgebung', r'sperrung', r'versammlung'],
    }
    
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SecurityIntelligenceApp/1.0 (compatible; research purposes)'
        })
        self.bs4_available = BS4_AVAILABLE
    
    def _get_country_code(self, country: str) -> str:
        """Convert country name to code."""
        country_map = {
            'FRANCE': 'FR', 'GERMANY': 'DE', 'DEUTSCHLAND': 'DE',
            'UNITED KINGDOM': 'UK', 'ENGLAND': 'UK', 'GB': 'UK',
        }
        return country_map.get(country.upper(), country.upper()[:2])
    
    def _extract_text(self, html: str) -> str:
        """Extract text from HTML, using BeautifulSoup if available."""
        if self.bs4_available:
            soup = BeautifulSoup(html, 'html.parser')
            for script in soup(['script', 'style']):
                script.decompose()
            return soup.get_text(separator=' ', strip=True)
        else:
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
    
    def _fetch_uk_police_data(self, city: str, lat: float = None, lon: float = None) -> Dict:
        """
        Fetch crime data from Police.uk API (England & Wales only).
        Requires coordinates. If not provided, returns empty result.
        """
        if lat is None or lon is None:
            return {
                'data': [],
                'success': False,
                'error': 'Coordinates required for UK Police data'
            }
        
        try:
            url = f"https://data.police.uk/api/crimes-street/all-crime"
            params = {'lat': lat, 'lng': lon}
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code != 200:
                return {
                    'data': [],
                    'success': False,
                    'error': f'Police.uk returned status {response.status_code}'
                }
            
            crimes = response.json()
            
            crime_summary = {}
            for crime in crimes[:100]:
                category = crime.get('category', 'unknown')
                crime_summary[category] = crime_summary.get(category, 0) + 1
            
            return {
                'data': [{'category': k, 'count': v} for k, v in crime_summary.items()],
                'total': len(crimes),
                'success': True,
                'error': None,
                'source': 'Police.uk API',
                'source_url': 'https://data.police.uk/'
            }
            
        except Exception as e:
            return {
                'data': [],
                'success': False,
                'error': f'Police.uk error: {str(e)}'
            }
    
    def _search_gov_uk(self, city: str, query: str = 'security') -> Dict:
        """Search GOV.UK news and communications."""
        try:
            url = "https://www.gov.uk/search/news-and-communications.json"
            params = {
                'keywords': f'{city} {query}',
                'count': 10
            }
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code != 200:
                return {'articles': [], 'success': False}
            
            data = response.json()
            articles = []
            
            for result in data.get('results', []):
                articles.append({
                    'title': result.get('title', ''),
                    'url': f"https://www.gov.uk{result.get('link', '')}",
                    'date': result.get('public_timestamp', '')[:10] if result.get('public_timestamp') else '',
                    'source': 'GOV.UK',
                    'snippet': result.get('description', '')[:200]
                })
            
            return {
                'articles': articles,
                'success': True,
                'source': 'GOV.UK',
                'source_url': 'https://www.gov.uk/'
            }
            
        except Exception:
            return {'articles': [], 'success': False}
    
    def fetch_official_data(self, city: str, country: str, 
                            lat: float = None, lon: float = None) -> Dict:
        """
        Fetch official data for a location.
        
        Attempts multiple official sources based on country.
        Returns aggregated results with source information.
        """
        country_code = self._get_country_code(country)
        
        result = {
            'crime_data': [],
            'announcements': [],
            'success': False,
            'sources_checked': [],
            'sources_available': [],
            'error': None
        }
        
        if country_code == 'UK':
            police_data = self._fetch_uk_police_data(city, lat, lon)
            result['sources_checked'].append('Police.uk')
            
            if police_data.get('success'):
                result['crime_data'] = police_data.get('data', [])
                result['sources_available'].append({
                    'name': 'Police.uk',
                    'url': police_data.get('source_url')
                })
                result['success'] = True
            
            gov_data = self._search_gov_uk(city)
            result['sources_checked'].append('GOV.UK')
            
            if gov_data.get('success'):
                result['announcements'] = gov_data.get('articles', [])
                result['sources_available'].append({
                    'name': 'GOV.UK',
                    'url': gov_data.get('source_url')
                })
                result['success'] = True
        
        if not result['success']:
            result['error'] = 'Official sources unavailable for this location. Using alternative sources.'
        
        result['fetched_at'] = datetime.now().isoformat()
        
        return result
    
    def get_demonstration_alerts(self, city: str, country: str) -> Dict:
        """
        Attempt to fetch demonstration/rally alerts from official sources.
        
        Note: This is best-effort and may return empty if sources unavailable.
        """
        official = self.fetch_official_data(city, country)
        
        demos = []
        for announcement in official.get('announcements', []):
            title_lower = announcement.get('title', '').lower()
            snippet_lower = announcement.get('snippet', '').lower()
            
            for lang, patterns in self.DEMONSTRATION_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, title_lower) or re.search(pattern, snippet_lower):
                        demos.append(announcement)
                        break
        
        return {
            'demonstrations': demos,
            'success': len(demos) > 0 or official.get('success', False),
            'sources': official.get('sources_available', []),
            'note': 'Official sources checked' if official.get('sources_available') else 'Official sources unavailable'
        }
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if the provider dependencies are available."""
        return True
    
    @classmethod
    def has_beautifulsoup(cls) -> bool:
        """Check if BeautifulSoup is available for better parsing."""
        return BS4_AVAILABLE
