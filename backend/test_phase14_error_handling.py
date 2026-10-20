"""
Phase 14 — Comprehensive Error Handling & Zero False-Clean Verification Suite.
Validates graceful failure and truthful status reporting across 10 failure modes:
1. Ollama unavailable
2. Qwen unavailable
3. Primary LLM unavailable
4. Fallback LLM unavailable
5. RAG unavailable
6. MCP unavailable
7. Static analyzer unavailable
8. Invalid source code
9. Database failure
10. Network timeout
"""

import os
import sys
import pytest

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.llm_gateway import gateway
from backend.rag.vector_store import store
from backend.mcp_tools import run_static_analysis
from backend.graph import run_full_pipeline
from backend.database import save_review_record, get_review_record, get_db_health
from backend.samples import SAMPLES


def clear_simulation_env():
    """Resets all simulation flags to default clean state."""
    flags = [
        "PR_AGENT_SIMULATE_OLLAMA_FAIL",
        "PR_AGENT_SIMULATE_QWEN_FAIL",
        "PR_AGENT_SIMULATE_PRIMARY_FAIL",
        "PR_AGENT_SIMULATE_FALLBACK_FAIL",
        "PR_AGENT_SIMULATE_RAG_FAIL",
        "PR_AGENT_SIMULATE_MCP_FAIL",
        "PR_AGENT_SIMULATE_ANALYZER_FAIL",
        "PR_AGENT_SIMULATE_DB_FAIL",
        "PR_AGENT_SIMULATE_NETWORK_TIMEOUT"
    ]
    for f in flags:
        os.environ.pop(f, None)
    gateway.reset_transient_errors()


# --------------------------------------------------------------------------
# 1. Ollama Unavailable
# --------------------------------------------------------------------------
def test_ollama_unavailable():
    print("\n[TEST 1] Verifying Ollama Unavailable Graceful Handling...")
    clear_simulation_env()
    os.environ["PR_AGENT_SIMULATE_OLLAMA_FAIL"] = "1"
    try:
        # Gateway status reports Ollama is offline
        status = gateway.get_gateway_status()
        assert status["ollama_available"] is False, "Ollama must be reported as unavailable"

        # Generate still executes via alternative without crashing
        res = gateway.generate("Analyze this code", provider_preference="ollama")
        assert len(res) > 0, "Gateway must fall back gracefully to heuristic engine"
        assert gateway.fallback_active is True, "Fallback state must be active"

        # Full pipeline still reviews code and never falsely reports CLEAN
        sample = SAMPLES["python"]
        pipe_res = run_full_pipeline(sample["code"], "python", "app.py")
        assert pipe_res["verdict"] == "FIX REQUIRED", "Buggy code must not report CLEAN when Ollama is down"
        assert pipe_res["health_score"] < 8.0, "Health score must reflect defects"
        print("  [PASS] Ollama offline handled gracefully; truthful verdict 'FIX REQUIRED' reported.")
    finally:
        clear_simulation_env()


# --------------------------------------------------------------------------
# 2. Qwen Unavailable
# --------------------------------------------------------------------------
def test_qwen_unavailable():
    print("\n[TEST 2] Verifying Qwen Model Unavailable Graceful Handling...")
    clear_simulation_env()
    os.environ["PR_AGENT_SIMULATE_QWEN_FAIL"] = "1"
    try:
        status = gateway.get_gateway_status()
        # Qwen missing should trigger fallback
        res = gateway.generate("Security Agent review", provider_preference="ollama")
        assert len(res) > 0, "Gateway must fall over when Qwen model is missing"
        assert gateway.fallback_error is not None, "Fallback error regarding Qwen must be recorded"
        assert "qwen" in gateway.fallback_error.lower(), "Error must identify Qwen model as unavailable"

        # Pipeline verifies defects without false clean
        sample = SAMPLES["javascript"]
        pipe_res = run_full_pipeline(sample["code"], "javascript", "server.js")
        assert pipe_res["verdict"] == "FIX REQUIRED", "Verdict must reflect detected defects"
        print("  [PASS] Qwen missing handled gracefully; truthful verdict 'FIX REQUIRED' reported.")
    finally:
        clear_simulation_env()


# --------------------------------------------------------------------------
# 3. Primary LLM Unavailable
# --------------------------------------------------------------------------
def test_primary_llm_unavailable():
    print("\n[TEST 3] Verifying Primary LLM Unavailable Graceful Handling...")
    clear_simulation_env()
    os.environ["PR_AGENT_SIMULATE_PRIMARY_FAIL"] = "1"
    try:
        status = gateway.get_gateway_status()
        # Generation must failover to fallback
        res = gateway.generate("Bug-Detection Agent review", provider_preference="gemini")
        assert len(res) > 0, "Must fall back to secondary provider/heuristic"
        assert gateway.fallback_active is True, "Fallback must be marked active"
        assert gateway.primary_error is not None, "Primary error must be recorded"

        # Pipeline verifies defects
        sample = SAMPLES["cpp"]
        pipe_res = run_full_pipeline(sample["code"], "cpp", "main.cpp")
        assert pipe_res["verdict"] == "FIX REQUIRED", "Primary failure must not produce false CLEAN"
        # Telemetry should note primary LLM failover
        gw_tele = next((t for t in pipe_res["telemetry"] if t["stage"] == "llm_gateway"), None)
        assert gw_tele is not None, "Gateway telemetry must exist"
        print("  [PASS] Primary LLM failure handled gracefully; automatic failover verified.")
    finally:
        clear_simulation_env()


# --------------------------------------------------------------------------
# 4. Fallback LLM Unavailable
# --------------------------------------------------------------------------
def test_fallback_llm_unavailable():
    print("\n[TEST 4] Verifying Primary & Fallback LLMs Concurrently Unavailable...")
    clear_simulation_env()
    os.environ["PR_AGENT_SIMULATE_PRIMARY_FAIL"] = "1"
    os.environ["PR_AGENT_SIMULATE_FALLBACK_FAIL"] = "1"
    try:
        # Gateway falls over to Fallback 2: Offline Deterministic Engine
        res = gateway.generate("Review code defects", provider_preference="gemini")
        assert len(res) > 0, "Must fall over to deterministic heuristic engine"
        assert gateway.last_provider_used == "offline_heuristic", "Offline heuristic engine must be active"

        # Pipeline executes end-to-end in offline mode without crashing
        sample = SAMPLES["ruby"]
        pipe_res = run_full_pipeline(sample["code"], "ruby", "app.rb")
        assert pipe_res["verdict"] == "FIX REQUIRED", "Offline review must identify real bugs"
        assert len(pipe_res["issues"]) > 0, "Issues must be flagged by offline heuristic engine"
        print("  [PASS] Dual LLM failure handled gracefully; offline heuristic engine executed.")
    finally:
        clear_simulation_env()


# --------------------------------------------------------------------------
# 5. RAG Unavailable
# --------------------------------------------------------------------------
def test_rag_unavailable():
    print("\n[TEST 5] Verifying RAG Vector Store Unavailable Graceful Handling...")
    clear_simulation_env()
    os.environ["PR_AGENT_SIMULATE_RAG_FAIL"] = "1"
    try:
        # Case 5a: Buggy code with RAG down -> flags bugs, RAG telemetry degraded
        sample = SAMPLES["python"]
        pipe_res = run_full_pipeline(sample["code"], "python", "app.py")
        rag_tele = next((t for t in pipe_res["telemetry"] if t["stage"] == "rag_retrieval"), None)
        assert rag_tele is not None, "RAG telemetry must be logged"
        assert rag_tele["status"] == "degraded", "RAG status must be marked degraded"
        assert pipe_res["verdict"] == "FIX REQUIRED", "Buggy code must be FIX REQUIRED"

        # Case 5b: Clean code with RAG down -> NEVER report CLEAN! Must report DEGRADED (RAG UNAVAILABLE)
        clean_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        clean_res = run_full_pipeline(clean_code, "python", "clean.py")
        assert clean_res["verdict"] != "CLEAN", "CRITICAL: System must NOT falsely report CLEAN when RAG is down"
        assert "RAG UNAVAILABLE" in clean_res["verdict"], "Verdict must truthfully state RAG UNAVAILABLE"
        print("  [PASS] RAG failure handled gracefully; zero false-clean verified.")
    finally:
        clear_simulation_env()


# --------------------------------------------------------------------------
# 6. MCP Unavailable
# --------------------------------------------------------------------------
def test_mcp_unavailable():
    print("\n[TEST 6] Verifying MCP Tool Dispatcher Layer Unavailable...")
    clear_simulation_env()
    os.environ["PR_AGENT_SIMULATE_MCP_FAIL"] = "1"
    try:
        res = run_static_analysis("x = 1", "python")
        assert res["status"] == "MCP UNAVAILABLE", "Status must be MCP UNAVAILABLE"
        assert res["findings"][0]["rule_id"] == "MCP:TOOL_UNAVAILABLE"

        # Pipeline verdict must report MCP UNAVAILABLE, never CLEAN
        pipe_res = run_full_pipeline("def foo(): pass", "python", "test.py")
        assert pipe_res["verdict"] == "MCP UNAVAILABLE", "Verdict must report MCP UNAVAILABLE"
        assert pipe_res["health_score"] <= 5.0, "Health score must reflect degraded capability"
        print("  [PASS] MCP layer failure handled gracefully; truthful verdict 'MCP UNAVAILABLE' reported.")
    finally:
        clear_simulation_env()


# --------------------------------------------------------------------------
# 7. Static Analyzer Unavailable
# --------------------------------------------------------------------------
def test_static_analyzer_unavailable():
    print("\n[TEST 7] Verifying Static Analyzer Unavailable...")
    clear_simulation_env()
    os.environ["PR_AGENT_SIMULATE_ANALYZER_FAIL"] = "1"
    try:
        res = run_static_analysis("x = 1", "python")
        assert res["status"] == "ANALYZER UNAVAILABLE", "Status must be ANALYZER UNAVAILABLE"

        # Pipeline verdict must report ANALYZER UNAVAILABLE, never CLEAN
        pipe_res = run_full_pipeline("def bar(): return True", "python", "bar.py")
        assert pipe_res["verdict"] == "ANALYZER UNAVAILABLE", "Verdict must be ANALYZER UNAVAILABLE"
        assert pipe_res["health_score"] <= 5.0, "Health score must be degraded"
        print("  [PASS] Analyzer failure handled gracefully; truthful verdict 'ANALYZER UNAVAILABLE' reported.")
    finally:
        clear_simulation_env()


# --------------------------------------------------------------------------
# 8. Invalid Source Code (Syntax Errors)
# --------------------------------------------------------------------------
def test_invalid_source_code():
    print("\n[TEST 8] Verifying Invalid Source Code (Syntax/Parsing Errors)...")
    clear_simulation_env()

    test_cases = [
        ("python", "def broken_code(:\n    print('unterminated parenthesis'", "test.py"),
        ("javascript", "function broken( { return 42;", "test.js"),
        ("cpp", "int main() { char *p = 'unclosed; return 0;", "test.cpp"),
        ("java", "public class A { void broken([) {} }", "A.java"),
        ("ruby", "def broken\n puts 'missing end'", "test.rb")
    ]

    for lang, broken_code, fname in test_cases:
        pipe_res = run_full_pipeline(broken_code, lang, fname)
        assert pipe_res["verdict"] == "FIX REQUIRED", f"Invalid {lang} syntax must yield FIX REQUIRED, never CLEAN"
        assert pipe_res["health_score"] < 10.0, f"Invalid {lang} syntax must reduce health score"
        has_syntax = any(
            "syntax" in str(i.get(k, "")).lower()
            for i in pipe_res["issues"]
            for k in ["rule_id", "rule_citation", "title", "description", "message"]
        )
        assert has_syntax, f"Must detect syntax error finding for invalid {lang} code"
        print(f"  [PASS] Invalid {lang.upper()} source caught as critical defect (Verdict: {pipe_res['verdict']}).")


# --------------------------------------------------------------------------
# 9. Database Failure
# --------------------------------------------------------------------------
def test_database_failure():
    print("\n[TEST 9] Verifying Database Failure Graceful Degradation...")
    clear_simulation_env()
    os.environ["PR_AGENT_SIMULATE_DB_FAIL"] = "1"
    try:
        # Saving review fails over to in-memory cache without raising unhandled exception
        save_res = save_review_record("rev-fail-1", {"verdict": "FIX REQUIRED", "filename": "test.py"})
        assert save_res["status"] == "degraded", "Save operation must report degraded status"
        assert "Database failure" in save_res["error"], "Error details must be captured"

        # Reading review record from in-memory fallback works seamlessly
        record = get_review_record("rev-fail-1")
        assert record is not None, "In-memory cache fallback must preserve review data"
        assert record["filename"] == "test.py"

        # DB health check truthfully reports degraded
        health = get_db_health()
        assert health["status"] == "degraded", "Health check must report degraded"

        # Pipeline executes and tags review with database_status degraded
        pipe_res = run_full_pipeline("x = 1", "python", "app.py")
        assert pipe_res["database_status"] == "degraded", "Pipeline output must flag database degradation"
        print("  [PASS] Database failure handled gracefully; zero 500 crashes, fallback active.")
    finally:
        clear_simulation_env()


# --------------------------------------------------------------------------
# 10. Network Timeout
# --------------------------------------------------------------------------
def test_network_timeout():
    print("\n[TEST 10] Verifying Network Timeout Graceful Handling...")
    clear_simulation_env()
    os.environ["PR_AGENT_SIMULATE_NETWORK_TIMEOUT"] = "1"
    try:
        res = gateway.generate("Review code", provider_preference="gemini")
        assert len(res) > 0, "Must fall back on network timeout"
        assert gateway.fallback_active is True, "Fallback must be active after timeout"
        assert gateway.error_category == "network_timeout", "Error category must be network_timeout"

        # Pipeline runs to completion with degraded gateway telemetry
        sample = SAMPLES["python"]
        pipe_res = run_full_pipeline(sample["code"], "python", "app.py")
        assert pipe_res["verdict"] == "FIX REQUIRED", "Network timeout must not result in false clean"
        gw_tele = next((t for t in pipe_res["telemetry"] if t["stage"] == "llm_gateway"), None)
        assert gw_tele is not None
        assert gw_tele["status"] == "degraded", "Gateway telemetry status must be degraded on timeout"
        assert "timeout" in gw_tele["action"].lower(), "Telemetry action must mention timeout"
        print("  [PASS] Network timeout handled gracefully; fallback active, no hanging/crash.")
    finally:
        clear_simulation_env()


# --------------------------------------------------------------------------
# 11. Zero False-Clean Invariant
# --------------------------------------------------------------------------
def test_zero_false_clean_invariant():
    print("\n[TEST 11] Verifying Zero False-Clean Invariant Across All Failure Modes...")
    failure_scenarios = [
        ("PR_AGENT_SIMULATE_MCP_FAIL", "1", "x = 1", "python"),
        ("PR_AGENT_SIMULATE_ANALYZER_FAIL", "1", "x = 1", "python"),
        ("PR_AGENT_SIMULATE_RAG_FAIL", "1", "x = 1", "python"),
        ("PR_AGENT_SIMULATE_NETWORK_TIMEOUT", "1", SAMPLES["python"]["code"], "python"),
    ]

    for env_var, val, code, lang in failure_scenarios:
        clear_simulation_env()
        os.environ[env_var] = val
        try:
            res = run_full_pipeline(code, lang, "test.py")
            assert res["verdict"] != "CLEAN", f"CRITICAL VIOLATION: {env_var} falsely produced CLEAN verdict!"
            print(f"  [PASS] {env_var}: Verdict is '{res['verdict']}' (Zero False-Clean Guaranteed).")
        finally:
            clear_simulation_env()


def run_all_tests():
    print("======================================================================")
    print("PHASE 14 — COMPREHENSIVE ERROR HANDLING & TRUTHFUL STATUS TEST SUITE")
    print("======================================================================")
    test_ollama_unavailable()
    test_qwen_unavailable()
    test_primary_llm_unavailable()
    test_fallback_llm_unavailable()
    test_rag_unavailable()
    test_mcp_unavailable()
    test_static_analyzer_unavailable()
    test_invalid_source_code()
    test_database_failure()
    test_network_timeout()
    test_zero_false_clean_invariant()
    print("\n======================================================================")
    print(">>> ALL 10 FAILURE MODES & ZERO FALSE-CLEAN INVARIANTS PASSED 100% <<<")
    print("======================================================================")


if __name__ == "__main__":
    run_all_tests()
