"""
RSS Provider - Free RSS feed aggregation for news intelligence

This provider aggregates news from configurable RSS feeds organized by country/language.
Easily extensible by adding feeds to the RSS_FEEDS configuration.

No API key required. Completely free.
Requires: feedparser (pip install feedparser)
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from email.utils import parsedate_to_datetime

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False


class RSSProvider:
    """
    RSS Feed Provider for news aggregation.
    
    Extensible configuration: Add/remove feeds in RSS_FEEDS dict.
    """
    
    RSS_FEEDS = {
        'FR': {
            'general': [
                {'name': 'Le Monde', 'url': 'https://www.lemonde.fr/rss/une.xml'},
                {'name': 'France Info', 'url': 'https://www.francetvinfo.fr/titres.rss'},
                {'name': 'Le Figaro', 'url': 'https://www.lefigaro.fr/rss/figaro_actualites.xml'},
                {'name': '20 Minutes', 'url': 'https://www.20minutes.fr/rss/actu.xml'},
            ],
            'faits_divers': [
                {'name': 'France Info Faits Divers', 'url': 'https://www.francetvinfo.fr/faits-divers.rss'},
                {'name': 'Le Parisien', 'url': 'https://www.leparisien.fr/arc/outboundfeeds/rss/faitsdivers.xml'},
            ]
        },
        'DE': {
            'general': [
                {'name': 'Spiegel', 'url': 'https://www.spiegel.de/schlagzeilen/tops/index.rss'},
                {'name': 'Zeit', 'url': 'https://newsfeed.zeit.de/index'},
                {'name': 'Tagesschau', 'url': 'https://www.tagesschau.de/xml/rss2'},
            ]
        },
        'UK': {
            'general': [
                {'name': 'BBC News', 'url': 'http://feeds.bbci.co.uk/news/rss.xml'},
                {'name': 'The Guardian', 'url': 'https://www.theguardian.com/uk/rss'},
                {'name': 'Sky News', 'url': 'https://feeds.skynews.com/feeds/rss/uk.xml'},
            ]
        },
        'ES': {
            'general': [
                {'name': 'El País', 'url': 'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada'},
                {'name': 'El Mundo', 'url': 'https://e00-elmundo.uecdn.es/elmundo/rss/espana.xml'},
            ]
        },
        'NL': {
            'general': [
                {'name': 'NOS', 'url': 'https://feeds.nos.nl/nosnieuwsalgemeen'},
                {'name': 'RTL Nieuws', 'url': 'https://www.rtlnieuws.nl/rss.xml'},
            ]
        },
        'BE': {
            'general': [
                {'name': 'RTBF', 'url': 'https://rss.rtbf.be/article/rss/rtbfinfo_homepage.xml'},
                {'name': 'Le Soir', 'url': 'https://www.lesoir.be/rss/cible_principale.xml'},
            ]
        },
        'IT': {
            'general': [
                {'name': 'La Repubblica', 'url': 'https://www.repubblica.it/rss/homepage/rss2.0.xml'},
                {'name': 'Corriere della Sera', 'url': 'https://xml2.corriereobjects.it/rss/homepage.xml'},
            ]
        },
        'DEFAULT': {
            'general': [
                {'name': 'Reuters', 'url': 'https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best'},
                {'name': 'AP News', 'url': 'https://rsshub.app/apnews/topics/apf-topnews'},
            ]
        }
    }
    
    SECURITY_KEYWORDS = {
        'homicide': ['homicide', 'murder', 'killed', 'stabbing', 'shooting', 'meurtre', 'tué', 
                     'mord', 'getötet', 'asesinato', 'omicidio'],
        'demonstration': ['protest', 'demonstration', 'manifestation', 'rassemblement', 'grève',
                         'strike', 'rally', 'march', 'streik', 'huelga', 'protesta'],
        'crime': ['crime', 'robbery', 'assault', 'theft', 'vol', 'agression', 'cambriolage',
                 'raub', 'überfall', 'robo', 'asalto', 'rapina']
    }
    
    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        if not FEEDPARSER_AVAILABLE:
            raise ImportError("feedparser is required. Install with: pip install feedparser")
    
    def _get_feeds_for_country(self, country: str) -> List[Dict]:
        """Get all RSS feeds for a country code."""
        country_upper = country.upper()
        
        country_map = {
            'FRANCE': 'FR', 'GERMANY': 'DE', 'DEUTSCHLAND': 'DE',
            'UNITED KINGDOM': 'UK', 'ENGLAND': 'UK', 'GREAT BRITAIN': 'UK', 'GB': 'UK',
            'SPAIN': 'ES', 'ESPAÑA': 'ES', 'ESPAGNE': 'ES',
            'NETHERLANDS': 'NL', 'PAYS-BAS': 'NL', 'NEDERLAND': 'NL',
            'BELGIUM': 'BE', 'BELGIQUE': 'BE', 'BELGIË': 'BE',
            'ITALY': 'IT', 'ITALIA': 'IT', 'ITALIE': 'IT',
        }
        
        country_code = country_map.get(country_upper, country_upper)
        
        feeds = []
        country_feeds = self.RSS_FEEDS.get(country_code, self.RSS_FEEDS.get('DEFAULT', {}))
        
        for category_feeds in country_feeds.values():
            feeds.extend(category_feeds)
        
        if not feeds:
            for category_feeds in self.RSS_FEEDS.get('DEFAULT', {}).values():
                feeds.extend(category_feeds)
        
        return feeds
    
    def _parse_date(self, entry: Dict) -> Optional[datetime]:
        """Parse date from RSS entry."""
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in date_fields:
            if entry.get(field):
                try:
                    return datetime(*entry[field][:6])
                except Exception:
                    continue
        
        for field in ['published', 'updated', 'created']:
            if entry.get(field):
                try:
                    return parsedate_to_datetime(entry[field])
                except Exception:
                    continue
        
        return None
    
    def _matches_location(self, text: str, city: str, country: str) -> bool:
        """Check if text mentions the location."""
        text_lower = text.lower()
        
        if city and city.lower() in text_lower:
            return True
        
        return False
    
    def _matches_keywords(self, text: str, category: str) -> bool:
        """Check if text matches keywords for a category."""
        text_lower = text.lower()
        keywords = self.SECURITY_KEYWORDS.get(category, [])
        
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    def _parse_feed(self, feed_info: Dict) -> List[Dict]:
        """Parse a single RSS feed."""
        try:
            feed = feedparser.parse(feed_info['url'])
            
            if feed.bozo and not feed.entries:
                return []
            
            articles = []
            for entry in feed.entries[:50]:
                title = entry.get('title', '').strip()
                link = entry.get('link', '')
                
                summary = entry.get('summary', entry.get('description', ''))
                if hasattr(summary, 'value'):
                    summary = summary.value
                summary = re.sub(r'<[^>]+>', '', str(summary))[:300]
                
                pub_date = self._parse_date(entry)
                date_str = pub_date.strftime('%Y-%m-%d') if pub_date else ''
                
                if title and link:
                    articles.append({
                        'title': title,
                        'url': link,
                        'date': date_str,
                        'source': feed_info['name'],
                        'snippet': summary,
                        'pub_datetime': pub_date
                    })
            
            return articles
            
        except Exception:
            return []
    
    def fetch_articles(self, city: str, country: str, category: str = 'all',
                       days: int = 30, max_articles: int = 50) -> Dict:
        """
        Fetch articles from RSS feeds matching location and category.
        
        Args:
            city: City name to filter
            country: Country for feed selection
            category: 'homicide', 'demonstration', 'crime', or 'all'
            days: Number of days to look back
            max_articles: Maximum number of articles to return
            
        Returns:
            Dict with 'articles', 'success', 'error' fields
        """
        try:
            feeds = self._get_feeds_for_country(country)
            
            if not feeds:
                return {
                    'articles': [],
                    'success': False,
                    'error': f'No RSS feeds configured for {country}'
                }
            
            cutoff_date = datetime.now() - timedelta(days=days)
            all_articles = []
            
            for feed_info in feeds:
                articles = self._parse_feed(feed_info)
                all_articles.extend(articles)
            
            filtered = []
            for article in all_articles:
                if article.get('pub_datetime') and article['pub_datetime'] < cutoff_date:
                    continue
                
                text = f"{article.get('title', '')} {article.get('snippet', '')}"
                
                if city and not self._matches_location(text, city, country):
                    continue
                
                if category != 'all' and not self._matches_keywords(text, category):
                    continue
                
                for a in article.copy():
                    if a == 'pub_datetime':
                        del article['pub_datetime']
                
                filtered.append(article)
            
            filtered.sort(key=lambda x: x.get('date', ''), reverse=True)
            filtered = filtered[:max_articles]
            
            return {
                'articles': filtered,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            return {
                'articles': [],
                'success': False,
                'error': f'RSS fetch error: {str(e)}'
            }
    
    def get_homicide_articles(self, city: str, country: str, days: int = 30) -> Dict:
        """Fetch articles related to homicides/violent crimes."""
        return self.fetch_articles(city, country, 'homicide', days)
    
    def get_demonstration_articles(self, city: str, country: str, days: int = 14) -> Dict:
        """Fetch articles related to demonstrations/protests."""
        return self.fetch_articles(city, country, 'demonstration', days)
    
    def get_crime_articles(self, city: str, country: str, days: int = 30) -> Dict:
        """Fetch articles related to general crime."""
        return self.fetch_articles(city, country, 'crime', days)
    
    @classmethod
    def add_feed(cls, country: str, category: str, name: str, url: str):
        """
        Add a new RSS feed to the configuration.
        
        Usage:
            RSSProvider.add_feed('FR', 'general', 'New Source', 'https://...')
        """
        country = country.upper()
        if country not in cls.RSS_FEEDS:
            cls.RSS_FEEDS[country] = {}
        if category not in cls.RSS_FEEDS[country]:
            cls.RSS_FEEDS[country][category] = []
        
        cls.RSS_FEEDS[country][category].append({'name': name, 'url': url})
