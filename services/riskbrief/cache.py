import sqlite3
import json
import hashlib
from datetime import datetime, timezone
from .config import CACHE_DB
from services.paths import get_cache_dir


def _ensure_dir():
    get_cache_dir().mkdir(parents=True, exist_ok=True)


def _conn():
    _ensure_dir()
    return sqlite3.connect(CACHE_DB)


def init_cache():
    with _conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS events_cache(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            country TEXT,
            event_hash TEXT UNIQUE,
            title TEXT,
            datetime TEXT,
            category TEXT,
            location TEXT,
            lat REAL,
            lon REAL,
            source TEXT,
            url TEXT,
            confidence REAL,
            raw_json TEXT,
            created_at TEXT
        )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_city_country ON events_cache(city, country)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_dt ON events_cache(datetime)")
        c.commit()


def make_hash(title: str, dt: str, source: str, url: str = "") -> str:
    base = f"{title}|{dt}|{source}|{url}".lower().strip()
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def upsert_event(city: str, country: str, e: dict):
    h = e.get("event_hash")
    if not h:
        h = make_hash(e.get("title", ""), e.get("datetime", ""), e.get("source", ""), e.get("url", ""))
        e["event_hash"] = h

    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        c.execute("""
        INSERT OR IGNORE INTO events_cache(
            city,country,event_hash,title,datetime,category,location,lat,lon,source,url,confidence,raw_json,created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            city, country, h,
            e.get("title", ""),
            e.get("datetime", ""),
            e.get("category", "UNKNOWN"),
            e.get("location", "unknown"),
            e.get("lat"), e.get("lon"),
            e.get("source", "-"),
            e.get("url", ""),
            float(e.get("confidence", 0.0)),
            json.dumps(e.get("raw", {}), ensure_ascii=False),
            now
        ))
        c.commit()


def load_cached(city: str, country: str, since_iso: str):
    init_cache()
    with _conn() as c:
        cur = c.execute("""
        SELECT title, datetime, category, location, lat, lon, source, url, confidence
        FROM events_cache
        WHERE city=? AND country=? AND datetime>=?
        ORDER BY datetime DESC
        """, (city, country, since_iso))
        rows = cur.fetchall()

    events = []
    for (title, dt, cat, loc, lat, lon, src, url, conf) in rows:
        events.append({
            "title": title, "datetime": dt, "category": cat, "location": loc,
            "lat": lat, "lon": lon, "source": src, "url": url, "confidence": conf
        })
    return events
