"""
Weather-Driven Outfit Recommendation Service
Your Web Service (Service 1)
Deployed on: AWS Elastic Beanstalk
"""
from __future__ import annotations

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import logging
import requests
from datetime import datetime
from outfit_engine import OutfitEngine
from queue_service import QueueService
from cache_service import CacheService
from db_service import (
    init_db, get_api_key, set_api_key,
    get_all_keys, save_outfit_history, get_outfit_history
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ── Initialise services ───────────────────────────────────────────────────────
outfit_engine = OutfitEngine()
queue_service  = QueueService()
cache_service  = CacheService()

# ── Initialise SQLite database ────────────────────────────────────────────────
init_db()

# ══════════════════════════════════════════════════════════════════════════════
#  API KEY CONFIGURATION  (loaded from SQLite, fallback to env vars)
# ══════════════════════════════════════════════════════════════════════════════

# 1. OpenWeatherMap
OWM_API_KEY  = get_api_key("OWM_API_KEY")  or os.environ.get("OWM_API_KEY",  "568d4f6a784fd23816ccfad2e96eb4a1")
OWM_BASE_URL = os.environ.get("OWM_BASE_URL", "https://api.openweathermap.org/data/2.5")

# 2. Friend Poll Hub API
FRIEND_API_BASE = get_api_key("FRIEND_API_URL") or os.environ.get(
    "FRIEND_API_BASE",
    "https://c730261bf2bc4236bcd5fd5f1d1c84bc.vfs.cloud9.us-east-1.amazonaws.com"
)
FRIEND_API_KEY = get_api_key("FRIEND_API_KEY") or os.environ.get(
    "FRIEND_API_KEY", "pollhub-secret-key-2024"
)

logger.info("OWM key     : %s…", OWM_API_KEY[:8])
logger.info("Friend API  : %s",  FRIEND_API_BASE)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER — OpenWeatherMap
# ══════════════════════════════════════════════════════════════════════════════

def fetch_live_weather(city: str, country_code: str = "IE") -> dict:
    """Fetch live weather from OpenWeatherMap."""
    key = get_api_key("OWM_API_KEY") or OWM_API_KEY
    try:
        url  = f"{OWM_BASE_URL}/weather?q={city},{country_code}&appid={key}&units=metric"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        d = resp.json()
        return {
            "temperature":       round(d["main"]["temp"], 1),
            "feels_like":        round(d["main"]["feels_like"], 1),
            "weather_condition": d["weather"][0]["main"],
            "description":       d["weather"][0]["description"],
            "humidity":          d["main"]["humidity"],
            "wind_speed":        round(d["wind"]["speed"] * 3.6, 1),
            "city":              d["name"],
            "country":           d["sys"]["country"],
        }
    except Exception as exc:
        logger.error("OWM error: %s", exc)
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER — Friend Poll Hub API
# ══════════════════════════════════════════════════════════════════════════════

def fetch_friend_polls() -> dict:
    """Fetch polls from classmate Poll Hub API."""
    base = get_api_key("FRIEND_API_URL") or FRIEND_API_BASE
    key  = get_api_key("FRIEND_API_KEY") or FRIEND_API_KEY
    try:
        resp = requests.get(
            f"{base}/api/polls",
            headers={"x-api-key": key},
            timeout=5
        )
        resp.raise_for_status()
        logger.info("Friend Poll API OK")
        return {"success": True, "service": "PollHub", "data": resp.json()}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "PollHub unavailable", "data": []}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "PollHub timed out",   "data": []}
    except Exception as exc:
        return {"success": False, "error": str(exc),              "data": []}


# ══════════════════════════════════════════════════════════════════════════════
#  Health / Info
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status":    "healthy",
        "service":   "Outfit Recommendation API",
        "version":   "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database":  "SQLite",
        "config": {
            "owm_key_set":    bool(get_api_key("OWM_API_KEY")),
            "friend_api_url": get_api_key("FRIEND_API_URL") or FRIEND_API_BASE,
        }
    }), 200


@app.route('/api/info', methods=['GET'])
def api_info():
    return jsonify({
        "service":     "Weather-Driven Outfit Recommendation API",
        "version":     "2.0.0",
        "description": "Outfit recommendations based on live weather data.",
        "endpoints": {
            "POST /api/recommend":           "Get outfit recommendation",
            "GET  /api/recommend/<job_id>":  "Poll async result",
            "GET  /api/outfits":             "Browse outfit catalogue",
            "GET  /api/weather/<city>":      "Live weather from OWM",
            "GET  /api/friend/polls":        "Friend Poll Hub API",
            "POST /api/friend/polls/<id>/vote": "Vote on a poll",
            "GET  /api/config":              "Get API config from DB",
            "POST /api/config":              "Update API config in DB",
            "GET  /api/history":             "Outfit history from SQLite",
            "GET  /health":                  "Health check",
        }
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
#  SQLite Config endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/config', methods=['GET'])
def get_config():
    """Return config from SQLite for the frontend."""
    return jsonify({
        "success":    True,
        "owm_key":    get_api_key("OWM_API_KEY")   or OWM_API_KEY,
        "friend_url": get_api_key("FRIEND_API_URL") or FRIEND_API_BASE,
    })


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update API keys stored in SQLite."""
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    updated = []
    for key in ["OWM_API_KEY", "FRIEND_API_URL", "FRIEND_API_KEY"]:
        if key in data and data[key]:
            set_api_key(key, data[key])
            updated.append(key)
    return jsonify({"success": True, "updated": updated})


# ══════════════════════════════════════════════════════════════════════════════
#  Outfit History (SQLite)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/history', methods=['GET'])
def outfit_history():
    """Return recent outfit history from SQLite."""
    limit   = int(request.args.get('limit', 10))
    history = get_outfit_history(limit)
    return jsonify({"success": True, "history": history, "count": len(history)})


# ══════════════════════════════════════════════════════════════════════════════
#  Weather endpoint (OpenWeatherMap)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/weather/<path:city>', methods=['GET'])
def get_weather(city):
    """Fetch live weather via OpenWeatherMap API."""
    # Support city,COUNTRY format e.g. Belfast,GB
    if ',' in city:
        city, country = city.split(',', 1)
    else:
        country = request.args.get('country', 'IE')
    weather = fetch_live_weather(city, country)
    if not weather:
        return jsonify({"error": f"Could not fetch weather for '{city}'"}), 502
    return jsonify({"success": True, "source": "OpenWeatherMap", "weather": weather})


# ══════════════════════════════════════════════════════════════════════════════
#  Friend Poll Hub API endpoints
# ══════════════════════════════════════════════════════════════════════════════


@app.route('/api/friend/polls', methods=['GET', 'POST'])
def friend_polls_create():
    base = get_api_key("FRIEND_API_URL") or FRIEND_API_BASE
    key  = get_api_key("FRIEND_API_KEY") or FRIEND_API_KEY
    if request.method == 'GET':
        category = request.args.get('category', '')
        try:
            url  = f"{base}/api/polls" + (f"?category={category}" if category else "")
            resp = requests.get(url, headers={"x-api-key": key}, timeout=5)
            resp.raise_for_status()
            return jsonify({"success": True, "service": "PollHub", "data": resp.json()})
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc), "data": []}), 502
    else:
        try:
            data = request.get_json(force=True)
            resp = requests.post(
                f"{base}/api/polls",
                json=data,
                headers={"x-api-key": key, "Content-Type": "application/json"},
                timeout=5
            )
            resp.raise_for_status()
            return jsonify({"success": True, "data": resp.json()})
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 502



@app.route('/api/friend/polls/<poll_id>/results', methods=['GET'])
def get_poll_results(poll_id):
    """Get live results for a specific poll."""
    base = get_api_key("FRIEND_API_URL") or FRIEND_API_BASE
    key  = get_api_key("FRIEND_API_KEY") or FRIEND_API_KEY
    try:
        resp = requests.get(
            f"{base}/api/polls/{poll_id}/results",
            headers={"x-api-key": key}, timeout=5
        )
        resp.raise_for_status()
        return jsonify({"success": True, "data": resp.json()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 502


@app.route('/api/friend/polls/<poll_id>/vote', methods=['POST'])
def vote_poll(poll_id):
    """Submit a vote to a poll."""
    base = get_api_key("FRIEND_API_URL") or FRIEND_API_BASE
    key  = get_api_key("FRIEND_API_KEY") or FRIEND_API_KEY
    try:
        data = request.get_json(force=True)
        resp = requests.post(
            f"{base}/api/polls/{poll_id}/vote",
            json=data,
            headers={"x-api-key": key, "Content-Type": "application/json"},
            timeout=5
        )
        resp.raise_for_status()
        return jsonify({"success": True, "data": resp.json()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 502


# ══════════════════════════════════════════════════════════════════════════════
#  Core recommendation endpoint
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/recommend', methods=['POST'])
def recommend():
    """
    Receive weather + preferences, return outfit recommendation.
    Auto-fetches weather from OWM if 'city' is provided.
    Saves result to SQLite history.
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # Auto-fetch weather if city provided
        if 'city' in data and 'temperature' not in data:
            weather = fetch_live_weather(data['city'], data.get('country', 'IE'))
            if not weather:
                return jsonify({"error": f"Could not fetch weather for '{data['city']}'"}), 502
            data['temperature']       = weather['temperature']
            data['weather_condition'] = weather['weather_condition']
            data.setdefault('humidity',   weather['humidity'])
            data.setdefault('wind_speed', weather['wind_speed'])

        # Validate
        missing = [f for f in ['temperature', 'weather_condition'] if f not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        temperature       = float(data['temperature'])
        weather_condition = data['weather_condition'].lower()
        humidity          = float(data.get('humidity', 50))
        wind_speed        = float(data.get('wind_speed', 0))
        occasion          = data.get('occasion', 'casual').lower()
        gender            = data.get('gender', 'unisex').lower()
        preferred_colors  = data.get('preferred_colors', [])
        async_mode        = data.get('async', False)
        city              = data.get('city', 'Unknown')

        # Cache check
        cache_key = cache_service.make_key(
            temperature, weather_condition, humidity, wind_speed, occasion, gender
        )
        cached = cache_service.get(cache_key)
        if cached:
            cached['source'] = 'cache'
            return jsonify(cached), 200

        # Async mode
        if async_mode:
            job_id = str(uuid.uuid4())
            queue_service.enqueue({
                "job_id": job_id, "temperature": temperature,
                "weather_condition": weather_condition, "humidity": humidity,
                "wind_speed": wind_speed, "occasion": occasion,
                "gender": gender, "preferred_colors": preferred_colors,
                "created_at": datetime.utcnow().isoformat()
            })
            return jsonify({"status": "queued", "job_id": job_id,
                            "poll_url": f"/api/recommend/{job_id}"}), 202

        # Sync mode
        recommendation = outfit_engine.recommend(
            temperature=temperature, weather_condition=weather_condition,
            humidity=humidity, wind_speed=wind_speed,
            occasion=occasion, gender=gender, preferred_colors=preferred_colors
        )

        # Save to SQLite history
        try:
            save_outfit_history(
                city=city, temperature=temperature,
                condition=weather_condition,
                outfit_name=recommendation.get('outfit_name', ''),
                occasion=occasion, gender=gender
            )
        except Exception as e:
            logger.warning("History save failed: %s", e)

        # Also fetch friend polls
        friend_data = fetch_friend_polls()

        response = {
            "status":     "success",
            "source":     "computed",
            "request_id": str(uuid.uuid4()),
            "timestamp":  datetime.utcnow().isoformat(),
            "input": {
                "temperature": temperature, "weather_condition": weather_condition,
                "humidity": humidity, "wind_speed": wind_speed,
                "occasion": occasion, "gender": gender
            },
            "recommendation": recommendation,
            "friend_service": {
                "service": "PollHub API",
                "url":     FRIEND_API_BASE,
                "success": friend_data["success"],
                "data":    friend_data.get("data", [])
            }
        }

        cache_service.set(cache_key, response)
        return jsonify(response), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/recommend/<job_id>', methods=['GET'])
def poll_recommendation(job_id):
    result = queue_service.get_result(job_id)
    if result is None:
        return jsonify({"status": "pending", "job_id": job_id}), 202
    return jsonify(result), 200


# ══════════════════════════════════════════════════════════════════════════════
#  Outfit catalogue
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/outfits', methods=['GET'])
def list_outfits():
    occasion = request.args.get('occasion')
    weather  = request.args.get('weather')
    gender   = request.args.get('gender', 'unisex')
    outfits  = outfit_engine.get_catalogue(occasion=occasion, weather=weather, gender=gender)
    return jsonify({"total": len(outfits),
                    "filters": {"occasion": occasion, "weather": weather, "gender": gender},
                    "outfits": outfits}), 200


# ══════════════════════════════════════════════════════════════════════════════
#  Error handlers
# ══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


# ══════════════════════════════════════════════════════════════════════════════
#  Serve frontend
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def serve_frontend():
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    return send_from_directory(frontend_dir, path)


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    port  = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    logger.info("Starting Outfit Recommendation API on port %d", port)
    app.run(host='0.0.0.0', port=port, debug=debug)