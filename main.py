"""
CIRO — Crisis Intelligence & Response Orchestrator
====================================================
FastAPI entry point for the CIRO backend system.
"""

import asyncio
import os
import time
import traceback
from datetime import datetime, timezone
from typing import Optional
import re

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import configuration and middleware
from config import settings, validate_environment, print_startup_banner
from middleware import CIROMiddleware, rate_limiter, request_cache, performance_monitor

# Validate environment at startup
try:
    print_startup_banner()
except RuntimeError as e:
    print(f"Configuration error: {e}")
    exit(1)

app = FastAPI(
    title="CIRO — Crisis Intelligence & Response Orchestrator",
    description="Agentic AI system for crisis response in Pakistan.",
    version="1.0.0",
)

cors_allow_list = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(CIROMiddleware, rate_limiter=rate_limiter, cache=request_cache)

# Global Exception Handler
from starlette.requests import Request
from starlette.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from utils.gemini_client import GeminiUnavailableError
    if isinstance(exc, HTTPException): return exc
    if isinstance(exc, GeminiUnavailableError):
        return JSONResponse(status_code=503, content={"detail": {"status": "ai_unavailable", "message": str(exc)}})
    return JSONResponse(status_code=500, content={"detail": {"status": "error", "message": "Internal server error."}})

# Include Routers
from mock_api.weather_router import router as weather_router
from mock_api.traffic_router import router as traffic_router
from mock_api.social_router import router as social_router
from mock_api.sensor_router import router as sensor_router
from mock_api.x_router import router as x_router
from auth import router as auth_router

app.include_router(weather_router, prefix="/mock", tags=["Mock Data"])
app.include_router(traffic_router, prefix="/mock", tags=["Mock Data"])
app.include_router(social_router, prefix="/mock", tags=["Mock Data"])
app.include_router(sensor_router, prefix="/mock", tags=["Mock Data"])
app.include_router(x_router, prefix="/mock", tags=["Mock Data"])
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Monitoring Endpoints
@app.get("/health", tags=["Monitoring"])
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/system-info", tags=["Monitoring"])
async def system_info():
    from utils.firebase_client import FirebaseClient
    fb = FirebaseClient()
    return {"status": "operational", "apis": {"gemini": bool(settings.gemini_api_key), "firebase": fb.is_connected()}}

# --- MAIN CRISIS PIPELINE ---
from agents.signal_collector import SignalCollector
from agents.crisis_detector import CrisisDetector
from agents.situation_analyzer import SituationAnalyzer
from agents.action_planner import ActionPlanner
from agents.executor import Executor

from models.signal_models import AnalyzeRequest
from models.action_models import AnalyzeResponse, MultiCrisisRequest, MultiCrisisResponse

from utils.gemini_client import GeminiClient
from utils.firebase_client import FirebaseClient
from utils.logger import AgentLogger

_gemini_client = GeminiClient()

@app.post("/analyze", tags=["Crisis Pipeline"], response_model=AnalyzeResponse)
async def analyze_crisis(request: AnalyzeRequest):
    incident_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    trace_id = request.client_trace_id or f"TRACE-{incident_id}"
    
    logger = AgentLogger(trace_id, incident_id)
    gemini = _gemini_client
    firebase = FirebaseClient()

    signal_collector = SignalCollector(gemini)
    crisis_detector = CrisisDetector(gemini)
    situation_analyzer = SituationAnalyzer(gemini)
    action_planner = ActionPlanner(gemini)
    executor = Executor(gemini)

    try:
        t_start = time.time()

        # Agent 1: Signal Collection
        signals = await signal_collector.collect(request, logger)
        
        # EXTRACT SIGNAL BREAKDOWN FOR MOBILE UI
        agent_logs_mobile = logger.get_agent_logs_for_mobile()
        signal_meta = {}
        for log in agent_logs_mobile:
            if log["agent_name"] == "agent_1_signal_collector":
                signal_meta = log.get("details", {}).get("detailed_breakdown", {})

        # Agent 2: Crisis Detection
        crisis = await crisis_detector.detect(signals, logger)

        # Agent 3: Situation Analysis
        crisis = await situation_analyzer.analyze(crisis, signals, logger)

        # Agent 4: Action Planning
        actions, messages = await action_planner.plan(crisis, logger)

        # Agent 5: Execution & Simulation
        simulation = await executor.execute(incident_id, crisis, actions, logger, messages)

        processing_time = int((time.time() - t_start) * 1000)

        response = AnalyzeResponse(
            incident_id=incident_id,
            status="success",
            processing_time_ms=processing_time,
            crisis=crisis,
            signals_used=signals.signals,
            actions=actions,
            stakeholder_messages=messages,
            simulation=simulation,
            agent_trace_id=trace_id,
            agent_logs=logger.get_agent_logs_for_mobile(),
            signal_metadata=signal_meta
        )

        firebase.save_incident(incident_id, response.model_dump())
        firebase.save_agent_trace(trace_id, logger.get_trace_data())
        return response

    except Exception as e:
        logger.log_agent_step("system", "error", str(request), str(e), 0)
        raise HTTPException(status_code=500, detail=str(e))

# Multi-Crisis & Resource Logic
@app.post("/analyze-multi", tags=["Crisis Pipeline"], response_model=MultiCrisisResponse)
async def analyze_multi_crisis(request: MultiCrisisRequest):
    # Multi-crisis logic implementation (restored)
    t_start = time.time()
    # Simplified multi-crisis runner for the fix
    results = []
    for c_input in request.crises:
        res = await analyze_crisis(AnalyzeRequest(text=c_input.text, location=c_input.location))
        results.append(res)
    
    return MultiCrisisResponse(
        incidents=results,
        total_processing_time_ms=int((time.time() - t_start) * 1000)
    )

# --- Incident & Log Endpoints ---
@app.get("/incidents", tags=["Incidents"])
async def get_all_incidents():
    return {"incidents": FirebaseClient().get_all_incidents()}

@app.get("/logs", tags=["Logging"])
async def list_logs():
    import json
    from pathlib import Path
    logs_dir = Path("./logs/agent_traces")
    if not logs_dir.exists(): return {"logs": []}
    files = sorted(logs_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    logs = []
    for f in files:
        with open(f, "r") as j:
            d = json.load(j)
            logs.append({"trace_id": d.get("trace_id"), "incident_id": d.get("incident_id"), "timestamp": d.get("timestamp")})
    return {"logs": logs}

@app.get("/logs/{trace_id}", tags=["Logging"])
async def get_log(trace_id: str):
    from utils.logger import AgentLogger
    trace = AgentLogger.get_trace(trace_id)
    if not trace: raise HTTPException(status_code=404)
    return trace

@app.post("/reset", tags=["System"])
async def reset_state():
    FirebaseClient().reset_state()
    return {"status": "success"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
