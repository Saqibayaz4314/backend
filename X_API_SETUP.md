# X (Twitter) API Integration Setup Guide

## ✅ Status
- X API router created and tested ✅
- Signal collector integrated ✅  
- Mock signals working ✅
- tweepy installed ✅

## 🔑 Adding Real X API Credentials

### Step 1: Get X API Credentials
1. Go to [Twitter Developer Portal](https://developer.twitter.com)
2. Create an app in the Developer Dashboard
3. Under "Keys & tokens", copy:
   - **API Key** → `X_API_KEY`
   - **API Secret** → `X_API_SECRET`
   - **Bearer Token** → `X_BEARER_TOKEN` ⭐ (MOST IMPORTANT - minimum for read-only access)
   - **Access Token** → `X_ACCESS_TOKEN`
   - **Access Token Secret** → `X_ACCESS_TOKEN_SECRET`

### Step 2: Add to `.env` File
Edit `backend/.env` and add these lines:

```bash
# X (Twitter) API Configuration
X_API_KEY=your_api_key_here
X_API_SECRET=your_api_secret_here
X_BEARER_TOKEN=your_bearer_token_here
X_ACCESS_TOKEN=your_access_token_here
X_ACCESS_TOKEN_SECRET=your_access_token_secret_here
```

**For minimal setup (read-only):** Only `X_BEARER_TOKEN` is needed.

### Step 3: Test Real API
Once you add credentials, the system will automatically:
1. Use mock signals by default (safe testing)
2. Switch to real X API when `use_real=true` is passed to the endpoint

Example API call:
```bash
# Mock signals (always works)
curl "http://localhost:8000/mock/x-social?area=g10&use_real=false"

# Real X API (if credentials provided)
curl "http://localhost:8000/mock/x-social?area=g10&use_real=true"
```

## 📍 Crisis Keywords Monitored
The system searches for:
- **Flood**: "flood", "pani bhar", "waterlogged", "blocked road"
- **Heatwave**: "heatwave", "heatstroke", "garmi", "temperature"
- **Accidents**: "accident", "crash", "traffic jam"
- **Blockages**: "blockage", "blocked", "jammed"

## 🔄 How Signal Collection Works

### Flow:
```
User Report (crisis text)
       ↓
Signal Collector Agent (Agent 1)
       ↓
   ├─ Weather API (Mock/Real)
   ├─ Traffic API (Google Maps)
   ├─ Social Media (Mock)
   ├─ X (Twitter) API ⭐ NEW
   ├─ Sensors (Mock)
   └─ Google Search (Serper) - optional
       ↓
   Signal Aggregation (7-50 signals with credibility scores)
       ↓
   Crisis Detector (Agent 2) → Severity Analysis
```

### X API Integration Points:
1. **Mock endpoint**: `/mock/x-social?area=g10`
   - Returns test signals immediately
   - No credentials needed
   - Perfect for development/testing

2. **Real endpoint**: 
   - Same endpoint with `use_real=true`
   - Searches live X for crisis keywords
   - Requires Bearer Token in `.env`
   - Graceful fallback to mock if auth fails

## 📊 Signal Format from X API
```json
{
  "text": "Tweet content...",
  "language": "english/hinglish",
  "timestamp": "2026-05-20T10:30:00Z",
  "credibility": 0.75,
  "mention_velocity": 8,
  "retweet_count": 245,
  "like_count": 418,
  "engagement_score": 0.82,
  "tweet_id": "1234567890",
  "author": "@username"
}
```

## 🧪 Testing Without Credentials
Currently, mock signals work perfectly:
- G-10 area returns 3 flood signals
- F-8 area returns 2 heatwave signals
- Credibility scores: 0.60-0.78
- Engagement metrics: automatically generated

**No credentials needed to test!** Just run the server and use `/mock/x-social` endpoint.

## 🚀 Deployment Notes
- Mock signals active by default (safe)
- Real API only activates with credentials
- If X credentials unavailable → falls back to mock
- No breaking changes if X API key is missing
- Supports graceful degradation

## 🐛 Troubleshooting

### "tweepy not installed" error
```bash
cd backend
pip install tweepy>=4.14.0
```

### "X_BEARER_TOKEN not found" in logs
- This is normal! Just means real X API not configured
- System automatically uses mock signals
- No action needed unless you want real-time X data

### "X API failed" error in logs
- Check Bearer Token is valid in `.env`
- Verify API credentials from Twitter Developer Dashboard
- System automatically falls back to mock signals

### Signals not updating
- Check Signal Collector logs in `/logs/` directory
- Verify `/mock/x-social` endpoint is responding
- Check if `include_mock_signals=true` in request

## ✨ Next Steps
1. **Optional**: Add X Bearer Token to `.env` for real-time signals
2. Run backend: `python main.py`
3. Test signals: `curl http://localhost:8000/mock/x-social?area=g10`
4. Check integration logs in agent response

---
**AISeekho 2026 — CIRO Crisis Intelligence System**
