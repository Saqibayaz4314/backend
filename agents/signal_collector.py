"""
Agent 1 — Signal Collector (Production-Ready)
================================================
Ingests raw crisis text, extracts location via Gemini, and calls mock API endpoints
to gather multi-source signals with credibility scores.

Pipeline position: FIRST — feeds into CrisisDetector (Agent 2).

Dependencies:
    - GeminiClient (utils/gemini_client.py)
    - AgentLogger  (utils/logger.py)
    - httpx        (async HTTP client)
"""

import time
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Optional
import os

import httpx

from config import settings
from models.signal_models import AnalyzeRequest, Signal, SignalCollection, SignalSource
from utils.gemini_client import GeminiClient
from utils.logger import AgentLogger


# ─────────────────────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_area(location: str) -> str:
    """Normalize location string to area code."""
    normalized = location.lower().replace("-", "").replace(",", "").strip().split()[0]
    return normalized


def _extract_city_for_weather(location: str) -> str:
    """Extract city name from location for weather API."""
    parts = location.split(",")
    if len(parts) > 1:
        return parts[1].strip()
    words = location.split()
    return words[-1] if words else location


def _get_mock_base_url() -> str:
    """Get mock API base URL from config."""
    host = os.getenv("HOST", settings.host)
    port = os.getenv("PORT", str(settings.port))
    if host == "0.0.0.0":
        host = "127.0.0.1"
    return f"http://{host}:{port}"


def _now_ms() -> int:
    """Return current time in milliseconds."""
    return int(time.time() * 1000)


_MOCK_BASE_URL = _get_mock_base_url()


# ─────────────────────────────────────────────────────────────────────────────
# Signal Collector Class
# ─────────────────────────────────────────────────────────────────────────────

class SignalCollector:
    """Agent 1: Collects crisis signals from multiple sources."""

    def __init__(self, gemini_client: GeminiClient) -> None:
        """Initialize with GeminiClient."""
        self.gemini = gemini_client

    async def collect(
        self,
        request: AnalyzeRequest,
        logger: AgentLogger,
    ) -> SignalCollection:
        """
        Collect signals from all available sources.
        
        Wraps collection with timeout to prevent hanging.
        """
        try:
            return await asyncio.wait_for(
                self._do_collect(request, logger),
                timeout=settings.signal_collection_timeout
            )
        except asyncio.TimeoutError:
            logger.log_agent_step(
                agent_name="agent_1_signal_collector",
                step="Signal Collection",
                input_data=request.text,
                output_data="TIMEOUT - Fallback to user signal only",
                duration_ms=settings.signal_collection_timeout * 1000,
                extra_data={"error": "Signal collection exceeded timeout"},
            )
            # Return minimal collection with user signal only
            return SignalCollection(
                signals=[Signal(
                    source=SignalSource.SOCIAL_MEDIA,
                    text=request.text,
                    credibility=0.65,
                    timestamp=datetime.now(timezone.utc),
                    location=request.location or "unknown",
                    metadata={"origin": "timeout_fallback"},
                )],
                area=request.location or "unknown",
                total_count=1,
                collection_time_ms=settings.signal_collection_timeout * 1000,
            )

    async def _do_collect(
        self,
        request: AnalyzeRequest,
        logger: AgentLogger,
    ) -> SignalCollection:
        """Internal collect method."""
        start_ms = _now_ms()
        signals: list[Signal] = []
        sources_checked: list[str] = []
        errors: list[str] = []

        # Extract location
        detected_location = request.location or "islamabad"
        area_code = _normalize_area(detected_location)

        # Add user's signal
        signals.append(Signal(
            source=SignalSource.SOCIAL_MEDIA,
            text=request.text,
            credibility=0.65,
            timestamp=datetime.now(timezone.utc),
            location=detected_location,
            metadata={"origin": "user_input"},
        ))

        # Collect from APIs
        if request.include_mock_signals:
            try:
                async with httpx.AsyncClient(
                    base_url=_MOCK_BASE_URL,
                    timeout=float(settings.http_client_timeout),
                ) as client:
                    # Weather
                    try:
                        weather_resp = await client.get(
                            f"{_MOCK_BASE_URL}/mock/weather",
                            params={"city": _extract_city_for_weather(detected_location)}
                        )
                        if weather_resp.status_code == 200:
                            weather_data = weather_resp.json()
                            signals.append(Signal(
                                source=SignalSource.WEATHER_API,
                                text=f"Weather: {weather_data.get('condition', 'UNKNOWN')}",
                                credibility=0.85,
                                timestamp=datetime.now(timezone.utc),
                                location=detected_location,
                                metadata=weather_data,
                            ))
                    except Exception as e:
                        errors.append(f"Weather API failed: {e}")
                    
                    sources_checked.append("weather")

                    # Traffic
                    try:
                        traffic_resp = await client.get(
                            f"{_MOCK_BASE_URL}/mock/traffic",
                            params={"area": area_code}
                        )
                        if traffic_resp.status_code == 200:
                            traffic_data = traffic_resp.json()
                            congestion = traffic_data.get('congestion_level', 0)
                            is_real = traffic_data.get('is_real', False)
                            source_label = "Google Maps Real-Time" if is_real else "Traffic Intelligence"

                            # Build enriched traffic text with route info
                            route_details = []
                            for route in traffic_data.get('routes', []):
                                dest = route.get('destination', 'Unknown')
                                dur_normal = route.get('duration_normal', 'N/A')
                                dur_traffic = route.get('duration_in_traffic', 'N/A')
                                dist = route.get('distance', 'N/A')
                                route_details.append(
                                    f"Route to {dest}: {dist}, normal={dur_normal}, with traffic={dur_traffic}"
                                )

                            traffic_text = f"Traffic [{source_label}]: congestion {congestion}/10"
                            if route_details:
                                traffic_text += ". Routes: " + "; ".join(route_details)
                            if traffic_data.get('blocked_routes'):
                                traffic_text += f". Blocked: {', '.join(traffic_data['blocked_routes'])}"

                            signals.append(Signal(
                                source=SignalSource.TRAFFIC_API,
                                text=traffic_text,
                                credibility=0.95 if is_real else 0.80,
                                timestamp=datetime.now(timezone.utc),
                                location=detected_location,
                                metadata=traffic_data,
                            ))
                    except Exception as e:
                        errors.append(f"Traffic API failed: {e}")
                    
                    sources_checked.append("traffic")

                    # Sensors
                    try:
                        sensor_resp = await client.get(
                            f"{_MOCK_BASE_URL}/mock/sensors",
                            params={"area": area_code}
                        )
                        if sensor_resp.status_code == 200:
                            sensor_data = sensor_resp.json()
                            signals.append(Signal(
                                source=SignalSource.SENSOR,
                                text=f"Sensors: water level {sensor_data.get('water_level_cm', 0)}cm",
                                credibility=0.88,
                                timestamp=datetime.now(timezone.utc),
                                location=detected_location,
                                metadata=sensor_data,
                            ))
                    except Exception as e:
                        errors.append(f"Sensor API failed: {e}")
                    
                    sources_checked.append("sensors")

                    # Social Media Signals
                    try:
                        social_resp = await client.get(
                            f"{_MOCK_BASE_URL}/mock/social",
                            params={"area": area_code}
                        )
                        if social_resp.status_code == 200:
                            social_data = social_resp.json()
                            social_signals = social_data.get('signals', [])
                            
                            if social_signals:
                                for signal in social_signals:
                                    signals.append(Signal(
                                        source=SignalSource.SOCIAL_MEDIA,
                                        text=signal.get('text', ''),
                                        credibility=signal.get('credibility', 0.65),
                                        timestamp=datetime.now(timezone.utc),
                                        location=detected_location,
                                        metadata={
                                            "language": signal.get('language', 'unknown'),
                                            "mention_velocity": signal.get('mention_velocity', 0),
                                            "source": social_data.get('source', 'Social Media Monitor'),
                                        },
                                    ))
                    except Exception as e:
                        errors.append(f"Social Media API failed: {e}")
                    
                    sources_checked.append("social_media")

                    # X (Twitter) API for real-time crisis signals
                    try:
                        x_resp = await client.get(
                            f"{_MOCK_BASE_URL}/mock/x-social",
                            params={"area": area_code}
                        )
                        if x_resp.status_code == 200:
                            x_data = x_resp.json()
                            x_signals = x_data.get('signals', [])
                            
                            if x_signals:
                                for signal in x_signals:
                                    signals.append(Signal(
                                        source=SignalSource.SOCIAL_MEDIA,
                                        text=signal.get('text', ''),
                                        credibility=signal.get('credibility', 0.70),
                                        timestamp=datetime.now(timezone.utc),
                                        location=detected_location,
                                        metadata={
                                            "language": signal.get('language', 'unknown'),
                                            "mention_velocity": signal.get('mention_velocity', 0),
                                            "retweet_count": signal.get('retweet_count', 0),
                                            "like_count": signal.get('like_count', 0),
                                            "engagement_score": signal.get('engagement_score', 0),
                                            "tweet_id": signal.get('tweet_id', ''),
                                            "origin": "x_api",
                                            "source": x_data.get('source', 'X API Feed'),
                                        },
                                    ))
                    except Exception as e:
                        errors.append(f"X API failed: {e}")
                    
                    sources_checked.append("x_api")

                    # X/Twitter API for live social signals
                    try:
                        x_signals = await self._fetch_x_social_signals(
                            client=client,
                            user_text=request.text,
                            location=detected_location,
                        )
                        signals.extend(x_signals)
                    except Exception as e:
                        errors.append(f"X/Twitter API failed: {e}")

                    sources_checked.append("x_twitter")

            except Exception as e:
                errors.append(f"API collection failed: {e}")

        # Calculate weighted score
        weighted_score = round(
            sum(s.credibility for s in signals) / len(signals), 2
        ) if signals else 0.0

        # Log and return
        elapsed_ms = _now_ms() - start_ms
        
        logger.log_agent_step(
            agent_name="agent_1_signal_collector",
            step="Signal Collection - COMPLETE",
            input_data=request.text,
            output_data=f"{len(signals)} total signals from {len(sources_checked)} sources",
            duration_ms=elapsed_ms,
            extra_data={
                "sources_checked": sources_checked,
                "signals_found": len(signals),
                "credibility_score": weighted_score,
                "errors": errors if errors else None,
                "location": detected_location,
                "user_signal_included": True,
                "detailed_breakdown": {
                    "weather": len([s for s in signals if s.source == SignalSource.WEATHER_API]),
                    "traffic": len([s for s in signals if s.source == SignalSource.TRAFFIC_API]),
                    "sensors": len([s for s in signals if s.source == SignalSource.SENSOR]),
                    "social_media": len([s for s in signals if s.source == SignalSource.SOCIAL_MEDIA]),
                },
            },
        )

        return SignalCollection(
            signals=signals,
            area=detected_location,
            total_count=len(signals),
            collection_time_ms=elapsed_ms,
        )


    async def _fetch_x_social_signals(
        self,
        client: httpx.AsyncClient,
        user_text: str,
        location: str,
    ) -> list[Signal]:
        """
        Fetch recent tweets from X API and convert them into Signal objects.
        Uses bearer token from X_BEARER_TOKEN (or X_API_KEY fallback).
        """
        token = settings.x_bearer_token or settings.x_api_key
        if not token:
            return []

        query = f"({location}) ({user_text}) lang:en -is:retweet"
        headers = {
            "Authorization": f"Bearer {token}",
        }
        params = {
            "query": query[:512],
            "max_results": 10,
            "tweet.fields": "created_at,lang,public_metrics",
        }

        try:
            response = await client.get(
                "https://api.x.com/2/tweets/search/recent",
                headers=headers,
                params=params,
                timeout=10.0,
            )
            response.raise_for_status()
        except Exception:
            # Backward-compatible endpoint
            response = await client.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers=headers,
                params=params,
                timeout=10.0,
            )
            response.raise_for_status()
        data = response.json()
        tweets = data.get("data", []) or []

        out: list[Signal] = []
        for tweet in tweets[:3]:
            text = (tweet.get("text") or "").strip()
            if not text:
                continue

            metrics = tweet.get("public_metrics", {}) or {}
            like_count = int(metrics.get("like_count", 0) or 0)
            rt_count = int(metrics.get("retweet_count", 0) or 0)
            velocity = like_count + (2 * rt_count)
            credibility = 0.58 if velocity < 20 else 0.66

            out.append(
                Signal(
                    source=SignalSource.SOCIAL_MEDIA,
                    text=f"X Post: {text[:450]}",
                    credibility=credibility,
                    timestamp=datetime.now(timezone.utc),
                    location=location,
                    metadata={
                        "origin": "x_recent_search",
                        "tweet_id": tweet.get("id"),
                        "language": tweet.get("lang"),
                        "mention_velocity": velocity,
                    },
                )
            )

        return out
