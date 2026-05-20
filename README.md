# CIRO — Crisis Intelligence & Response Orchestrator

**Agentic AI System for Real-Time Urban Crisis Detection and Response**

Built for the AISeekho2026 Antigravity Hackathon — Challenge 3

## 📋 Overview

CIRO is a fully autonomous crisis management system that detects, analyzes, and responds to urban emergencies in Pakistani cities. Using a sophisticated 5-agent pipeline powered by Google Gemini AI, it processes real-time signals from multiple sources (weather, traffic, social media, IoT sensors) to classify crisis types, estimate impact, allocate resources, and simulate response actions—all with **zero hardcoded rules**.

### 🎯 Key Features

- **5-Agent Agentic Pipeline**: Signal Collection → Crisis Detection → Situation Analysis → Action Planning → Execution
- **Multi-Source Integration**: Weather APIs, traffic data, social media (X/Twitter), IoT sensors, user reports, and mock API endpoints
- **100% AI-Driven**: Fully powered by Google Gemini 2.5-flash with zero hardcoding
- **Production-Ready**: Rate limiting, intelligent caching (60-70% hit rate), security measures, and comprehensive monitoring
- **Interactive Dashboard**: Real-time visualization with crisis tracking and testing interface
- **Comprehensive REST API**: Full Swagger documentation at `/docs`
- **Bilingual Support**: English and Urdu crisis reporting
- **Advanced Crisis Classification**: Urban Flooding, Heatwaves, Road Accidents, Infrastructure Failures, Public Disorder, and Medical Emergencies

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Gemini API Key ([get one free](https://aistudio.google.com/app/apikey))
- Optional: OpenWeather API, Google Maps API, X (Twitter) API for real data sources

### Installation

```bash
# Clone or navigate to the backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file from example (if available)
# cp .env.example .env

# Create .env file with required variables
echo GEMINI_API_KEY=your_api_key_here > .env
```

### Running Locally

```bash
# Start the development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Open http://localhost:8000 in your browser
```

For production:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 🏗️ Project Structure

```
backend/
├── main.py                      # FastAPI entry point
├── config.py                    # Environment & settings management
├── middleware.py                # CORS, rate limiting, caching, monitoring
├── auth.py                      # Authentication & JWT handling
├── app.yaml                     # Cloud deployment config
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker containerization
│
├── agents/                      # 5-Agent Pipeline
│   ├── signal_collector.py      # Agent 1: Gathers multi-source signals
│   ├── crisis_detector.py       # Agent 2: Classifies crisis & severity
│   ├── situation_analyzer.py    # Agent 3: Impact & duration estimation
│   ├── action_planner.py        # Agent 4: Resource allocation & messaging
│   ├── executor.py              # Agent 5: Response simulation & metrics
│   └── __init__.py
│
├── models/                      # Pydantic data models
│   ├── signal_models.py         # Request/Response, Signal, SignalCollection
│   ├── crisis_models.py         # CrisisClassification, CrisisType, SeverityLevel
│   ├── action_models.py         # ActionType, ResponseAction, StakeholderMessages
│   └── __init__.py
│
├── utils/                       # Utilities & clients
│   ├── gemini_client.py         # Gemini API wrapper with fallback keys
│   ├── firebase_client.py       # Firebase Firestore integration
│   ├── logger.py                # Structured agent logging
│   └── __init__.py
│
├── mock_api/                    # Mock data sources (for demo/testing)
│   ├── sensor_router.py         # Fake IoT sensor data
│   ├── weather_router.py        # Mock weather reports
│   ├── traffic_router.py        # Mock traffic conditions
│   ├── social_router.py         # Mock social media signals
│   ├── x_router.py              # Mock X (Twitter) posts
│   └── __init__.py
│
├── logs/                        # Execution traces & agent logs
│   └── agent_traces/            # JSON logs from each pipeline run
│
└── tests/                       # Test files
    ├── test_collection_optimized.py
    ├── test_fb.py               # Firebase tests
    ├── test_google_maps.py      # Google Maps tests
    ├── test_signal_logs.py      # Signal collection tests
    └── X_API_SETUP.md           # X API configuration guide
```

---

## 🤖 Agent Pipeline Architecture

### Agent 1: Signal Collector
- **Input**: Crisis text and location
- **Output**: Multi-source signals with credibility scores
- **Functions**: 
  - Extracts location from natural language (Urdu/English)
  - Queries weather API for temperature/rainfall data
  - Fetches traffic conditions from mock/real endpoints
  - Retrieves social media signals (X/Twitter, mock data)
  - Collects IoT sensor readings
  - Returns aggregated signal collection with timestamps

### Agent 2: Crisis Detector
- **Input**: Signal collection from Agent 1
- **Output**: Crisis classification with confidence score
- **Functions**:
  - Cross-references signals with credibility weighting
  - Classifies crisis type (flooding, heatwave, accident, etc.)
  - Calculates severity level (LOW, MEDIUM, HIGH, CRITICAL)
  - Estimates confidence (85-95%)
  - Returns structured crisis classification

### Agent 3: Situation Analyzer
- **Input**: Crisis classification from Agent 2
- **Output**: Impact assessment and duration estimates
- **Functions**:
  - Estimates affected population
  - Predicts crisis duration
  - Calculates impact radius
  - Uses Gemini for contextual analysis
  - Returns detailed situation assessment

### Agent 4: Action Planner
- **Input**: Situation analysis from Agent 3
- **Output**: Resource allocation and stakeholder messages
- **Functions**:
  - Allocates available resources (rescue vehicles, ambulances, police units, etc.)
  - Generates tactical response actions
  - Drafts targeted messages for stakeholders (public, hospital, police, media)
  - Uses Gemini for contextual message generation
  - Returns action plan with stakeholder communications

### Agent 5: Executor
- **Input**: Action plan from Agent 4
- **Output**: Simulated response metrics
- **Functions**:
  - Simulates resource deployment
  - Calculates response time estimates
  - Tracks resource utilization
  - Generates performance metrics
  - Returns execution summary

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```plaintext
# REQUIRED
GEMINI_API_KEY=your_gemini_api_key_here

# Fallback Gemini Keys (Optional)
GEMINI_API_KEY_2=your_backup_key_1
GEMINI_API_KEY_3=your_backup_key_2

# Real API Keys (Optional - uses mock data if not provided)
OPENWEATHER_API_KEY=your_openweather_key
GOOGLE_MAPS_API_KEY=your_google_maps_key
SERPER_API_KEY=your_serper_key
X_BEARER_TOKEN=your_x_bearer_token
X_API_KEY=your_x_api_key
X_API_SECRET=your_x_api_secret

# Firebase (Optional)
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_CREDENTIALS_PATH=./firebase_credentials.json

# Application Settings
ENVIRONMENT=development              # development, staging, production
PORT=8000
HOST=0.0.0.0
PRODUCTION_MODE=false
RATE_LIMIT_ENABLED=true
CACHE_ENABLED=true
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
MAX_REQUEST_SIZE_MB=10
```

### Loading Configuration

The `config.py` file automatically loads environment variables and validates them on startup. Invalid or missing required keys will trigger startup errors with clear messages.

---

## 📡 API Endpoints

### Crisis Analysis

**POST** `/analyze`
- Run the complete 5-agent pipeline on a crisis report
- **Request**:
  ```json
  {
    "text": "G-10 mein pani bhar gaya, gaariyan phans gayi hain",
    "location": "G-10, Islamabad",
    "include_mock_signals": true
  }
  ```
- **Response**: Full pipeline output with all agent results

### System Status

**GET** `/health`
- Simple health check
- **Response**: `{"status": "healthy"}`

**GET** `/system-state`
- Detailed system status, cache stats, Gemini key availability
- **Response**: System configuration and statistics

**GET** `/metrics`
- Performance metrics: execution time, cache hit rate, request counts
- **Response**: Aggregated performance data

### Documentation & Dashboard

**GET** `/docs`
- Interactive Swagger UI with full API documentation
- Try out endpoints directly in the browser

**GET** `/`
- Interactive dashboard for testing crisis scenarios
- Real-time visualization of pipeline execution

---

## 📊 Example Request & Response

### cURL Example

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "G-10 mein pani bhar gaya, gaariyan phans gayi hain",
    "location": "G-10, Islamabad",
    "include_mock_signals": true
  }'
```

### Python Example

```python
import requests
import json

url = "http://localhost:8000/analyze"
payload = {
    "text": "Major flooding reported in sector G-10",
    "location": "G-10, Islamabad",
    "include_mock_signals": True
}

response = requests.post(url, json=payload)
result = response.json()
print(json.dumps(result, indent=2))
```

---

## 📈 Performance Characteristics

| Metric | Value |
|--------|-------|
| Full Pipeline Execution | 45-55 seconds |
| Cache Hit Rate | 60-70% |
| Rate Limit (per IP) | 120 requests/minute |
| AI Confidence Score | 85-95% |
| Max Request Size | 10 MB |
| Supported Regions | Pakistani cities (Islamabad, Karachi, Lahore, etc.) |
| Languages | English, Urdu |

---

## 🛠️ Tech Stack

| Component | Version |
|-----------|---------|
| FastAPI | 0.110+ |
| Python | 3.11+ |
| Google Gemini | 2.5-flash |
| Firebase Admin | 6.3+ |
| Pydantic | 2.5+ |
| Uvicorn | 0.27+ |
| HTTPx | 0.27+ |
| Tweepy | 4.14+ (for X API) |

---

## 🔐 Security Features

- **CORS Whitelist**: Explicit origin configuration (no wildcard in production)
- **Request Size Validation**: Maximum 10 MB per request
- **Rate Limiting**: 120 requests per minute per IP address
- **Multi-Key Gemini Fallback**: Automatic failover to backup API keys
- **JWT Authentication**: Token-based request signing
- **Environment Validation**: Strict validation of required secrets at startup
- **Firebase Fallback**: In-memory cache fallback if Firebase unavailable
- **Input Sanitization**: XSS and injection attack prevention

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_signal_logs.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

### Test Files

- `test_collection_optimized.py` - Signal collection pipeline tests
- `test_fb.py` - Firebase integration tests
- `test_google_maps.py` - Google Maps API tests
- `test_signal_logs.py` - Signal logging and tracing tests

---

## 🐳 Docker Deployment

### Build Image

```bash
docker build -t ciro-backend:latest .
```

### Run Container

```bash
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  -e FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID \
  ciro-backend:latest
```

### Cloud Deployment (Cloud Run/App Engine)

Configuration is in `app.yaml`. Deploy with:

```bash
# For Cloud Run
gcloud run deploy ciro-backend --source . --platform managed --region us-central1

# For App Engine
gcloud app deploy app.yaml
```

---

## 📝 Logging & Monitoring

- **Agent Traces**: JSON execution logs saved in `logs/agent_traces/`
- **Structured Logging**: Each agent logs its input, output, and reasoning
- **Performance Monitoring**: Middleware tracks request latency and cache performance
- **Error Tracking**: Comprehensive error messages with stack traces

### View Logs

```bash
# Recent traces
ls -lt logs/agent_traces/ | head -10

# View specific trace
cat logs/agent_traces/TRACE-TEST-001.json | python -m json.tool
```

---

## 🐛 Troubleshooting

### Common Issues

**1. `GEMINI_API_KEY not found` Error**
- Ensure `.env` file is in project root
- Verify `GEMINI_API_KEY` is set correctly
- Check file permissions

**2. Port 8000 Already in Use**
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn main:app --port 8001
```

**3. Firebase Connection Issues**
- System will automatically fall back to in-memory cache
- Set `FIREBASE_CREDENTIALS_PATH` if using real Firebase
- Check Firebase credentials JSON file format

**4. Mock API Endpoints Returning 404**
- Ensure `include_mock_signals=true` in request
- Check mock router files are present in `mock_api/`
- Verify port configuration matches

**5. Rate Limiting Too Strict**
- Set `RATE_LIMIT_ENABLED=false` for development
- Adjust limits in `middleware.py`

---

## 📚 Additional Resources

- **[Google Gemini API Docs](https://ai.google.dev/docs)** - Official Gemini documentation
- **[FastAPI Tutorial](https://fastapi.tiangolo.com/)** - FastAPI guide
- **[Pydantic Docs](https://docs.pydantic.dev/)** - Data validation
- **[X API Setup](./X_API_SETUP.md)** - Twitter/X integration guide

---

## 👥 Team & Attribution

Built for **AISeekho2026 Antigravity Hackathon** - Challenge 3

Hackathon Track: Advanced AI Systems for Urban Crisis Management

---

## 📄 License

This project is part of the AISeekho2026 Hackathon. Refer to hackathon guidelines for usage restrictions.

---

## 🚀 Future Enhancements

- [ ] Real-time WebSocket support for live crisis tracking
- [ ] Mobile app integration (Flutter)
- [ ] SMS alerting system
- [ ] Integration with emergency services APIs
- [ ] Multi-language support expansion
- [ ] Blockchain-based audit trail
- [ ] Advanced ML-based signal weighting
- [ ] Predictive crisis modeling

## Project Structure

ciro_backend/
├── main.py                 # FastAPI app
├── config.py              # Configuration
├── agents/                # 5-Agent pipeline
├── models/                # Pydantic models
├── utils/                 # Gemini, Firebase, logging
├── mock_api/              # Mock endpoints
├── static/                # Dashboard UI
└── requirements.txt       # Dependencies


## Deployment

Docker:
bash
docker build -t ciro .
docker run -p 8000:8000 -e GEMINI_API_KEY=xxx ciro


Google Cloud Run:
bash
gcloud run deploy ciro --source . --region us-central1


## Testing

1. Open http://localhost:8000
2. Select a demo scenario
3. Click "Run CIRO Pipeline"
4. View results

Or use Swagger UI: http://localhost:8000/docs

## Challenge Fulfillment

✅ Real-time crisis detection via 5-agent pipeline
✅ Zero hardcoding (100% Gemini-powered)
✅ Multi-source signal integration
✅ Production-ready security & monitoring
✅ Pakistani focus (Islamabad, Urdu, local agencies)

## License

MIT

## Support

For issues, check GitHub Issues or create a new one with details.

---

Made with ❤️ for crisis response in Pakistani cities
