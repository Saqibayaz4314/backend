"""
X (Twitter) API Router — Real & Mock Implementation
=================================================
Handles real-time signal collection from X API with fallback to mock data.
Supports both v2 API (Bearer Token) and can be extended to v1.1.

Integration: Signal Collector calls this endpoint to get real-time crisis signals
from Twitter/X for specified locations and keywords.
"""

from datetime import datetime, timezone
from typing import Optional, List
import os
from fastapi import APIRouter, Query
import tweepy

router = APIRouter()

# Import config for X API credentials
try:
    from config import settings
    X_BEARER_TOKEN = settings.x_bearer_token
    X_API_KEY = settings.x_api_key
    X_API_SECRET = settings.x_api_secret
    X_ACCESS_TOKEN = settings.x_access_token
    X_ACCESS_TOKEN_SECRET = settings.x_access_token_secret
except:
    X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
    X_API_KEY = os.getenv("X_API_KEY")
    X_API_SECRET = os.getenv("X_API_SECRET")
    X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
    X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")


def _get_x_client():
    """Initialize X API client with bearer token (v2 API)."""
    if X_BEARER_TOKEN:
        try:
            client = tweepy.Client(bearer_token=X_BEARER_TOKEN)
            return client
        except Exception as e:
            print(f"X API initialization failed: {e}")
            return None
    return None


def _get_mock_x_signals(area: str) -> dict:
    """Returns mock X signals for testing without real credentials."""
    area_lower = area.lower().replace("-", "").strip()
    timestamp = datetime.now(timezone.utc).isoformat()

    mock_data = {
        "g10": {
            "area": "G-10",
            "signals": [
                {
                    "text": "G-10 mein pani bhar gaya! Multiple reports of flooding on Margalla Road. Gaariyan pans gayi hain. Avoid the area! #Flood #IslamabadEmergency",
                    "language": "hinglish",
                    "timestamp": timestamp,
                    "credibility": 0.78,
                    "mention_velocity": 12,
                    "retweet_count": 245,
                    "like_count": 418,
                    "engagement_score": 0.82,
                    "tweet_id": "mock_x_001",
                    "author": "@crisisreporter_pk",
                },
                {
                    "text": "BREAKING: Heavy rainfall causing major waterlogging in G-10, Islamabad. Roads are blocked. Emergency services on alert. Stay safe! 🚨",
                    "language": "english",
                    "timestamp": timestamp,
                    "credibility": 0.75,
                    "mention_velocity": 8,
                    "retweet_count": 167,
                    "like_count": 289,
                    "engagement_score": 0.76,
                    "tweet_id": "mock_x_002",
                    "author": "@IslamabadMetro",
                },
                {
                    "text": "Margalla Road G-10 completely submerged. Traffic jammed for 2+ hours. Official help needed ASAP. 🔴",
                    "language": "english",
                    "timestamp": timestamp,
                    "credibility": 0.70,
                    "mention_velocity": 6,
                    "retweet_count": 89,
                    "like_count": 156,
                    "engagement_score": 0.68,
                    "tweet_id": "mock_x_003",
                    "author": "@LocalNewsPK",
                },
            ],
            "total_mentions": 34,
            "dominant_keyword": "flood",
            "source": "X API Mock Feed",
        },
        "f8": {
            "area": "F-8",
            "signals": [
                {
                    "text": "F-8 bohat zyada garmi ho rahi hai! Temperature cross kar gaya 48°C. Multiple heatstroke cases reported. Drink water, stay indoors! 🌡️ #HeatWave",
                    "language": "hinglish",
                    "timestamp": timestamp,
                    "credibility": 0.76,
                    "mention_velocity": 9,
                    "retweet_count": 201,
                    "like_count": 367,
                    "engagement_score": 0.79,
                    "tweet_id": "mock_x_004",
                    "author": "@HealthAlertPK",
                },
                {
                    "text": "HEATWAVE ALERT: F-8, Islamabad recording dangerous temperatures. Emergency response activated. Avoid outdoor activities.",
                    "language": "english",
                    "timestamp": timestamp,
                    "credibility": 0.73,
                    "mention_velocity": 7,
                    "retweet_count": 134,
                    "like_count": 223,
                    "engagement_score": 0.71,
                    "tweet_id": "mock_x_005",
                    "author": "@IslamabadDMO",
                },
            ],
            "total_mentions": 18,
            "dominant_keyword": "heatwave",
            "source": "X API Mock Feed",
        },
    }

    # Return mock data if area matches, otherwise return empty
    for key in mock_data:
        if key in area_lower:
            return mock_data[key]

    return {
        "area": area,
        "signals": [],
        "total_mentions": 0,
        "dominant_keyword": "",
        "source": "X API Mock Feed",
        "data_available": False,
        "note": f"Mock data not configured for area '{area}'. Returning empty signals.",
    }


def _search_x_real(area: str, keywords: Optional[List[str]] = None) -> dict:
    """
    Search real X API for crisis signals.
    
    Keywords to search:
    - flood, flooding, pani bhar gaya, waterlogged, blocked road
    - heatwave, heatstroke, garmi, temperature
    - accident, crash, traffic jam
    """
    if not keywords:
        keywords = [
            "flood OR pani bhar",
            "heatwave OR heatstroke",
            "accident OR crash",
            "blockage OR blocked",
        ]

    client = _get_x_client()
    if not client:
        return _get_mock_x_signals(area)

    signals = []
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        for keyword in keywords:
            # Construct search query with area and keyword
            query = f'"{area}" ({keyword}) -is:retweet lang:en OR lang:ur'
            
            # Search tweets (v2 API)
            tweets = client.search_recent_tweets(
                query=query,
                max_results=10,
                tweet_fields=["created_at", "public_metrics"],
                user_fields=["username"],
                expansions=["author_id"],
            )

            if tweets.data:
                users = {user.id: user.username for user in tweets.includes["users"]}
                
                for tweet in tweets.data:
                    metrics = tweet.public_metrics or {}
                    # Calculate credibility from engagement
                    engagement = (
                        metrics.get("retweet_count", 0) * 0.3
                        + metrics.get("like_count", 0) * 0.2
                        + metrics.get("reply_count", 0) * 0.1
                    )
                    # Normalize credibility (0.4 - 0.95)
                    credibility = min(0.95, max(0.4, 0.4 + (engagement / 500)))
                    mention_velocity = metrics.get("retweet_count", 0) + metrics.get("like_count", 0)

                    signals.append({
                        "text": tweet.text,
                        "language": "english",  # Can be enhanced with language detection
                        "timestamp": timestamp,
                        "credibility": round(credibility, 2),
                        "mention_velocity": min(mention_velocity, 100),  # Normalized
                        "retweet_count": metrics.get("retweet_count", 0),
                        "like_count": metrics.get("like_count", 0),
                        "engagement_score": round(credibility, 2),
                        "tweet_id": tweet.id,
                        "author": f"@{users.get(tweet.author_id, 'unknown')}",
                    })

        if signals:
            return {
                "area": area,
                "signals": signals[:15],  # Return top 15 signals
                "total_mentions": len(signals),
                "dominant_keyword": "mixed_crisis_indicators",
                "source": "X API Real Feed",
                "data_available": True,
            }

    except Exception as e:
        print(f"X API search failed: {e}")
        return _get_mock_x_signals(area)

    # Fallback to mock if no results
    return _get_mock_x_signals(area)


@router.get("/x-social", summary="Get real-time signals from X (Twitter)")
async def get_x_signals(
    area: str = Query("g10", description="Area code (e.g., g10, f8)"),
    use_real: bool = Query(False, description="Use real X API if credentials available"),
):
    """
    Get crisis signals from X (Twitter) for specified area.
    
    - If `use_real=true` and X credentials configured: Uses real X API
    - Otherwise: Returns mock signals for testing
    
    Supports keywords: flood, heatwave, accident, blockage, traffic
    Returns signals with credibility scores and engagement metrics.
    """
    if use_real and X_BEARER_TOKEN:
        # Try real X API
        result = _search_x_real(area)
    else:
        # Mock signals
        result = _get_mock_x_signals(area)

    return result


@router.get("/x-social/mock", summary="Get mock X signals (test endpoint)")
async def get_x_mock(area: str = Query("g10", description="Area code")):
    """Force mock data (for testing without real credentials)."""
    return _get_mock_x_signals(area)
