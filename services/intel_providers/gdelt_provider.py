"""
GDELT Provider - Free global news/events data from GDELT 2.1 API

GDELT (Global Database of Events, Language, and Tone) provides free access
to global news articles. This provider queries GDELT for security-relevant
articles based on city and country.

No API key required. Completely free.
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import urllib.parse


class GDELTProvider:
    """
    GDELT 2.1 API Provider for free news/events data.
    
    Endpoints used:
    - DOC 2.0 API: https://api.gdeltproject.org/api/v2/doc/doc
    """
    
    BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
    
    HOMICIDE_KEYWORDS = {
        'en': ['homicide', 'murder', 'killed', 'stabbing', 'shooting', 'fatal', 'death', 'shot dead', 'stabbed'],
        'fr': ['homicide', 'meurtre', 'tué', 'tuée', 'mort', 'fusillade', 'coup de couteau', 'poignardé', 'assassinat'],
        'de': ['mord', 'getötet', 'erschossen', 'erstochen', 'tödlich', 'schießerei', 'messerstecherei'],
        'es': ['homicidio', 'asesinato', 'matado', 'apuñalado', 'tiroteo', 'baleado', 'muerto']
    }
    
    DEMONSTRATION_KEYWORDS = {
        'en': ['protest', 'demonstration', 'rally', 'march', 'strike', 'riot', 'unrest', 'blockade'],
        'fr': ['manifestation', 'rassemblement', 'grève', 'marche', 'blocage', 'émeute', 'protestation'],
        'de': ['demonstration', 'protest', 'streik', 'kundgebung', 'blockade', 'unruhen'],
        'es': ['manifestación', 'protesta', 'huelga', 'marcha', 'bloqueo', 'disturbios']
    }
    
    CRIME_KEYWORDS = {
        'en': ['crime', 'robbery', 'assault', 'theft', 'burglary', 'violence', 'attack', 'incident'],
        'fr': ['crime', 'vol', 'agression', 'cambriolage', 'violence', 'attaque', 'incident', 'délinquance'],
        'de': ['verbrechen', 'raub', 'überfall', 'diebstahl', 'gewalt', 'angriff'],
        'es': ['crimen', 'robo', 'asalto', 'hurto', 'violencia', 'ataque']
    }
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SecurityIntelligenceApp/1.0'
        })
    
    def _build_query(self, city: str, country: str, keywords: List[str], 
                     days: int = 30, city_aliases: Optional[List[str]] = None) -> str:
        """
        Build GDELT query string with optional city aliases.
        
        Args:
            city: Primary city name
            country: Country name
            keywords: Search keywords
            days: Days to look back
            city_aliases: Optional list of alternative city names (e.g., ["CDMX", "Ciudad de México"])
        
        Returns:
            GDELT query string like:
            "Mexico" AND ("Mexico City" OR "CDMX") AND (keywords)
        """
        location_terms = []
        
        if country:
            location_terms.append(f'"{country}"')
        
        city_terms = []
        if city:
            city_terms.append(f'"{city}"')
            if city_aliases:
                for alias in city_aliases:
                    if alias and alias.lower() != city.lower():
                        city_terms.append(f'"{alias}"')
        
        if city_terms:
            city_query = "(" + " OR ".join(city_terms) + ")"
            location_terms.append(city_query)
        
        location_query = " AND ".join(location_terms) if location_terms else ""
        
        keyword_query = "(" + " OR ".join([f'"{kw}"' for kw in keywords]) + ")"
        
        if location_query and keyword_query:
            return f"{location_query} AND {keyword_query}"
        elif location_query:
            return location_query
        else:
            return keyword_query
    
    def _get_all_keywords(self, keyword_dict: Dict[str, List[str]]) -> List[str]:
        """Flatten all language keywords into a single list."""
        all_keywords = []
        for lang_keywords in keyword_dict.values():
            all_keywords.extend(lang_keywords)
        return list(set(all_keywords))
    
    def _parse_gdelt_response(self, data: Dict) -> List[Dict]:
        """Parse GDELT API response into standardized article format."""
        articles = []
        
        if not data or 'articles' not in data:
            return articles
        
        for article in data.get('articles', []):
            try:
                parsed = {
                    'title': article.get('title', '').strip(),
                    'url': article.get('url', ''),
                    'date': article.get('seendate', '')[:10] if article.get('seendate') else '',
                    'source': article.get('domain', ''),
                    'snippet': article.get('title', '')[:200],
                    'language': article.get('language', 'en')
                }
                if parsed['title'] and parsed['url']:
                    articles.append(parsed)
            except Exception:
                continue
        
        return articles
    
    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on URL and similar titles."""
        seen_urls = set()
        seen_titles = set()
        unique = []
        
        for article in articles:
            url = article.get('url', '')
            title = article.get('title', '').lower()[:50]
            
            if url in seen_urls or title in seen_titles:
                continue
            
            seen_urls.add(url)
            seen_titles.add(title)
            unique.append(article)
        
        return unique
    
    def fetch_articles(self, city: str, country: str, keywords: List[str], 
                       days: int = 30, max_records: int = 50,
                       city_aliases: Optional[List[str]] = None) -> Dict:
        """
        Fetch articles from GDELT matching location and keywords.
        
        Args:
            city: City name
            country: Country name
            keywords: List of keywords to search for
            days: Number of days to look back
            max_records: Maximum number of records to fetch
            city_aliases: Optional list of alternative city names for better matching
            
        Returns:
            Dict with 'articles', 'success', 'error' fields
        """
        try:
            query = self._build_query(city, country, keywords, days, city_aliases)
            
            if days <= 1:
                timespan = '24h'
            elif days <= 3:
                timespan = '3d'
            elif days <= 7:
                timespan = '7d'
            elif days <= 30:
                timespan = '1m'
            elif days <= 90:
                timespan = '3m'
            else:
                timespan = '1y'
            
            params = {
                'query': query,
                'mode': 'artlist',
                'maxrecords': str(max_records),
                'format': 'json',
                'timespan': timespan,
                'sort': 'DateDesc'
            }
            
            response = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
            
            if response.status_code != 200:
                return {
                    'articles': [],
                    'success': False,
                    'error': f'GDELT API returned status {response.status_code}'
                }
            
            response_text = response.text.strip()
            if not response_text or response_text == '':
                return {
                    'articles': [],
                    'success': True,
                    'error': None
                }
            
            try:
                data = response.json()
            except ValueError:
                return {
                    'articles': [],
                    'success': True,
                    'error': None
                }
            
            articles = self._parse_gdelt_response(data)
            articles = self._deduplicate_articles(articles)
            
            return {
                'articles': articles,
                'success': True,
                'error': None
            }
            
        except requests.exceptions.Timeout:
            return {
                'articles': [],
                'success': False,
                'error': 'GDELT request timed out'
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
    
    def get_homicide_articles(self, city: str, country: str, days: int = 30,
                              city_aliases: Optional[List[str]] = None) -> Dict:
        """Fetch articles related to homicides/violent crimes."""
        keywords = self._get_all_keywords(self.HOMICIDE_KEYWORDS)
        return self.fetch_articles(city, country, keywords, days, city_aliases=city_aliases)
    
    def get_demonstration_articles(self, city: str, country: str, days: int = 14,
                                   city_aliases: Optional[List[str]] = None) -> Dict:
        """Fetch articles related to demonstrations/protests."""
        keywords = self._get_all_keywords(self.DEMONSTRATION_KEYWORDS)
        return self.fetch_articles(city, country, keywords, days, city_aliases=city_aliases)
    
    def get_crime_articles(self, city: str, country: str, days: int = 30,
                          city_aliases: Optional[List[str]] = None) -> Dict:
        """Fetch articles related to general crime/security incidents."""
        keywords = self._get_all_keywords(self.CRIME_KEYWORDS)
        return self.fetch_articles(city, country, keywords, days, city_aliases=city_aliases)
    
    def get_all_security_articles(self, city: str, country: str, 
                                   homicide_days: int = 30,
                                   demo_days: int = 14) -> Dict:
        """
        Fetch all security-relevant articles in one call.
        
        Returns categorized results for homicides, demonstrations, and general crime.
        """
        homicides = self.get_homicide_articles(city, country, homicide_days)
        demonstrations = self.get_demonstration_articles(city, country, demo_days)
        crime = self.get_crime_articles(city, country, homicide_days)
        
        return {
            'homicides': homicides,
            'demonstrations': demonstrations,
            'crime': crime,
            'fetched_at': datetime.now().isoformat()
        }
