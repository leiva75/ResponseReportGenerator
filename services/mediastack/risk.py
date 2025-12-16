def compute_risk(stats: dict) -> dict:
    strong_count = stats.get("strong_count", 0)
    incident_count = stats.get("incident_count", 0)
    gathering_count = stats.get("gathering_count", 0)
    sources = stats.get("sources", [])
    total = stats.get("total_articles", 0)
    
    medium_count = max(0, incident_count - strong_count)
    score = (2 * strong_count) + (1 * medium_count) + (1 * gathering_count)
    
    if score <= 2:
        risk_level = "Low"
    elif score <= 6:
        risk_level = "Medium"
    else:
        risk_level = "High"
    
    source_count = len(sources)
    if total >= 8 and source_count >= 3:
        confidence = "High"
    elif total >= 4:
        confidence = "Medium"
    else:
        confidence = "Low"
    
    risk_drivers = []
    if strong_count > 0:
        risk_drivers.append(f"Violent incident mentions ({strong_count})")
    if gathering_count > 0:
        risk_drivers.append(f"Protest/demonstration mentions ({gathering_count})")
    if incident_count > 0 and strong_count == 0:
        risk_drivers.append(f"Security-related coverage ({incident_count})")
    if total < 5:
        risk_drivers.append("Limited news coverage for this area")
    if not risk_drivers:
        risk_drivers.append("No significant security signals detected")
    
    operational_notes = []
    if risk_level == "Low":
        operational_notes.append("Standard precautions recommended")
        operational_notes.append("No specific areas to avoid identified")
    elif risk_level == "Medium":
        operational_notes.append("Heightened awareness recommended")
        if gathering_count > 0:
            operational_notes.append("Monitor local news for demonstration locations")
        operational_notes.append("Avoid known incident areas if identified")
    else:
        operational_notes.append("Exercise increased caution")
        operational_notes.append("Avoid crowded public areas if possible")
        operational_notes.append("Monitor local security updates frequently")
        if gathering_count > 0:
            operational_notes.append("Steer clear of announced protest routes")
    
    return {
        "risk_level": risk_level,
        "confidence": confidence,
        "basis": "news-based reporting (MediaStack)",
        "risk_drivers": risk_drivers[:4],
        "operational_notes": operational_notes[:4],
        "score": score
    }
