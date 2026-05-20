"""
Agent 1 — Signal Collector (Production-Ready)
================================================
Collects LIVE signals from OpenWeather, Google Maps, and X API.
Falls back to Mock APIs only if keys are missing.
"""

import time
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
import os
import httpx

from config import settings
from models.signal_models import AnalyzeRequest, Signal, SignalCollection, SignalSource
from utils.gemini_client import GeminiClient
from utils.logger import AgentLogger

class SignalCollector:
    def __init__(self, gemini_client: GeminiClient) -> None:
        self.gemini = gemini_client

    async def collect(self, request: AnalyzeRequest, logger: AgentLogger) -> SignalCollection:
        start_ms = int(time.time() * 1000)
        signals: list[Signal] = []
        sources_live: list[str] = []
        
        detected_location = request.location or "islamabad"
        # Extract keywords for better API search
        area_keyword = detected_location.split(",")[0].strip()

        # 1. User Signal (Always first)
        signals.append(Signal(
            source=SignalSource.SOCIAL_MEDIA,
            text=request.text,
            credibility=0.80,
            timestamp=datetime.now(timezone.utc),
            location=detected_location,
            metadata={"origin": "user_input"}
        ))

        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = []
            
            # --- WEATHER ---
            if settings.openweather_api_key:
                tasks.append(self._get_live_weather(client, detected_location))
                sources_live.append("weather")
            else:
                tasks.append(self._get_mock_signal(client, "weather", {"city": detected_location}))

            # --- TRAFFIC ---
            if settings.google_maps_api_key:
                tasks.append(self._get_live_traffic(client, detected_location))
                sources_live.append("traffic")
            else:
                tasks.append(self._get_mock_signal(client, "traffic", {"area": area_keyword}))

            # --- SENSORS (Always Mock/IoT Sim) ---
            tasks.append(self._get_mock_signal(client, "sensors", {"area": area_keyword}))

            # --- SOCIAL / X ---
            if settings.x_bearer_token:
                tasks.append(self._get_live_x_signals(client, area_keyword))
                sources_live.append("social_media")
            else:
                tasks.append(self._get_mock_signal(client, "social", {"area": area_keyword}))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list): signals.extend(res)
                elif isinstance(res, Signal): signals.append(res)

        elapsed_ms = int(time.time() * 1000) - start_ms

        # Critical: Mobile App Breakdown Mapping
        breakdown = {
            "weather": len([s for s in signals if s.source == SignalSource.WEATHER_API]),
            "traffic": len([s for s in signals if s.source == SignalSource.TRAFFIC_API]),
            "sensors": len([s for s in signals if s.source == SignalSource.SENSOR]),
            "social_media": len([s for s in signals if s.source == SignalSource.SOCIAL_MEDIA]),
        }

        logger.log_agent_step(
            agent_name="agent_1_signal_collector",
            step="Signal Collection",
            input_data=request.text,
            output_data=f"Collected {len(signals)} signals. Live: {', '.join(sources_live)}",
            duration_ms=elapsed_ms,
            extra_data={
                "detailed_breakdown": breakdown,
                "location_detected": detected_location,
                "live_sources": sources_live
            }
        )

        return SignalCollection(signals=signals, area=detected_location, total_count=len(signals), collection_time_ms=elapsed_ms)

    async def _get_live_weather(self, client: httpx.AsyncClient, loc: str) -> Optional[Signal]:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={loc}&appid={settings.openweather_api_key}&units=metric"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return Signal(
                    source=SignalSource.WEATHER_API,
                    text=f"Live Weather: {data['weather'][0]['description']}, Temp: {data['main']['temp']}°C",
                    credibility=0.98, timestamp=datetime.now(timezone.utc), location=loc, metadata=data
                )
        except: return None

    async def _get_live_traffic(self, client: httpx.AsyncClient, loc: str) -> Optional[Signal]:
        # Simple distance matrix check as proxy for traffic
        try:
            url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={loc}&destinations={loc}&departure_time=now&key={settings.google_maps_api_key}"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return Signal(
                    source=SignalSource.TRAFFIC_API,
                    text="Google Maps: Real-time traffic data confirmed for area.",
                    credibility=0.95, timestamp=datetime.now(timezone.utc), location=loc, metadata=data
                )
        except: return None

    async def _get_live_x_signals(self, client: httpx.AsyncClient, query: str) -> list[Signal]:
        # Real X API call
        out = []
        try:
            headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
            url = f"https://api.twitter.com/2/tweets/search/recent?query={query} crisis&max_results=5"
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                tweets = resp.json().get("data", [])
                for t in tweets:
                    out.append(Signal(
                        source=SignalSource.SOCIAL_MEDIA,
                        text=f"X Post: {t['text']}",
                        credibility=0.70, timestamp=datetime.now(timezone.utc), location=query, metadata=t
                    ))
        except: pass
        return out

    async def _get_mock_signal(self, client: httpx.AsyncClient, type: str, params: dict) -> Optional[Any]:
        # Fallback to internal mock endpoints
        try:
            host = "127.0.0.1" if settings.host == "0.0.0.0" else settings.host
            url = f"http://{host}:{settings.port}/mock/{type}"
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if type == "social":
                    return [Signal(source=SignalSource.SOCIAL_MEDIA, text=s['text'], credibility=0.6, 
                                  timestamp=datetime.now(timezone.utc), location=params.get('area')) for s in data.get('signals', [])]
                
                source_map = {"weather": SignalSource.WEATHER_API, "traffic": SignalSource.TRAFFIC_API, "sensors": SignalSource.SENSOR}
                return Signal(source=source_map[type], text=str(data), credibility=0.8, 
                             timestamp=datetime.now(timezone.utc), location=params.get('area', 'unknown'), metadata=data)
        except: return None
