"""
User Profile Service  — Classmate Web Service (Service 2)
==========================================================
This represents the API your classmate would write and share with you.
It stores and retrieves user style preferences so the outfit recommender
can personalise its output per user.

API:
  POST /api/profiles           — create profile
  GET  /api/profiles/<user_id> — get profile
  PUT  /api/profiles/<user_id> — update profile
  GET  /health                 — health check
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)

# In-memory store (classmate would use a real DB)
_profiles: dict[str, dict] = {
    "demo-user": {
        "user_id": "demo-user",
        "name": "Demo User",
        "preferred_styles": ["casual", "smart-casual"],
        "preferred_colors": ["navy", "white", "olive"],
        "gender": "unisex",
        "size": "M",
        "climate_sensitivity": "normal",
        "created_at": "2024-01-01T00:00:00"
    }
}


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "User Profile API"}), 200


@app.route('/api/profiles', methods=['POST'])
def create_profile():
    data = request.get_json(force=True) or {}
    user_id = str(uuid.uuid4())
    profile = {
        "user_id": user_id,
        "name": data.get("name", "Anonymous"),
        "preferred_styles": data.get("preferred_styles", ["casual"]),
        "preferred_colors": data.get("preferred_colors", []),
        "gender": data.get("gender", "unisex"),
        "size": data.get("size", "M"),
        "climate_sensitivity": data.get("climate_sensitivity", "normal"),
        "created_at": datetime.utcnow().isoformat()
    }
    _profiles[user_id] = profile
    return jsonify(profile), 201


@app.route('/api/profiles/<user_id>', methods=['GET'])
def get_profile(user_id):
    profile = _profiles.get(user_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile), 200


@app.route('/api/profiles/<user_id>', methods=['PUT'])
def update_profile(user_id):
    if user_id not in _profiles:
        return jsonify({"error": "Profile not found"}), 404
    data = request.get_json(force=True) or {}
    _profiles[user_id].update({
        k: v for k, v in data.items()
        if k in ("preferred_styles", "preferred_colors",
                 "gender", "size", "climate_sensitivity", "name")
    })
    return jsonify(_profiles[user_id]), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
