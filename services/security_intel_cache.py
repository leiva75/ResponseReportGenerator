"""
Security Intelligence Cache - SQLite-based caching with TTL

Provides local caching for security intelligence data with:
- 6-hour TTL (configurable)
- Offline mode support
- Windows-compatible paths
- Automatic cleanup of expired entries

No external dependencies beyond Python standard library.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from pathlib import Path

from services.paths import get_security_intel_cache_db, get_cache_dir


class SecurityIntelCache:
    """
    SQLite-based cache for security intelligence data.
    
    Usage:
        cache = SecurityIntelCache()
        cache.set('key', {'data': 'value'})
        result = cache.get('key')  # Returns None if expired
    """
    
    DEFAULT_TTL_HOURS = 12
    
    def __init__(self, db_path: str = None, ttl_hours: int = None):
        """
        Initialize the cache.
        
        Args:
            db_path: Path to SQLite database. Defaults to data/security_intel_cache.db
            ttl_hours: Time-to-live in hours. Defaults to 6 hours.
        """
        if db_path is None:
            cache_dir = get_cache_dir()
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(get_security_intel_cache_db())
        
        self.db_path = db_path
        self.ttl_hours = ttl_hours or self.DEFAULT_TTL_HOURS
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS intel_cache (
                    key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_expires_at 
                ON intel_cache(expires_at)
            ''')
            conn.commit()
        finally:
            conn.close()
    
    def get(self, key: str) -> Optional[Dict]:
        """
        Get cached data if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data dict or None if not found/expired
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT payload_json, fetched_at, expires_at 
                FROM intel_cache 
                WHERE key = ?
            ''', (key,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            expires_at = datetime.fromisoformat(row['expires_at'])
            if datetime.now() > expires_at:
                self._delete(key)
                return None
            
            data = json.loads(row['payload_json'])
            data['_cache_info'] = {
                'fetched_at': row['fetched_at'],
                'expires_at': row['expires_at'],
                'from_cache': True
            }
            
            return data
            
        except Exception:
            return None
        finally:
            conn.close()
    
    def set(self, key: str, data: Dict, ttl_hours: int = None) -> bool:
        """
        Store data in cache.
        
        Args:
            key: Cache key
            data: Data to cache (must be JSON serializable)
            ttl_hours: Override default TTL
            
        Returns:
            True if successful, False otherwise
        """
        ttl = ttl_hours or self.ttl_hours
        now = datetime.now()
        expires_at = now + timedelta(hours=ttl)
        
        data_copy = dict(data)
        data_copy.pop('_cache_info', None)
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO intel_cache 
                (key, payload_json, fetched_at, expires_at)
                VALUES (?, ?, ?, ?)
            ''', (
                key,
                json.dumps(data_copy),
                now.isoformat(),
                expires_at.isoformat()
            ))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()
    
    def _delete(self, key: str) -> bool:
        """Delete a cache entry."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM intel_cache WHERE key = ?', (key,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()
    
    def clear_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM intel_cache 
                WHERE expires_at < ?
            ''', (datetime.now().isoformat(),))
            count = cursor.rowcount
            conn.commit()
            return count
        finally:
            conn.close()
    
    def clear_all(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries removed
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM intel_cache')
            count = cursor.rowcount
            conn.commit()
            return count
        finally:
            conn.close()
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dict with total entries, expired entries, cache size
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as total FROM intel_cache')
            total = cursor.fetchone()['total']
            
            cursor.execute('''
                SELECT COUNT(*) as expired 
                FROM intel_cache 
                WHERE expires_at < ?
            ''', (datetime.now().isoformat(),))
            expired = cursor.fetchone()['expired']
            
            try:
                file_size = os.path.getsize(self.db_path)
            except OSError:
                file_size = 0
            
            return {
                'total_entries': total,
                'expired_entries': expired,
                'valid_entries': total - expired,
                'cache_size_bytes': file_size,
                'ttl_hours': self.ttl_hours
            }
        finally:
            conn.close()
    
    def list_keys(self) -> list:
        """List all cache keys."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT key FROM intel_cache')
            return [row['key'] for row in cursor.fetchall()]
        finally:
            conn.close()


def get_cache_instance(ttl_hours: int = None) -> SecurityIntelCache:
    """Get a cache instance (convenience function)."""
    return SecurityIntelCache(ttl_hours=ttl_hours)
