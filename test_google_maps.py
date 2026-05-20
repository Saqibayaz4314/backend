#!/usr/bin/env python3
"""
Test Google Maps Distance Matrix API
"""
import os
import sys
import httpx
import json
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

def test_google_maps_api():
    """Test if Google Maps API key works"""
    
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    if not api_key:
        print("❌ GOOGLE_MAPS_API_KEY not found in .env")
        return False
    
    print(f"✓ API Key found (length: {len(api_key)})")
    
    # Test parameters
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": "33.7298,-73.1785",  # G-10 Coordinates
        "destinations": "33.7298,-73.1785",
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": api_key
    }
    
    print("\nMaking API request to Google Maps Distance Matrix API...")
    print(f"URL: {url}")
    print(f"Origins (G-10): 33.7298,-73.1785")
    
    try:
        response = httpx.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        status = data.get("status", "UNKNOWN")
        
        print(f"API Status: {status}")
        
        if status == "OK":
            print("✅ Google Maps API Key is VALID and WORKING!")
            print("\nResponse Summary:")
            print(json.dumps(data, indent=2)[:500] + "...")
            return True
        elif status == "REQUEST_DENIED":
            print("❌ API Key is INVALID or doesn't have Distance Matrix API enabled")
            print(f"Error Message: {data.get('error_message', 'No message')}")
            return False
        elif status == "ZERO_RESULTS":
            print("⚠️  API Key works but got ZERO_RESULTS")
            print("(This is normal for same origin/destination)")
            print("✅ Key is valid!")
            return True
        else:
            print(f"⚠️  Unexpected status: {status}")
            print(f"Error: {data.get('error_message', 'No message')}")
            return False
            
    except httpx.TimeoutException:
        print("❌ Request timeout - check internet connection")
        return False
    except httpx.RequestError as e:
        print(f"❌ Request error: {e}")
        return False
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response: {response.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Google Maps Distance Matrix API")
    print("=" * 60)
    
    result = test_google_maps_api()
    
    print("\n" + "=" * 60)
    if result:
        print("✅ TEST PASSED - API Key is working!")
        sys.exit(0)
    else:
        print("❌ TEST FAILED - API Key validation failed")
        sys.exit(1)
