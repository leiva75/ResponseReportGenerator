"""
Caching service for City Security Brief
Uses SQLite for persistent caching with TTL support.
"""
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from services.paths import get_security_brief_cache_db, get_cache_dir

logger = logging.getLogger(__name__)

CACHE_DB_PATH = str(get_security_brief_cache_db())
DEFAULT_TTL_HOURS = 6


class SecurityCache:
    """SQLite-based cache for security brief data."""
    
    def __init__(self, db_path: str = CACHE_DB_PATH, ttl_hours: int = DEFAULT_TTL_HOURS):
        self.db_path = db_path
        self.ttl_hours = ttl_hours
        self._init_db()
    
    def _init_db(self):
        """Initialize the cache database."""
        get_cache_dir().mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_cache (
                cache_key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_expires_at ON security_cache(expires_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def _generate_key(self, city: str, country: str, address: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """Generate a unique cache key."""
        key_parts = [
            city.lower().strip(),
            country.lower().strip(),
            (address or "").lower().strip(),
            (start_date or "").strip(),
            (end_date or "").strip()
        ]
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, city: str, country: str, address: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached data if available and not expired."""
        cache_key = self._generate_key(city, country, address, start_date, end_date)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT data, expires_at FROM security_cache
                WHERE cache_key = ? AND expires_at > ?
            ''', (cache_key, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                logger.info(f"Cache hit for {city}, {country}")
                return json.loads(row[0])
            
            logger.info(f"Cache miss for {city}, {country}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, city: str, country: str, data: Dict[str, Any], address: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
        """Store data in cache."""
        cache_key = self._generate_key(city, country, address, start_date, end_date)
        expires_at = datetime.now() + timedelta(hours=self.ttl_hours)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO security_cache (cache_key, data, created_at, expires_at)
                VALUES (?, ?, ?, ?)
            ''', (cache_key, json.dumps(data), datetime.now().isoformat(), expires_at.isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cached data for {city}, {country}")
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def clear_expired(self):
        """Remove expired cache entries."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM security_cache WHERE expires_at < ?
            ''', (datetime.now().isoformat(),))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted > 0:
                logger.info(f"Cleared {deleted} expired cache entries")
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    def invalidate(self, city: str, country: str, address: Optional[str] = None):
        """Invalidate a specific cache entry."""
        cache_key = self._generate_key(city, country, address)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM security_cache WHERE cache_key = ?', (cache_key,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")


_cache_instance = None

def get_cache() -> SecurityCache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SecurityCache()
    return _cache_instance
