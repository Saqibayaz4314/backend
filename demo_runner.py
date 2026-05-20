import asyncio
import httpx
import json
import time
import subprocess
import os
import sys

async def run_demo():
    print("=== CIRO Multi-Agent Pipeline End-to-End Test ===")
    
    # Start the server
    print("\nStarting CIRO backend server...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    # Wait for server to start
    time.sleep(10)
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print("\n1. Testing Pipeline with 'g10' (Urban Flooding simulation)")
            print("Sending request to /analyze...")
            
            payload = {
                "text": "Flooding on 9th Ave near g10",
                "location": "g10",
                "source": "social_media"
            }
            
            response = await client.post("http://127.0.0.1:8000/analyze", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                print("\n[SUCCESS] Pipeline Completed Successfully!")
                print(f"Crisis Type: {data['crisis']['type']}")
                print(f"Location: {data['crisis']['location']}")
                print(f"Confidence: {data['crisis']['confidence']}")
                
                print("\nGenerated Actions:")
                for action in data['actions']:
                    print(f"  - [{action['type']}] {action['description']} (Entity: {action['entity']})")
                    
                print("\nSimulation Metrics:")
                print(f"  Before: {data['simulation']['metrics_before']}")
                print(f"  After: {data['simulation']['metrics_after']}")
            else:
                print(f"\n[ERROR] Pipeline failed with status code {response.status_code}")
                print(response.text)
                
    finally:
        print("\nStopping server...")
        server_process.terminate()
        server_process.wait()
        
        print("\n=== SERVER LOGS ===")
        print(server_process.stdout.read().decode(errors='replace'))
        print(server_process.stderr.read().decode(errors='replace'))

if __name__ == "__main__":
    asyncio.run(run_demo())
