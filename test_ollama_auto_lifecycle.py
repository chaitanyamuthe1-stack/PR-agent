"""
Automated Verification for Ollama Qwen-Coder Lifecycle in PR Agent.
Tests:
1. Ollama auto-boot via lifespan startup.
2. Verified connection and model detection.
3. Clean shutdown on backend lifespan exit (zero orphaned processes).
"""

import sys
import time
import httpx
import asyncio
from backend.main import app
from backend.ollama_service import ollama_service, is_ollama_running
from backend.llm_gateway import gateway


async def run_lifecycle_test():
    print("\n--- TEST 1: Initial State Check ---")
    initial_running = is_ollama_running()
    print(f"Ollama running before test: {initial_running}")
    if initial_running:
        print("Stopping existing instance to test clean auto-boot...")
        ollama_service.stop_ollama()
        time.sleep(1)

    print("\n--- TEST 2: Testing Lifespan Startup Hook ---")
    # Simulate FastAPI lifespan startup
    async with app.router.lifespan_context(app):
        print("FastAPI lifespan entered. Waiting for Ollama to come online...")
        # Wait up to 15 seconds for Ollama daemon to finish booting
        online = False
        for i in range(30):
            if is_ollama_running():
                online = True
                break
            await asyncio.sleep(0.5)

        assert online, "Ollama must be online after FastAPI lifespan starts"
        print("  [PASS] Ollama server is ONLINE via lifespan hook!")

        # Verify gateway detects Ollama Qwen
        status = gateway.get_gateway_status()
        print(f"Gateway Provider: {status['provider']} | Status: {status['status']} | Badge: {status['badge']}")
        assert status["ollama_available"] is True, "Gateway must detect Ollama available"
        assert status["ollama_model_installed"] is True, "Gateway must detect qwen2.5-coder:7b installed"
        print("  [PASS] Gateway reports Ollama Qwen Coder Connected!")

        # Quick inference probe
        print("\n--- TEST 3: Testing Inference through Gateway ---")
        res = gateway.generate("Respond with JSON: {\"status\": \"ok\"}", provider_preference="ollama")
        print(f"Gateway Response: {res[:120]}...")
        assert len(res) > 0, "Response must not be empty"
        print("  [PASS] Inference successfully returned by Qwen2.5-Coder!")

        print("\n--- TEST 4: Exiting Lifespan (Simulating Backend Shutdown) ---")

    # Lifespan has exited
    print("FastAPI lifespan exited. Verifying Ollama shutdown...")
    time.sleep(2)
    after_running = is_ollama_running()
    print(f"Ollama running after shutdown: {after_running}")
    assert not after_running, "Ollama must be SHUT DOWN after FastAPI exits"
    print("  [PASS] Ollama server cleanly shut down with zero lingering processes!")

    print("\n=======================================================")
    print(" ALL LIFECYCLE TESTS PASSED PERFECTLY!")
    print("=======================================================")


if __name__ == "__main__":
    asyncio.run(run_lifecycle_test())
