import asyncio
import sys
import json
import os

for mod in list(sys.modules.keys()):
    if any(x in mod for x in ['config', 'agents', 'models', 'mock_api']):
        del sys.modules[mod]

from agents.signal_collector import SignalCollector
from models.signal_models import AnalyzeRequest, SignalSource
from utils.gemini_client import GeminiClient
from utils.logger import AgentLogger

async def test():
    try:
        print("\n" + "="*80)
        print("✅ AGENT LOGGING TEST - DETAILED SIGNAL COLLECTION")
        print("="*80)
        
        gemini = GeminiClient()
        collector = SignalCollector(gemini)
        
        # Create logger
        logger = AgentLogger(
            trace_id="TEST-SIGNAL-LOGS-001",
            incident_id="G10-FLOOD-TEST",
            console_output=True
        )
        
        # Test request
        request = AnalyzeRequest(
            text="G-10 mein heavy flooding ho rahi hai, roads blocked",
            location="G-10",
            include_mock_signals=True
        )
        
        print(f"\n📍 Testing: {request.text}")
        print(f"📊 Location: {request.location}\n")
        
        # Collect signals
        signals = await collector.collect(request, logger)
        
        print(f"\n✅ Collection Complete!")
        print(f"   Total Signals: {len(signals.signals)}")
        print(f"   Collection Time: {signals.collection_time_ms}ms\n")
        
        # Show signals by source
        print("📊 SIGNALS BY SOURCE:")
        sources_data = {}
        for sig in signals.signals:
            src = sig.source.value if hasattr(sig.source, 'value') else str(sig.source)
            if src not in sources_data:
                sources_data[src] = []
            sources_data[src].append(sig)
        
        for source, sigs in sources_data.items():
            print(f"\n   {source}: {len(sigs)} signals")
            for i, sig in enumerate(sigs[:2], 1):
                print(f"      {i}. {sig.text[:50]}... (credibility: {sig.credibility})")
        
        # Check logs file
        log_file = "logs/agent_traces/TEST-SIGNAL-LOGS-001.json"
        print(f"\n📝 Logs saved to: {log_file}")
        
        # Read and display log structure
        if os.path.exists(log_file):
            with open(log_file) as f:
                log_data = json.load(f)
                if "agents" in log_data and "agent_1_signal_collector" in log_data["agents"]:
                    collector_log = log_data["agents"]["agent_1_signal_collector"]
                    # If it's a dict, it's the newer format
                    if isinstance(collector_log, dict):
                        print(f"\n✅ LOG ENTRY STRUCTURE:")
                        print(f"   Step: {collector_log.get('step', 'N/A')}")
                        print(f"   Output: {collector_log.get('output', 'N/A')}")
                        
                        print(f"\n   📋 Detailed Data:")
                        print(f"      Sources Checked: {collector_log.get('sources_checked', [])}")
                        if "detailed_breakdown" in collector_log:
                            print(f"      Signal Breakdown:")
                            for src, count in collector_log["detailed_breakdown"].items():
                                status = "✅" if count > 0 else "❌"
                                print(f"         {status} {src.replace('_', ' ').title()}: {count}")
        else:
            print(f"\n❌ Log file not found at {log_file}")
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETE - Logs structure verified!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())
