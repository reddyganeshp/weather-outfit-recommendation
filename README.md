# WeatherWear — Weather-Driven Outfit Recommendation System

A full-stack cloud application that recommends outfits based on real-time weather data, user preferences, and occasion. Built with Python 3 + Flask, deployed on AWS.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (HTML/JS)                      │
│              Served via S3 + CloudFront (AWS)               │
└──────┬───────────┬──────────────┬────────────┬─────────────┘
       │           │              │            │
       ▼           ▼              ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  Outfit  │ │ Profile  │ │Open-Meteo│ │Open-Meteo│
│   API    │ │   API    │ │ Weather  │ │Geocoding │
│ (YOURS)  │ │(CLASSMATE│ │ (PUBLIC) │ │ (PUBLIC) │
│ Service 1│ │Service 2)│ │Service 3 │ │Service 4 │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
  Flask/AWS    Flask/       REST API     REST API
  EB (auto-   classmate's  No key req.  No key req.
  scaling)    cloud
```

## Web Services

| # | Service | Type | Technology |
|---|---------|------|-----------|
| 1 | **Outfit Recommendation API** | Yours | Python 3, Flask, AWS Elastic Beanstalk |
| 2 | **User Profile API** | Classmate's | Python 3, Flask |
| 3 | **Open-Meteo Weather API** | Public | REST, no API key needed |
| 4 | **Open-Meteo Geocoding API** | Public | REST, no API key needed |

---

## Quick Start (Local)

### Prerequisites
- Python 3.11+
- Docker + Docker Compose (optional but recommended)

### Option A — Docker Compose (recommended)

```bash
# Start all services
docker-compose up --build

# Services available at:
#   Frontend:    http://localhost:8080
#   Outfit API:  http://localhost:5000
#   Profile API: http://localhost:5001
```

### Option B — Manual

```bash
# Terminal 1: Start your Outfit API
cd backend
pip install -r requirements.txt
python app.py

# Terminal 2: Start the classmate Profile API
cd classmate-service
pip install -r requirements.txt
python app.py

# Terminal 3: Serve frontend
cd frontend
python -m http.server 8080
```

Open http://localhost:8080 in your browser.

---

## Running Tests

```bash
cd backend
pip install pytest
pytest tests.py -v
```

**28 tests** covering:
- All API endpoints (recommend, catalogue, health, info)
- Outfit engine logic (temperature bands, comfort score, seasonal logic)
- Cache service (set/get, expiry, eviction)
- Queue service (enqueue, async processing)
- Edge cases and error handling

---

## Your API — Endpoint Reference

### `POST /api/recommend`

Receive weather + preference data, return personalised outfit recommendation.

**Request body:**
```json
{
  "temperature": 18.5,
  "weather_condition": "rainy",
  "humidity": 75,
  "wind_speed": 20,
  "occasion": "work",
  "gender": "unisex",
  "preferred_colors": ["navy", "white"],
  "async": false
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `temperature` | float | ✅ | Degrees Celsius |
| `weather_condition` | string | ✅ | `sunny` `cloudy` `rainy` `snowy` `windy` |
| `humidity` | float | ❌ | 0–100, default 50 |
| `wind_speed` | float | ❌ | km/h, default 0 |
| `occasion` | string | ❌ | `casual` `work` `formal` `outdoor` `sport` |
| `gender` | string | ❌ | `unisex` `male` `female` |
| `preferred_colors` | list | ❌ | e.g. `["navy","white"]` |
| `async` | bool | ❌ | true = queue job, returns job_id |

**Response (200):**
```json
{
  "status": "success",
  "source": "computed",
  "recommendation": {
    "outfit_name": "Rainy Day Chic",
    "items": [
      { "category": "top", "name": "Oxford Button-Down", "chosen_color": "white" },
      { "category": "bottom", "name": "Slim-Fit Jeans", "chosen_color": "dark wash" },
      { "category": "outerwear", "name": "Trench Coat", "chosen_color": "camel" },
      { "category": "footwear", "name": "Chelsea Boots", "chosen_color": "black" }
    ],
    "accessories": ["Compact umbrella", "Waterproof bag"],
    "tips": ["Tuck your trousers into boots or wear water-resistant shoes."],
    "comfort_score": 7.0,
    "style_notes": "...",
    "color_palette": ["white", "dark wash", "camel", "black"]
  }
}
```

### `GET /api/recommend/<job_id>`
Poll result of an async recommendation job.
- `202` → still processing
- `200` → complete, body contains `recommendation`

### `GET /api/outfits`
Browse the outfit catalogue.
- `?occasion=work` — filter by occasion
- `?weather=rainy` — filter by weather
- `?gender=female` — filter by gender

### `GET /health`
Returns `{"status": "healthy"}` — used by load balancer health checks.

### `GET /api/info`
Full API documentation as JSON.

---

## Scalability Design

The service is designed for production scale:

| Feature | Implementation | Cloud equivalent |
|---------|---------------|-----------------|
| **Async jobs** | In-memory queue + background thread | AWS SQS + Lambda |
| **Caching** | In-memory LRU cache (TTL=5min) | AWS ElastiCache (Redis) |
| **Auto-scaling** | Elastic Beanstalk min 2, max 8 instances | AWS ALB + ASG |
| **Multi-worker** | Gunicorn 4 workers per instance | — |
| **Health checks** | `/health` endpoint | ALB health checks |
| **Stateless** | No server-side session state | Ready for horizontal scale |

In production, replace:
- `QueueService._queue` → `boto3.client('sqs')`
- `CacheService._store` → `redis.Redis(host=REDIS_HOST)`

---

## Cloud Deployment (AWS)

```bash
# Make script executable
chmod +x deploy-aws.sh

# Configure AWS credentials first
aws configure

# Deploy
./deploy-aws.sh
```

This script:
1. Deploys the Outfit API to **AWS Elastic Beanstalk** (auto-scaling, min 2 / max 8 instances)
2. Uploads the frontend to **AWS S3** with **CloudFront** CDN

---

## Sharing Your API with Classmates

After deployment, share:

```
Base URL: http://<your-eb-url>
POST     http://<your-eb-url>/api/recommend
GET      http://<your-eb-url>/api/outfits
GET      http://<your-eb-url>/api/info
GET      http://<your-eb-url>/health
```

All endpoints return JSON. CORS is enabled for all origins.

---

## Project Structure

```
weather-outfit-system/
├── backend/                  # Your Outfit Recommendation API
│   ├── app.py                # Flask application + routes
│   ├── outfit_engine.py      # Core recommendation logic
│   ├── queue_service.py      # Async job queue (simulates SQS)
│   ├── cache_service.py      # Response cache (simulates Redis)
│   ├── tests.py              # 28 unit + integration tests
│   ├── requirements.txt
│   └── Dockerfile
│
├── classmate-service/        # Classmate's User Profile API
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   └── index.html            # Single-page app (vanilla JS)
│
├── docker-compose.yml        # Run all services together
├── nginx.conf                # Frontend web server config
├── deploy-aws.sh             # AWS deployment script
└── README.md
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| Framework | Flask 3.0 |
| WSGI Server | Gunicorn (4 workers) |
| Containerisation | Docker + Docker Compose |
| Cloud Platform | AWS (Elastic Beanstalk + S3 + CloudFront) |
| Frontend | Vanilla HTML5/CSS3/JavaScript |
| Public APIs | Open-Meteo (weather + geocoding) |
| Testing | pytest |
