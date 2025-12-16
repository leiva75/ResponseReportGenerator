from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import logging
import os

from .provider import fetch_news, normalize_country_code
from .classifier import classify_articles
from .risk import compute_risk
from .cache import cache_get, cache_set, cache_get_stale

logger = logging.getLogger(__name__)

mediastack_bp = Blueprint("mediastack", __name__)


@mediastack_bp.route("/security-brief", methods=["GET"])
def security_brief():
    city = request.args.get("city", "").strip()
    country_input = request.args.get("country", "").strip()
    window_days = request.args.get("window_days", "14")
    
    try:
        window_days = int(window_days)
        if window_days not in [7, 14, 30]:
            window_days = 14
    except ValueError:
        window_days = 14
    
    if not city or not country_input:
        return jsonify({"error": "city and country are required"}), 400
    
    country_code = normalize_country_code(country_input)
    if not country_code:
        return jsonify({
            "error": f"Could not resolve country: '{country_input}'",
            "hint": "Use ISO2 code (e.g., MX, FR, US) or country name (e.g., France, Mexico)"
        }), 400
    
    cached = cache_get(city, country_code, window_days)
    if cached:
        logger.info(f"Cache hit for {city}, {country_code}, {window_days}d")
        cached["meta"]["from_cache"] = True
        return jsonify(cached)
    
    if not os.environ.get("MEDIASTACK_API_KEY"):
        return jsonify({
            "error": "MediaStack API not configured",
            "message": "Please add MEDIASTACK_API_KEY to Secrets"
        }), 503
    
    articles = fetch_news(city, country_code, window_days)
    
    if not articles:
        stale = cache_get_stale(city, country_code, window_days)
        if stale:
            logger.warning(f"Using stale cache for {city}, {country_code}")
            stale["meta"]["from_cache"] = True
            stale["meta"]["stale"] = True
            return jsonify(stale)
        
        return jsonify({
            "meta": {
                "city": city,
                "country": country_code.upper(),
                "country_input": country_input,
                "window_days": window_days,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "error": "Data temporarily unavailable"
            },
            "recent_incidents": [],
            "upcoming_gatherings": [],
            "risk": {
                "risk_level": "Unknown",
                "confidence": "Low",
                "basis": "news-based reporting (MediaStack)",
                "risk_drivers": ["Unable to fetch current data"],
                "operational_notes": ["Check again later", "Use alternative sources"]
            }
        })
    
    classified = classify_articles(articles)
    risk = compute_risk(classified["stats"])
    
    result = {
        "meta": {
            "city": city,
            "country": country_code.upper(),
            "country_input": country_input,
            "window_days": window_days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "articles_analyzed": classified["stats"]["total_articles"],
            "sources_count": len(classified["stats"]["sources"]),
            "from_cache": False
        },
        "recent_incidents": classified["incidents"],
        "upcoming_gatherings": classified["gatherings"],
        "risk": risk
    }
    
    cache_set(city, country_code, window_days, result)
    
    return jsonify(result)
