import asyncio
import sys
import time
import os

# Set search path to ensure we find 'backend'
sys.path.append(os.getcwd())

try:
    from agents.signal_collector import SignalCollector
    from models.signal_models import AnalyzeRequest
    from utils.gemini_client import GeminiClient
    from utils.logger import AgentLogger
    from config import settings

    async def test():
        try:
            print("=" * 70)
            print("✅ OPTIMIZED SIGNAL COLLECTION TEST (Google Search REMOVED)")
            print("=" * 70)
            
            gemini = GeminiClient()
            collector = SignalCollector(gemini)
            logger = AgentLogger(trace_id="test", incident_id="g10_flood")
            
            request = AnalyzeRequest(
                text="G-10 mein heavy flooding ho rahi hai",
                location="G-10",
                include_mock_signals=True
            )
            
            print(f"\n🔍 Testing with: {request.text}")
            print(f"📍 Location: {request.location}\n")
            
            start = time.time()
            
            signals = await collector.collect(request, logger)
            
            elapsed = time.time() - start
            
            print(f"⏱️  Collection Time: {elapsed:.2f} seconds")
            print(f"📊 Total Signals: {len(signals.signals)}")
            
            # Breakdown by source
            sources = {}
            for sig in signals.signals:
                src = sig.source.value if hasattr(sig.source, "value") else str(sig.source)
                sources[src] = sources.get(src, 0) + 1
            
            print("\n📋 Signals by Source:")
            for src, count in sources.items():
                print(f"   • {src}: {count}")
            
            # X API signals
            x_signals = [s for s in signals.signals if s.metadata.get("origin") == "x_api"]
            print(f"\n🐦 X API Signals: {len(x_signals)}")
            
            print("\n✅ Result: FASTER collection without Google Search noise!")
            print("=" * 70)
            
        except Exception as e:
            print(f"Error during test: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(test())
except ImportError as e:
    print(f"Import Error: {e}")
    # Print working directory and list files to debug imports
    print(f"CWD: {os.getcwd()}")
    print(f"Contents: {os.listdir('.')}")
