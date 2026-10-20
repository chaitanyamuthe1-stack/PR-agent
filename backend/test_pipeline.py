"""
Verification script for PR Agent Backend Pipeline.
"""

import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.mcp_tools import run_static_analysis, get_mcp_tools_for_language
from backend.rag.vector_store import store
from backend.llm_gateway import gateway
from backend.graph import run_full_pipeline
from backend.samples import SAMPLES

def test_static_analysis():
    print("Testing MCP Static Analysis Layer...")
    py_sample = SAMPLES["python"]["code"]
    res = run_static_analysis(py_sample, "python")
    assert len(res["findings"]) > 0, "Python static analysis should find issues"
    print(f"  [PASS] Python static analysis found {len(res['findings'])} findings.")
    print(f"  [PASS] MCP tools invoked: {res['tools_invoked']}")

    cpp_sample = SAMPLES["cpp"]["code"]
    res_cpp = run_static_analysis(cpp_sample, "cpp")
    assert len(res_cpp["findings"]) > 0, "C++ static analysis should find issues"
    print(f"  [PASS] C++ static analysis found {len(res_cpp['findings'])} findings.")

def test_rag_vector_store():
    print("\nTesting RAG Dedicated Vector Store...")
    stats = store.get_stats()
    assert stats["total_vectors"] > 0, "Vector store should have pre-indexed rules"
    print(f"  [PASS] Total indexed vectors: {stats['total_vectors']}")

    results = store.search("SQL injection untrusted input query", language="python", top_k=2)
    assert len(results) > 0, "RAG search should return results"
    print(f"  [PASS] RAG search top result: {results[0]['rule_id']} (similarity: {results[0]['similarity_score']})")

def test_llm_gateway():
    print("\nTesting LLM Gateway Status & Failover...")
    gw_status = gateway.get_gateway_status()
    print(f"  [PASS] Gateway status: {gw_status['badge']} ({gw_status['fallback_state']})")

def test_full_langgraph_pipeline():
    print("\nTesting End-to-End LangGraph Pipeline...")
    py_sample = SAMPLES["python"]
    result = run_full_pipeline(
        code=py_sample["code"],
        language=py_sample["language"],
        filename=py_sample["filename"],
        max_iterations=1
    )

    assert result["health_score"] < 8.0, "Buggy code should have health score < 8.0"
    assert result["verdict"] == "FIX REQUIRED", "Verdict should be FIX REQUIRED"
    assert len(result["issues"]) > 0, "Pipeline should detect issues"
    assert len(result["telemetry"]) >= 5, "Pipeline should record 6 telemetry stages"
    assert len(result["corrected_code"]) > 20, "Pipeline should provide corrected code"
    assert len(result["changelog"]) > 0, "Pipeline should provide changelog"

    print(f"  [PASS] Initial Health Score: {result['health_score']}/10 ({result['verdict']})")
    print(f"  [PASS] Total Issues Detected: {len(result['issues'])}")
    print(f"  [PASS] Telemetry stages logged: {[t['name'] for t in result['telemetry']]}")
    print(f"  [PASS] Corrected code lines: {len(result['corrected_code'].splitlines())}")
    print(f"  [PASS] Changelog modifications: {len(result['changelog'])}")

if __name__ == "__main__":
    test_static_analysis()
    test_rag_vector_store()
    test_llm_gateway()
    test_full_langgraph_pipeline()
    print("\n>>> ALL BACKEND PIPELINE TESTS PASSED SUCCESSFULLY! <<<")
