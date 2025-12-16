import re
from .config import (
    INCIDENT_KEYWORDS_ES, INCIDENT_KEYWORDS_EN,
    GATHERING_KEYWORDS_ES, GATHERING_KEYWORDS_EN,
    FUTURE_KEYWORDS, STRONG_VIOLENCE_KEYWORDS
)

def _text_matches(text: str, keywords: list) -> list:
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]

def classify_articles(articles: list) -> dict:
    incidents = []
    gatherings = []
    
    all_incident_kw = INCIDENT_KEYWORDS_ES + INCIDENT_KEYWORDS_EN
    all_gathering_kw = GATHERING_KEYWORDS_ES + GATHERING_KEYWORDS_EN
    
    for art in articles:
        title = art.get("title", "") or ""
        description = art.get("description", "") or ""
        full_text = f"{title} {description}"
        
        incident_signals = _text_matches(full_text, all_incident_kw)
        gathering_signals = _text_matches(full_text, all_gathering_kw)
        future_signals = _text_matches(full_text, FUTURE_KEYWORDS)
        strong_signals = _text_matches(full_text, STRONG_VIOLENCE_KEYWORDS)
        
        entry = {
            "title": title[:200],
            "source": art.get("source", "unknown"),
            "published_at": art.get("published_at", ""),
            "url": art.get("url", ""),
            "signals": [],
            "is_strong": len(strong_signals) > 0
        }
        
        if gathering_signals:
            entry["signals"] = gathering_signals[:3]
            if future_signals:
                entry["signals"].append("planned")
            gatherings.append(entry)
        elif incident_signals:
            entry["signals"] = incident_signals[:3]
            if strong_signals:
                entry["signals"].append("violence")
            incidents.append(entry)
    
    incidents = sorted(incidents, key=lambda x: x.get("published_at", ""), reverse=True)[:6]
    gatherings = sorted(gatherings, key=lambda x: x.get("published_at", ""), reverse=True)[:6]
    
    return {
        "incidents": incidents,
        "gatherings": gatherings,
        "stats": {
            "total_articles": len(articles),
            "incident_count": len([a for a in articles if _text_matches(f"{a.get('title','')} {a.get('description','')}", all_incident_kw)]),
            "gathering_count": len([a for a in articles if _text_matches(f"{a.get('title','')} {a.get('description','')}", all_gathering_kw)]),
            "strong_count": len([a for a in articles if _text_matches(f"{a.get('title','')} {a.get('description','')}", STRONG_VIOLENCE_KEYWORDS)]),
            "sources": list(set(a.get("source", "") for a in articles if a.get("source")))
        }
    }
