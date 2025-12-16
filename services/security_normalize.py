"""
Normalization service for City Security Brief
Converts raw connector data into standardized brief format.
"""
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SecurityNormalizer:
    """Normalizes and formats security data into brief format."""
    
    MAX_KEY_RISKS = 3
    MAX_UPCOMING_PROTESTS = 3
    MAX_RECENT_UNREST = 2
    MAX_ADVICE_BULLETS = 5
    
    CATEGORY_GROUPS = {
        "crime": ["crime", "murder", "killing", "stabbing", "shooting", "robbery", "assault", "theft", "homicide"],
        "violence": ["violence", "violent-crime", "attack"],
        "protests": ["protest", "demonstration", "rally", "march"],
        "unrest": ["riot", "unrest", "civil_disorder", "clash"],
        "transport": ["strike", "disruption", "transport", "blockage"],
        "general": ["crime_trend", "advisory", "other"]
    }
    
    def __init__(self):
        pass
    
    def _categorize_items(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Group items by category type."""
        grouped = {
            "crime": [],
            "violence": [],
            "protests": [],
            "unrest": [],
            "transport": [],
            "general": []
        }
        
        for item in items:
            category = item.get("category", "").lower()
            placed = False
            
            for group_name, keywords in self.CATEGORY_GROUPS.items():
                if any(kw in category for kw in keywords):
                    grouped[group_name].append(item)
                    placed = True
                    break
            
            if not placed:
                grouped["general"].append(item)
        
        return grouped
    
    def _format_bullet(self, item: Dict, include_source: bool = True) -> str:
        """Format a single item as a bullet point."""
        title = item.get("title", "")[:80]
        
        if include_source:
            source = item.get("source", "Unknown")
            return f"{title} [{source}]"
        
        return title
    
    def _extract_key_risks(self, grouped: Dict[str, List[Dict]]) -> List[str]:
        """Extract top key risks (recent crimes from last 3 days)."""
        risks = []
        
        for item in grouped["crime"][:3]:
            risks.append(self._format_bullet(item))
        
        for item in grouped["violence"][:1]:
            if len(risks) < 5:
                risks.append(self._format_bullet(item))
        
        for item in grouped["unrest"][:1]:
            if len(risks) < 5:
                risks.append(self._format_bullet(item))
        
        return risks[:5]
    
    def _extract_protests(self, grouped: Dict[str, List[Dict]]) -> Tuple[List[str], List[str]]:
        """Extract upcoming and recent protest information."""
        upcoming = []
        recent = []
        
        for item in grouped["protests"]:
            title = item.get("title", "")
            location = item.get("location", "")
            source = item.get("source", "")
            
            source_type = "official" if "official" in source.lower() or "police" in source.lower() else "reported"
            
            bullet = f"{title}"
            if location and location.lower() not in title.lower():
                bullet += f" ({location})"
            bullet += f" [{source_type}]"
            
            upcoming.append(bullet)
        
        for item in grouped["unrest"]:
            title = item.get("title", "")
            recent.append(f"{title} [{item.get('source', 'Media')}]")
        
        return upcoming[:self.MAX_UPCOMING_PROTESTS], recent[:self.MAX_RECENT_UNREST]
    
    def _generate_advice(self, grouped: Dict[str, List[Dict]], city: str, country: str) -> List[str]:
        """Generate operational advice bullets."""
        advice = []
        
        advice.append("Keep group together in busy areas; maintain buddy system")
        
        if grouped["violence"]:
            advice.append("Avoid displaying valuables; use hotel safes for passports")
        
        if grouped["protests"] or grouped["unrest"]:
            advice.append("Avoid demonstration areas; monitor local news for updates")
        
        if grouped["transport"]:
            high_risk = any(item.get("severity") in ["medium", "high"] for item in grouped["transport"])
            if high_risk:
                advice.append("Check transport status 24h before travel; have backup plans")
            else:
                advice.append("Confirm transport schedules day before departure")
        
        advice.append("Share venue security contact with all crew; establish rally point")
        
        if not grouped["violence"] and not grouped["unrest"]:
            advice.append(f"{city} generally safe; standard touring precautions apply")
        
        return advice[:self.MAX_ADVICE_BULLETS]
    
    def normalize_to_brief(
        self,
        items: List[Dict],
        city: str,
        country: str,
        risk_level: str,
        confidence: str
    ) -> Dict:
        """Convert scored items into structured brief format."""
        grouped = self._categorize_items(items)
        
        key_risks = self._extract_key_risks(grouped)
        upcoming_protests, recent_unrest = self._extract_protests(grouped)
        advice = self._generate_advice(grouped, city, country)
        
        sources = list(set(item.get("source", "Unknown") for item in items if item.get("source")))
        
        if not key_risks:
            key_risks = ["No high-severity incidents reported in recent data"]
        
        brief = {
            "city": city,
            "country": country,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "risk_level": risk_level,
            "confidence": confidence,
            "key_risks": key_risks,
            "protests": {
                "upcoming": upcoming_protests if upcoming_protests else ["No confirmed upcoming demonstrations found"],
                "recent": recent_unrest if recent_unrest else ["No recent unrest reported"]
            },
            "advice": advice,
            "sources": sources[:6],
            "source_details": [
                {
                    "source": item.get("source"),
                    "url": item.get("url"),
                    "timestamp": item.get("timestamp"),
                    "confidence": item.get("confidence")
                }
                for item in items[:10] if item.get("url")
            ],
            "disclaimer": "This brief is informational and may be incomplete. Always verify with local authorities / venue security."
        }
        
        return brief
    
    def format_text_brief(self, brief: Dict) -> str:
        """Format brief as copy-friendly text block."""
        lines = []
        
        lines.append(f"CITY SECURITY BRIEF — {brief['city']}, {brief['country']} — {brief['generated_at']}")
        lines.append(f"Overall Risk: {brief['risk_level']} (Confidence: {brief['confidence']})")
        lines.append("")
        
        lines.append("Key Risks (now):")
        for risk in brief["key_risks"]:
            lines.append(f"  • {risk}")
        lines.append("")
        
        lines.append("Protests / Demonstrations:")
        lines.append("  Upcoming (declared/announced):")
        for protest in brief["protests"]["upcoming"]:
            lines.append(f"    • {protest}")
        lines.append("  Recent unrest:")
        for unrest in brief["protests"]["recent"]:
            lines.append(f"    • {unrest}")
        lines.append("")
        
        lines.append("Operational Advice (tour):")
        for advice in brief["advice"]:
            lines.append(f"  • {advice}")
        lines.append("")
        
        lines.append(f"Sources: {', '.join(brief['sources'][:5])}")
        lines.append("")
        lines.append(f"⚠️ {brief['disclaimer']}")
        
        return "\n".join(lines)


def get_normalizer() -> SecurityNormalizer:
    """Get a normalizer instance."""
    return SecurityNormalizer()
