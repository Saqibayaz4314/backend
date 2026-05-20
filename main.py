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

from config import settings, validate_environment, print_startup_banner
from middleware import CIROMiddleware, rate_limiter, request_cache, performance_monitor

try:
    print_startup_banner()
except RuntimeError as e:
    print(f"Configuration error: {e}")
    exit(1)

app = FastAPI(
    title="CIRO — Crisis Intelligence & Response Orchestrator",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(CIROMiddleware, rate_limiter=rate_limiter, cache=request_cache)

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

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# --- Pipeline Endpoints ---
from agents.signal_collector import SignalCollector
from agents.crisis_detector import CrisisDetector
from agents.situation_analyzer import SituationAnalyzer
from agents.action_planner import ActionPlanner
from agents.executor import Executor

from models.signal_models import AnalyzeRequest, SignalSource
from models.action_models import AnalyzeResponse

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

        # Step 1: Signal Collection
        logger.log_agent_step("agent_1_signal_collector", "Signal Collection", "Starting...", "COLLECTING_LIVE_DATA", 0)
        signals = await signal_collector.collect(request, logger)
        
        # Calculate Breakdown Directly from signals object (FOR UI)
        signal_meta = {
            "weather": len([s for s in signals.signals if s.source == SignalSource.WEATHER_API]),
            "traffic": len([s for s in signals.signals if s.source == SignalSource.TRAFFIC_API]),
            "sensors": len([s for s in signals.signals if s.source == SignalSource.SENSOR]),
            "social_media": len([s for s in signals.signals if s.source == SignalSource.SOCIAL_MEDIA]),
        }

        # Step 2: Crisis Detection
        logger.log_agent_step("agent_2_crisis_detector", "Crisis Detection", "Analyzing signals...", "DETECTING_CRISIS", 0)
        crisis = await crisis_detector.detect(signals, logger)

        # Step 3: Situation Analysis
        logger.log_agent_step("agent_3_situation_analyzer", "Situation Analysis", "Calculating impact...", "ANALYZING_SITUATION", 0)
        crisis = await situation_analyzer.analyze(crisis, signals, logger)

        # Step 4: Action Planning
        logger.log_agent_step("agent_4_action_planner", "Action Planning", "Generating response...", "PLANNING_ACTIONS", 0)
        actions, messages = await action_planner.plan(crisis, logger)

        # Step 5: Execution & Simulation
        logger.log_agent_step("agent_5_executor", "Executor", "Simulating outcome...", "EXECUTING_SIMULATION", 0)
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

        # Final Save
        firebase.save_incident(incident_id, response.model_dump())
        firebase.save_agent_trace(trace_id, logger.get_trace_data())
        return response

    except Exception as e:
        logger.log_agent_step("system", "Error", "Pipeline failure", str(e), 0)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/incidents", tags=["Incidents"])
async def get_all_incidents():
    return {"incidents": FirebaseClient().get_all_incidents()}

@app.get("/logs/{trace_id}")
async def get_log(trace_id: str):
    trace = AgentLogger.get_trace(trace_id)
    if not trace: raise HTTPException(status_code=404)
    return trace

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
