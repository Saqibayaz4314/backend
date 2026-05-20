"""
Traffic Router — Google Maps Directions API Integration
=========================================================
Provides real-time traffic and route data for crisis management.
Uses Google Maps Directions API when available, falls back to mock data.
"""

import os
from datetime import datetime, timezone
from fastapi import APIRouter, Query
import httpx

router = APIRouter()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# ─────────────────────────────────────────────────────────────────────
# Islamabad Sector Coordinates (lat, lng)
# ─────────────────────────────────────────────────────────────────────
LOCATION_COORDS = {
    # Major sectors
    "g10":  {"lat": 33.6844, "lng": 73.0479, "name": "G-10, Islamabad"},
    "g-10": {"lat": 33.6844, "lng": 73.0479, "name": "G-10, Islamabad"},
    "f8":   {"lat": 33.7100, "lng": 73.0551, "name": "F-8, Islamabad"},
    "f-8":  {"lat": 33.7100, "lng": 73.0551, "name": "F-8, Islamabad"},
    "g6":   {"lat": 33.7294, "lng": 73.0831, "name": "G-6, Islamabad"},
    "g-6":  {"lat": 33.7294, "lng": 73.0831, "name": "G-6, Islamabad"},
    "i8":   {"lat": 33.6938, "lng": 73.0734, "name": "I-8, Islamabad"},
    "i-8":  {"lat": 33.6938, "lng": 73.0734, "name": "I-8, Islamabad"},
    "f6":   {"lat": 33.7200, "lng": 73.0600, "name": "F-6, Islamabad"},
    "f-6":  {"lat": 33.7200, "lng": 73.0600, "name": "F-6, Islamabad"},
    "g9":   {"lat": 33.6925, "lng": 73.0425, "name": "G-9, Islamabad"},
    "g-9":  {"lat": 33.6925, "lng": 73.0425, "name": "G-9, Islamabad"},
    "e11":  {"lat": 33.7066, "lng": 73.0014, "name": "E-11, Islamabad"},
    "e-11": {"lat": 33.7066, "lng": 73.0014, "name": "E-11, Islamabad"},
    "h9":   {"lat": 33.6800, "lng": 73.0500, "name": "H-9, Islamabad"},
    "h-9":  {"lat": 33.6800, "lng": 73.0500, "name": "H-9, Islamabad"},
    "blue area": {"lat": 33.7300, "lng": 73.0800, "name": "Blue Area, Islamabad"},
    # Other major cities
    "lahore":  {"lat": 31.5204, "lng": 74.3587, "name": "Lahore"},
    "karachi": {"lat": 24.8607, "lng": 67.0011, "name": "Karachi"},
    "rawalpindi": {"lat": 33.5651, "lng": 73.0169, "name": "Rawalpindi"},
    "lyari":   {"lat": 24.8615, "lng": 67.0099, "name": "Lyari, Karachi"},
}

# ─────────────────────────────────────────────────────────────────────
# Nearby destinations for route calculation (hospitals, stations)
# ─────────────────────────────────────────────────────────────────────
EMERGENCY_DESTINATIONS = {
    "islamabad": [
        {"name": "PIMS Hospital", "lat": 33.6945, "lng": 73.0478},
        {"name": "Shifa International Hospital", "lat": 33.6632, "lng": 73.0582},
        {"name": "Pakistan Institute of Medical Sciences", "lat": 33.6945, "lng": 73.0478},
    ],
    "karachi": [
        {"name": "Jinnah Hospital", "lat": 24.8630, "lng": 67.0341},
        {"name": "Civil Hospital", "lat": 24.8603, "lng": 67.0100},
    ],
    "lahore": [
        {"name": "Mayo Hospital", "lat": 31.5690, "lng": 74.3133},
        {"name": "Services Hospital", "lat": 31.5092, "lng": 74.3427},
    ],
}


def _get_city(area: str) -> str:
    """Get the city for an area to look up emergency destinations."""
    area_lower = area.lower()
    if any(k in area_lower for k in ["karachi", "lyari"]):
        return "karachi"
    elif any(k in area_lower for k in ["lahore"]):
        return "lahore"
    return "islamabad"


def _get_coords(area: str) -> dict:
    """Get coordinates for an area, default to Islamabad center."""
    area_lower = area.lower().strip()
    if area_lower in LOCATION_COORDS:
        return LOCATION_COORDS[area_lower]
    # Try partial match
    for key, coords in LOCATION_COORDS.items():
        if key in area_lower or area_lower in key:
            return coords
    # Default to Islamabad center
    return {"lat": 33.6844, "lng": 73.0479, "name": area}


async def _fetch_google_directions(origin_lat: float, origin_lng: float,
                                    dest_lat: float, dest_lng: float,
                                    dest_name: str) -> dict | None:
    """
    Fetch route data from Google Maps Directions API.
    Returns route info with traffic data, or None on failure.
    """
    if not GOOGLE_MAPS_API_KEY:
        return None

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{dest_lat},{dest_lng}",
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": GOOGLE_MAPS_API_KEY,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            data = response.json()

            if data.get("status") != "OK" or not data.get("routes"):
                return None

            route = data["routes"][0]
            leg = route["legs"][0]

            # Calculate congestion ratio from traffic duration
            normal_duration = leg["duration"]["value"]  # seconds
            traffic_duration = leg.get("duration_in_traffic", {}).get("value", normal_duration)
            congestion_ratio = traffic_duration / max(normal_duration, 1)

            # Map congestion ratio to 0-10 scale
            if congestion_ratio >= 2.0:
                congestion_level = 10
            elif congestion_ratio >= 1.5:
                congestion_level = 8
            elif congestion_ratio >= 1.3:
                congestion_level = 7
            elif congestion_ratio >= 1.15:
                congestion_level = 5
            elif congestion_ratio >= 1.05:
                congestion_level = 3
            else:
                congestion_level = 1

            # Extract route step names (actual road names)
            road_names = []
            for step in leg.get("steps", []):
                instruction = step.get("html_instructions", "")
                # Strip HTML tags
                import re
                clean = re.sub(r'<[^>]+>', ' ', instruction).strip()
                if clean:
                    road_names.append(clean[:80])

            return {
                "destination": dest_name,
                "distance": leg["distance"]["text"],
                "distance_meters": leg["distance"]["value"],
                "duration_normal": leg["duration"]["text"],
                "duration_normal_seconds": normal_duration,
                "duration_in_traffic": leg.get("duration_in_traffic", {}).get("text", leg["duration"]["text"]),
                "duration_in_traffic_seconds": traffic_duration,
                "congestion_ratio": round(congestion_ratio, 2),
                "congestion_level": congestion_level,
                "route_steps": road_names[:6],
                "start_address": leg.get("start_address", ""),
                "end_address": leg.get("end_address", ""),
            }

    except Exception as e:
        print(f"[Traffic] Google Directions API error: {e}")
        return None


@router.get("/traffic", summary="Get traffic data (Real Google Maps or Mock)")
async def get_traffic(area: str = Query("g10", description="Area code")):
    """
    Returns real traffic data from Google Maps Directions API if key is available.
    Calculates routes from the crisis area to nearby hospitals/emergency services.
    Falls back to mock data if API is unavailable.
    """
    area_lower = area.lower().strip()
    timestamp = datetime.now(timezone.utc).isoformat()
    coords = _get_coords(area)
    city = _get_city(area)

    # ── Try Google Maps Directions API ──
    if GOOGLE_MAPS_API_KEY:
        destinations = EMERGENCY_DESTINATIONS.get(city, EMERGENCY_DESTINATIONS["islamabad"])
        routes = []

        for dest in destinations[:3]:
            route_data = await _fetch_google_directions(
                coords["lat"], coords["lng"],
                dest["lat"], dest["lng"],
                dest["name"]
            )
            if route_data:
                routes.append(route_data)

        if routes:
            # Use worst congestion from all routes
            max_congestion = max(r["congestion_level"] for r in routes)
            blocked_routes = [
                r["destination"] + " route"
                for r in routes if r["congestion_level"] >= 7
            ]
            anomaly = max_congestion >= 6

            print(f"[Traffic] Google Maps API: {len(routes)} routes, congestion={max_congestion}")

            return {
                "area": area,
                "congestion_level": max_congestion,
                "blocked_routes": blocked_routes,
                "normal_congestion": 2,
                "anomaly_detected": anomaly,
                "credibility": 0.95,
                "source": "Google Maps Directions API (Real-Time)",
                "is_real": True,
                "routes": routes,
                "timestamp": timestamp,
            }

    # ── Fallback to Mock Data ──
    if "g10" in area_lower or "g-10" in area_lower:
        return {
            "area": area,
            "congestion_level": 9,
            "blocked_routes": ["Main Margalla Road", "G-10 Markaz Underpass"],
            "normal_congestion": 3,
            "anomaly_detected": True,
            "credibility": 0.90,
            "source": "Traffic Intelligence (Mock)",
            "is_real": False,
            "routes": [
                {"destination": "PIMS Hospital", "distance": "3.2 km", "duration_normal": "8 mins",
                 "duration_in_traffic": "22 mins", "congestion_level": 9,
                 "route_steps": ["Head east on G-10 Main Road", "Turn onto Faisal Avenue", "Continue to PIMS"]},
                {"destination": "Shifa International", "distance": "5.1 km", "duration_normal": "12 mins",
                 "duration_in_traffic": "35 mins", "congestion_level": 8,
                 "route_steps": ["Head south on Service Road", "Merge onto Kashmir Highway", "Take exit to H-8"]},
            ],
            "timestamp": timestamp,
        }
    elif "f8" in area_lower or "f-8" in area_lower:
        return {
            "area": area,
            "congestion_level": 6,
            "blocked_routes": ["F-8 Markaz Road"],
            "normal_congestion": 4,
            "anomaly_detected": True,
            "credibility": 0.85,
            "source": "Traffic Intelligence (Mock)",
            "is_real": False,
            "routes": [
                {"destination": "PIMS Hospital", "distance": "2.8 km", "duration_normal": "7 mins",
                 "duration_in_traffic": "15 mins", "congestion_level": 6,
                 "route_steps": ["Head south on F-8 Main Road", "Turn onto Faisal Avenue", "Continue to PIMS"]},
            ],
            "timestamp": timestamp,
        }
    else:
        return {
            "area": area,
            "congestion_level": 2,
            "blocked_routes": [],
            "normal_congestion": 2,
            "anomaly_detected": False,
            "credibility": 0.90,
            "source": "Traffic Intelligence (Mock)",
            "is_real": False,
            "routes": [],
            "timestamp": timestamp,
        }
