"""
Scoring service for City Security Brief
Implements relevance filtering and scoring based on recency, proximity, severity, and source confidence.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from math import radians, sin, cos, sqrt, atan2
import logging

logger = logging.getLogger(__name__)


class SecurityScorer:
    """Scores and ranks security data items."""
    
    SEVERITY_WEIGHTS = {
        "critical": 1.0,
        "high": 0.8,
        "medium": 0.5,
        "low": 0.2
    }
    
    SOURCE_CONFIDENCE_WEIGHTS = {
        "official": 1.0,
        "government": 0.95,
        "aggregator": 0.7,
        "media": 0.6,
        "user_report": 0.3
    }
    
    CATEGORY_SEVERITY_BOOST = {
        "terrorism": 0.3,
        "riot": 0.25,
        "violence": 0.2,
        "assault": 0.2,
        "robbery": 0.15,
        "protest": 0.1,
        "demonstration": 0.05,
        "strike": 0.1,
        "disruption": 0.1,
        "unrest": 0.15
    }
    
    def __init__(self, max_items: int = 10):
        self.max_items = max_items
    
    def _calculate_recency_score(self, timestamp: datetime) -> float:
        """Calculate recency weight (last 7 days highest)."""
        if not timestamp:
            return 0.3
        
        now = datetime.now()
        if timestamp.tzinfo:
            from datetime import timezone
            now = datetime.now(timezone.utc)
        
        age = now - timestamp
        days = age.days + (age.seconds / 86400)
        
        if days < 1:
            return 1.0
        elif days < 3:
            return 0.9
        elif days < 7:
            return 0.7
        elif days < 14:
            return 0.5
        elif days < 30:
            return 0.3
        else:
            return 0.1
    
    def _calculate_proximity_score(
        self, 
        item_lat: Optional[float], 
        item_lon: Optional[float],
        target_lat: Optional[float],
        target_lon: Optional[float]
    ) -> Tuple[float, Optional[float]]:
        """Calculate proximity weight and return distance in km."""
        if not all([item_lat, item_lon, target_lat, target_lon]):
            return 0.5, None
        
        R = 6371
        
        lat1, lon1 = radians(target_lat), radians(target_lon)
        lat2, lon2 = radians(item_lat), radians(item_lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        distance = R * c
        
        if distance < 1:
            score = 1.0
        elif distance < 2:
            score = 0.9
        elif distance < 5:
            score = 0.7
        elif distance < 10:
            score = 0.5
        elif distance < 25:
            score = 0.3
        else:
            score = 0.1
        
        return score, distance
    
    def _calculate_severity_score(self, severity: str, category: str) -> float:
        """Calculate severity weight with category boost."""
        base_score = self.SEVERITY_WEIGHTS.get(severity.lower(), 0.3)
        
        category_lower = category.lower()
        boost = 0
        for cat, cat_boost in self.CATEGORY_SEVERITY_BOOST.items():
            if cat in category_lower:
                boost = max(boost, cat_boost)
        
        return min(1.0, base_score + boost)
    
    def _calculate_source_score(self, source_type: str, confidence: str) -> float:
        """Calculate source confidence weight."""
        source_base = self.SOURCE_CONFIDENCE_WEIGHTS.get(source_type.lower(), 0.5)
        
        confidence_multiplier = {
            "high": 1.0,
            "medium": 0.8,
            "low": 0.6
        }.get(confidence.lower(), 0.7)
        
        return source_base * confidence_multiplier
    
    def score_item(
        self,
        item: Dict,
        target_lat: Optional[float] = None,
        target_lon: Optional[float] = None
    ) -> Dict:
        """Score a single data item."""
        timestamp = item.get("timestamp")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except:
                timestamp = None
        
        recency_score = self._calculate_recency_score(timestamp)
        
        proximity_score, distance = self._calculate_proximity_score(
            item.get("lat"), item.get("lon"),
            target_lat, target_lon
        )
        
        severity_score = self._calculate_severity_score(
            item.get("severity", "low"),
            item.get("category", "")
        )
        
        source_score = self._calculate_source_score(
            item.get("source_type", "aggregator"),
            item.get("confidence", "medium")
        )
        
        weights = {
            "recency": 0.25,
            "proximity": 0.20,
            "severity": 0.35,
            "source": 0.20
        }
        
        final_score = (
            recency_score * weights["recency"] +
            proximity_score * weights["proximity"] +
            severity_score * weights["severity"] +
            source_score * weights["source"]
        )
        
        inclusion_reasons = []
        if proximity_score >= 0.7 and distance and distance < 5:
            inclusion_reasons.append(f"proximity <{int(distance)+1}km")
        if recency_score >= 0.7:
            inclusion_reasons.append("recency <72h")
        if severity_score >= 0.6:
            inclusion_reasons.append("severity high")
        if source_score >= 0.8:
            inclusion_reasons.append("official source")
        
        return {
            **item,
            "score": round(final_score, 3),
            "score_breakdown": {
                "recency": round(recency_score, 2),
                "proximity": round(proximity_score, 2),
                "severity": round(severity_score, 2),
                "source": round(source_score, 2)
            },
            "distance_km": round(distance, 1) if distance else None,
            "inclusion_reason": " + ".join(inclusion_reasons) if inclusion_reasons else "relevant data"
        }
    
    def score_and_rank(
        self,
        items: List[Dict],
        target_lat: Optional[float] = None,
        target_lon: Optional[float] = None
    ) -> List[Dict]:
        """Score all items and return ranked list."""
        scored_items = []
        
        for item in items:
            scored = self.score_item(item, target_lat, target_lon)
            
            if scored["score"] >= 0.2:
                scored_items.append(scored)
        
        scored_items.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_items[:self.max_items]
    
    def calculate_overall_risk(self, scored_items: List[Dict]) -> Tuple[str, str]:
        """Calculate overall risk level and confidence."""
        if not scored_items:
            return "Low", "Low"
        
        high_severity_count = sum(1 for item in scored_items if item.get("severity") in ["high", "critical"])
        avg_score = sum(item.get("score", 0) for item in scored_items) / len(scored_items)
        
        official_count = sum(1 for item in scored_items if "official" in item.get("source", "").lower())
        
        if high_severity_count >= 3 or avg_score >= 0.7:
            risk_level = "High"
        elif high_severity_count >= 1 or avg_score >= 0.5:
            risk_level = "Moderate"
        else:
            risk_level = "Low"
        
        if official_count >= len(scored_items) * 0.5:
            confidence = "High"
        elif official_count >= 1 or len(scored_items) >= 3:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        return risk_level, confidence


def get_scorer() -> SecurityScorer:
    """Get a scorer instance."""
    return SecurityScorer()
