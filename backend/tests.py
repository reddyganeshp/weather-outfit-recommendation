"""
Unit + integration tests for the Outfit Recommendation API
Run: pytest tests.py -v
"""

import json
import pytest
from app import app
from outfit_engine import OutfitEngine, _temp_band, _comfort_score
from cache_service import CacheService


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def engine():
    return OutfitEngine()


# ─────────────────────────────────────────────
#  Health endpoint
# ─────────────────────────────────────────────

def test_health(client):
    r = client.get('/health')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['status'] == 'healthy'


def test_api_info(client):
    r = client.get('/api/info')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert 'endpoints' in data


# ─────────────────────────────────────────────
#  Recommendation endpoint
# ─────────────────────────────────────────────

def test_recommend_sunny_casual(client):
    payload = {
        "temperature": 24,
        "weather_condition": "sunny",
        "humidity": 45,
        "wind_speed": 10,
        "occasion": "casual",
        "gender": "unisex"
    }
    r = client.post('/api/recommend',
                    data=json.dumps(payload),
                    content_type='application/json')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['status'] == 'success'
    rec = data['recommendation']
    assert 'outfit_name' in rec
    assert 'items' in rec
    assert len(rec['items']) >= 2
    assert 'accessories' in rec
    assert 'tips' in rec
    assert isinstance(rec['comfort_score'], float)


def test_recommend_snowy_formal(client):
    payload = {
        "temperature": -3,
        "weather_condition": "snowy",
        "occasion": "formal"
    }
    r = client.post('/api/recommend',
                    data=json.dumps(payload),
                    content_type='application/json')
    assert r.status_code == 200
    data = json.loads(r.data)
    rec = data['recommendation']
    # Should recommend warm items
    item_names = [i['name'].lower() for i in rec['items']]
    outerwear = [i for i in rec['items'] if i['category'] == 'outerwear']
    assert len(outerwear) >= 1


def test_recommend_missing_fields(client):
    r = client.post('/api/recommend',
                    data=json.dumps({"temperature": 20}),
                    content_type='application/json')
    assert r.status_code == 400
    data = json.loads(r.data)
    assert 'error' in data


def test_recommend_invalid_json(client):
    r = client.post('/api/recommend',
                    data="not-json",
                    content_type='application/json')
    assert r.status_code == 400


def test_recommend_preferred_colors(client):
    payload = {
        "temperature": 18,
        "weather_condition": "cloudy",
        "occasion": "work",
        "preferred_colors": ["navy", "white"]
    }
    r = client.post('/api/recommend',
                    data=json.dumps(payload),
                    content_type='application/json')
    assert r.status_code == 200


def test_recommend_async(client):
    payload = {
        "temperature": 15,
        "weather_condition": "cloudy",
        "async": True
    }
    r = client.post('/api/recommend',
                    data=json.dumps(payload),
                    content_type='application/json')
    assert r.status_code == 202
    data = json.loads(r.data)
    assert data['status'] == 'queued'
    assert 'job_id' in data
    assert 'poll_url' in data


# ─────────────────────────────────────────────
#  Catalogue endpoint
# ─────────────────────────────────────────────

def test_list_outfits(client):
    r = client.get('/api/outfits')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['total'] > 0
    assert isinstance(data['outfits'], list)


def test_list_outfits_filtered(client):
    r = client.get('/api/outfits?occasion=formal&weather=cloudy')
    assert r.status_code == 200
    data = json.loads(r.data)
    for item in data['outfits']:
        assert 'formal' in item['occasion_tags']


# ─────────────────────────────────────────────
#  Outfit engine unit tests
# ─────────────────────────────────────────────

@pytest.mark.parametrize("temp,expected", [
    (30, "hot"), (22, "warm"), (15, "mild"), (5, "cold"), (-2, "freezing")
])
def test_temp_band(temp, expected):
    assert _temp_band(temp) == expected


def test_comfort_score_ideal():
    score = _comfort_score(20, 50, 5)
    assert score >= 8.0


def test_comfort_score_extreme_heat():
    score = _comfort_score(35, 90, 10)
    assert score < 6.0


def test_engine_hot_no_outerwear(engine):
    rec = engine.recommend(32, "sunny", 40, 5, "casual")
    categories = [i['category'] for i in rec['items']]
    assert 'outerwear' not in categories


def test_engine_cold_has_outerwear(engine):
    rec = engine.recommend(-5, "snowy", 60, 15, "casual")
    categories = [i['category'] for i in rec['items']]
    assert 'outerwear' in categories


def test_engine_returns_all_required_keys(engine):
    rec = engine.recommend(18, "cloudy", 55, 10, "work")
    for key in ['outfit_name', 'items', 'accessories',
                'tips', 'comfort_score', 'style_notes', 'color_palette']:
        assert key in rec


# ─────────────────────────────────────────────
#  Cache service unit tests
# ─────────────────────────────────────────────

def test_cache_set_get():
    cache = CacheService()
    key = cache.make_key(20, "sunny", 50, 5, "casual", "unisex")
    cache.set(key, {"data": "test"})
    result = cache.get(key)
    assert result == {"data": "test"}


def test_cache_miss():
    cache = CacheService()
    assert cache.get("nonexistent") is None


def test_cache_expiry():
    import time
    cache = CacheService(ttl=1)
    key = cache.make_key(20, "sunny", 50, 5, "casual", "unisex")
    cache.set(key, {"data": "expires"})
    time.sleep(1.1)
    assert cache.get(key) is None


def test_cache_eviction():
    cache = CacheService(max_size=2)
    k1 = cache.make_key(20, "sunny", 50, 5, "casual", "unisex")
    k2 = cache.make_key(22, "cloudy", 55, 8, "work", "unisex")
    k3 = cache.make_key(5, "snowy", 70, 20, "outdoor", "male")
    cache.set(k1, {"a": 1})
    cache.set(k2, {"b": 2})
    cache.set(k3, {"c": 3})
    assert cache.size <= 2


# ─────────────────────────────────────────────
#  Error handlers
# ─────────────────────────────────────────────

def test_404(client):
    r = client.get('/does-not-exist')
    assert r.status_code == 404


def test_405(client):
    r = client.delete('/api/recommend')
    assert r.status_code == 405
