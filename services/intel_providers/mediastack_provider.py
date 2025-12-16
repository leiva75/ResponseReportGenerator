"""
MediaStack Provider - Real-time news data from MediaStack API

MediaStack provides access to 7,500+ global news sources with real-time updates.
Requires an API key (free tier: 100 requests/month).

API Documentation: https://mediastack.com/documentation
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MediaStackProvider:
    """
    MediaStack API Provider for real-time news data.
    
    Endpoint: https://api.mediastack.com/v1/news
    """
    
    BASE_URL = "http://api.mediastack.com/v1/news"
    
    SECURITY_KEYWORDS = [
        'crime', 'attack', 'violence', 'murder', 'assault', 'robbery',
        'protest', 'demonstration', 'riot', 'unrest', 'strike',
        'terrorism', 'explosion', 'shooting', 'stabbing', 'kidnapping',
        'theft', 'burglary', 'arrest', 'police', 'emergency'
    ]
    
    INCIDENT_KEYWORDS = [
        'crime', 'violence', 'attack', 'shooting', 'murder',
        'assault', 'stabbing', 'killed', 'death', 'fatal'
    ]
    
    DEMONSTRATION_KEYWORDS = [
        'protest', 'strike', 'demonstration', 'rally', 'march',
        'riot', 'unrest', 'blockade', 'uprising'
    ]
    
    COUNTRY_CODES = {
        'france': 'fr', 'germany': 'de', 'united kingdom': 'gb', 'uk': 'gb',
        'spain': 'es', 'italy': 'it', 'netherlands': 'nl', 'belgium': 'be',
        'portugal': 'pt', 'austria': 'at', 'switzerland': 'ch', 'poland': 'pl',
        'sweden': 'se', 'norway': 'no', 'denmark': 'dk', 'finland': 'fi',
        'ireland': 'ie', 'greece': 'gr', 'czech republic': 'cz', 'hungary': 'hu',
        'romania': 'ro', 'bulgaria': 'bg', 'croatia': 'hr', 'slovakia': 'sk',
        'slovenia': 'si', 'estonia': 'ee', 'latvia': 'lv', 'lithuania': 'lt',
        'united states': 'us', 'usa': 'us', 'canada': 'ca', 'mexico': 'mx',
        'brazil': 'br', 'argentina': 'ar', 'colombia': 'co', 'chile': 'cl',
        'peru': 'pe', 'venezuela': 've', 'australia': 'au', 'new zealand': 'nz',
        'japan': 'jp', 'china': 'cn', 'india': 'in', 'south korea': 'kr',
        'russia': 'ru', 'turkey': 'tr', 'egypt': 'eg', 'south africa': 'za',
        'nigeria': 'ng', 'kenya': 'ke', 'morocco': 'ma', 'israel': 'il',
        'saudi arabia': 'sa', 'uae': 'ae', 'singapore': 'sg', 'malaysia': 'my',
        'thailand': 'th', 'indonesia': 'id', 'philippines': 'ph', 'vietnam': 'vn'
    }
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = api_key or os.environ.get('MEDIASTACK_API_KEY')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SecurityIntelligenceApp/1.0'
        })
    
    def is_configured(self) -> bool:
        """Check if MediaStack API key is configured."""
        return bool(self.api_key)
    
    def _get_country_code(self, country: str) -> Optional[str]:
        """Convert country name to ISO 2-letter code."""
        if not country:
            return None
        country_lower = country.lower().strip()
        return self.COUNTRY_CODES.get(country_lower)
    
    def _parse_response(self, data: Dict) -> List[Dict]:
        """Parse MediaStack API response into standardized article format."""
        articles = []
        
        if not data or 'data' not in data:
            return articles
        
        for article in data.get('data', []):
            try:
                published_at = article.get('published_at', '')
                if published_at:
                    try:
                        dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d')
                    except Exception:
                        date_str = published_at[:10] if len(published_at) >= 10 else ''
                else:
                    date_str = ''
                
                parsed = {
                    'title': (article.get('title') or '').strip(),
                    'description': (article.get('description') or '').strip(),
                    'url': article.get('url', ''),
                    'date': date_str,
                    'source': article.get('source', ''),
                    'category': article.get('category', ''),
                    'language': article.get('language', 'en'),
                    'country': article.get('country', ''),
                    'author': article.get('author', ''),
                    'image': article.get('image', '')
                }
                
                if parsed['title'] and parsed['url']:
                    articles.append(parsed)
            except Exception as e:
                logger.debug(f"Error parsing MediaStack article: {e}")
                continue
        
        return articles
    
    def _filter_by_city(self, articles: List[Dict], city: str) -> List[Dict]:
        """Filter articles that mention the city."""
        if not city:
            return articles
        
        city_lower = city.lower()
        filtered = []
        
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}".lower()
            if city_lower in text:
                filtered.append(article)
        
        return filtered
    
    def fetch_news(self, keywords: List[str], country: Optional[str] = None,
                   city: Optional[str] = None, limit: int = 50, 
                   languages: str = 'en') -> Dict:
        """
        Fetch news articles from MediaStack.
        
        Args:
            keywords: List of keywords to search for
            country: Country name (added to keyword search for free tier)
            city: City name (added to keyword search for better targeting)
            limit: Maximum number of articles (max 100 for free tier)
            languages: Language codes (comma-separated)
            
        Returns:
            Dict with 'articles', 'success', 'error' fields
        """
        if not self.is_configured():
            return {
                'articles': [],
                'success': False,
                'error': 'MediaStack API key not configured'
            }
        
        try:
            location = city if city else country
            if not location:
                return {
                    'articles': [],
                    'success': False,
                    'error': 'City or country required for MediaStack search'
                }
            
            keyword_phrase = f"{location} {keywords[0]}" if keywords else location
            
            params = {
                'access_key': self.api_key,
                'keywords': keyword_phrase,
                'languages': languages,
                'limit': min(limit, 100),
                'sort': 'published_desc'
            }
            
            response = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
            
            if response.status_code == 401:
                return {
                    'articles': [],
                    'success': False,
                    'error': 'MediaStack API key is invalid'
                }
            
            if response.status_code == 422:
                return {
                    'articles': [],
                    'success': False,
                    'error': 'MediaStack request limit exceeded or invalid parameters'
                }
            
            if response.status_code != 200:
                return {
                    'articles': [],
                    'success': False,
                    'error': f'MediaStack API returned status {response.status_code}'
                }
            
            data = response.json()
            
            if 'error' in data:
                error_info = data['error']
                error_msg = error_info.get('message', 'Unknown error') if isinstance(error_info, dict) else str(error_info)
                return {
                    'articles': [],
                    'success': False,
                    'error': f'MediaStack error: {error_msg}'
                }
            
            articles = self._parse_response(data)
            
            return {
                'articles': articles,
                'success': True,
                'error': None,
                'pagination': data.get('pagination', {})
            }
            
        except requests.exceptions.Timeout:
            return {
                'articles': [],
                'success': False,
                'error': 'MediaStack request timed out'
            }
        except requests.exceptions.RequestException as e:
            return {
                'articles': [],
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            return {
                'articles': [],
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def get_incident_articles(self, city: str, country: str, limit: int = 25) -> Dict:
        """
        Fetch articles related to violent incidents.
        
        Args:
            city: City name for filtering
            country: Country name
            limit: Max articles to fetch
            
        Returns:
            Dict with articles, success status
        """
        result = self.fetch_news(
            keywords=self.INCIDENT_KEYWORDS[:3],
            country=country,
            city=city,
            limit=limit
        )
        
        return result
    
    def get_demonstration_articles(self, city: str, country: str, limit: int = 25) -> Dict:
        """
        Fetch articles related to protests/demonstrations.
        
        Args:
            city: City name for filtering
            country: Country name
            limit: Max articles to fetch
            
        Returns:
            Dict with articles, success status
        """
        result = self.fetch_news(
            keywords=self.DEMONSTRATION_KEYWORDS[:3],
            country=country,
            city=city,
            limit=limit
        )
        
        return result
    
    def get_security_articles(self, city: str, country: str, limit: int = 50) -> Dict:
        """
        Fetch all security-related articles.
        
        Args:
            city: City name for filtering
            country: Country name
            limit: Max articles to fetch
            
        Returns:
            Dict with articles, success status
        """
        result = self.fetch_news(
            keywords=self.SECURITY_KEYWORDS[:3],
            country=country,
            city=city,
            limit=limit
        )
        
        if result['success'] and city:
            result['articles'] = self._filter_by_city(result['articles'], city)
        
        return result


def is_mediastack_available() -> bool:
    """Check if MediaStack API key is configured."""
    return bool(os.environ.get('MEDIASTACK_API_KEY'))
