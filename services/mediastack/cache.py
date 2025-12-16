import sqlite3
import json
from datetime import datetime, timedelta, timezone
from .config import CACHE_DB_PATH, CACHE_TTL_HOURS
from services.paths import get_cache_dir

def _ensure_db():
    get_cache_dir().mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mediastack_cache (
            cache_key TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def _make_key(city: str, country: str, window_days: int) -> str:
    return f"{city.lower()}:{country.lower()}:{window_days}"

def cache_get(city: str, country: str, window_days: int) -> dict | None:
    _ensure_db()
    key = _make_key(city, country, window_days)
    conn = sqlite3.connect(CACHE_DB_PATH)
    cur = conn.execute(
        "SELECT data, created_at FROM mediastack_cache WHERE cache_key = ?",
        (key,)
    )
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return None
    
    data_str, created_str = row
    created_at = datetime.fromisoformat(created_str)
    now = datetime.now(timezone.utc)
    
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    
    if now - created_at > timedelta(hours=CACHE_TTL_HOURS):
        return None
    
    return json.loads(data_str)

def cache_set(city: str, country: str, window_days: int, data: dict):
    _ensure_db()
    key = _make_key(city, country, window_days)
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.execute("""
        INSERT OR REPLACE INTO mediastack_cache (cache_key, data, created_at)
        VALUES (?, ?, ?)
    """, (key, json.dumps(data), now))
    conn.commit()
    conn.close()

def cache_get_stale(city: str, country: str, window_days: int) -> dict | None:
    _ensure_db()
    key = _make_key(city, country, window_days)
    conn = sqlite3.connect(CACHE_DB_PATH)
    cur = conn.execute(
        "SELECT data FROM mediastack_cache WHERE cache_key = ?",
        (key,)
    )
    row = cur.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    return None
