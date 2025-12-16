from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import math

from .collectors import fetch_past_incidents, fetch_upcoming_protests

risk_bp = Blueprint("risk", __name__)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def risk_level(distance_km):
    if distance_km is None:
        return "UNKNOWN"
    if distance_km < 2.0:
        return "RED"
    if distance_km <= 5.0:
        return "AMBER"
    return "GREEN"


def parse_iso(dt_str: str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def sort_events(events):
    def key(e):
        d = e.get("distance_km")
        dist_key = d if isinstance(d, (int, float)) else 10**9
        dt = parse_iso(e.get("datetime", "")) or datetime(1970, 1, 1, tzinfo=timezone.utc)
        return (dist_key, -dt.timestamp())
    return sorted(events, key=key)


def format_event_block(e):
    cat = e.get("category", "UNKNOWN")
    loc = e.get("location", "unknown")
    dt = e.get("datetime", "unknown")
    src = e.get("source", "-")
    conf = float(e.get("confidence", 0.0))

    dist = e.get("distance_km")
    dist_txt = f"{dist:.1f} km" if isinstance(dist, (int, float)) else "unknown"
    lvl = e.get("risk_level") or risk_level(dist)

    return "\n".join([
        f"{cat} — {loc} [{lvl}]",
        f"Distance: {dist_txt} from your position",
        f"Date: {dt}",
        f"Source: {src} — confidence {conf:.2f}",
    ])


def pad_to_34(blocks):
    while len(blocks) < 34:
        blocks.append("\n".join([
            "N/A — No reliable local incident found for this slot [UNKNOWN]",
            "Distance: unknown from your position",
            "Date: unknown",
            "Source: - — confidence 0.00",
        ]))
    return blocks[:34]


@risk_bp.route("/riskbrief", methods=["POST"])
def riskbrief():
    data = request.get_json(force=True) or {}

    city = (data.get("city") or "").strip()
    country = (data.get("country") or "").strip()

    user_lat = data.get("user_lat")
    user_lon = data.get("user_lon")

    start_dt = parse_iso(data.get("start_datetime", ""))
    end_dt = parse_iso(data.get("end_datetime", ""))

    if not city or not country:
        return jsonify({"error": "city and country are required"}), 400
    if not isinstance(user_lat, (int, float)) or not isinstance(user_lon, (int, float)):
        return jsonify({"error": "user_lat and user_lon (numbers) are required"}), 400
    if not start_dt or not end_dt:
        return jsonify({"error": "start_datetime and end_datetime must be valid ISO strings"}), 400

    past = fetch_past_incidents(city, country, since_days=30)
    upcoming = fetch_upcoming_protests(city, country, start_dt, end_dt)

    for e in past:
        lat, lon = e.get("lat"), e.get("lon")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            e["distance_km"] = haversine_km(user_lat, user_lon, lat, lon)
        else:
            e["distance_km"] = None
        e["risk_level"] = risk_level(e["distance_km"])

    for e in upcoming:
        lat, lon = e.get("lat"), e.get("lon")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            e["distance_km"] = haversine_km(user_lat, user_lon, lat, lon)
        else:
            e["distance_km"] = None
        e["risk_level"] = risk_level(e["distance_km"])

    past_sorted = sort_events(past)
    upcoming_sorted = sort_events(upcoming)

    last34_blocks = [format_event_block(e) for e in past_sorted][:34]
    last34_blocks = pad_to_34(last34_blocks)

    upcoming_blocks = [format_event_block(e) for e in upcoming_sorted]
    if not upcoming_blocks:
        upcoming_blocks = ["None announced / insufficient public data"]

    alerts = [e for e in past_sorted if e.get("risk_level") in ("RED", "AMBER")]
    nearest_alerts_blocks = [format_event_block(e) for e in alerts[:5]]

    return jsonify({
        "city": city,
        "country": country,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "last34_blocks": last34_blocks,
        "upcoming_protests_blocks": upcoming_blocks,
        "nearest_alerts_blocks": nearest_alerts_blocks,
        "counts": {
            "past_found": len(past),
            "upcoming_found": len(upcoming),
            "alerts_found": len(alerts),
        }
    })
