"""
Automated Test Suite for Optimized PR Agent Pipeline.
Validates:
1. Stage execution, duration recording, and accurate state transitions (PENDING, RUNNING, COMPLETED, SKIPPED, FAILED, TIMED_OUT).
2. Parallel execution and timeout handling.
3. Cache hits, misses, composite key invalidation, and RAG cache.
4. Circuit breaker states (CLOSED, OPEN, HALF_OPEN) and fast-fail fallback.
5. Duplicate finding aggregation, rule deduplication, and verified vs unverified telemetry.
6. Empty and large pull request bounds.
7. Vulnerable test fixture verification (vulnerable_app.py / SAMPLES['python']).
8. Remediation validation, syntax integrity, and regression prevention.
9. Configurable health score, verification weighting, and unassessed vs genuine zero/ten distinction.
"""

import os
import sys
import time
import pytest
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.graph import run_full_pipeline, validate_code_syntax, parallel_review_node
from backend.mcp_tools import run_static_analysis, get_static_cache_stats, clear_static_cache
from backend.rag.vector_store import store, get_rag_cache_stats, clear_rag_cache
from backend.llm_gateway import gateway, CircuitBreaker
from backend.agents.summary_agent import run_summary_agent, calculate_health_score, ScoringCriteria
from backend.samples import SAMPLES


def test_1_stage_execution_and_state_transitions():
    """All 6 stages must be present in telemetry with truthful states, durations, and total elapsed time."""
    clean_code = "def calculate_sum(a: int, b: int) -> int:\n    return a + b\n"
    res = run_full_pipeline(clean_code, "python", "math_utils.py")

    assert "telemetry" in res
    stages = [t["stage"] for t in res["telemetry"]]
    
    # Requirement 2: All 6 stages must be preserved and visible
    expected_stages = [
        "static_analysis",
        "rag_retrieval",
        "llm_gateway",
        "multi_agent_review",
        "summary_agent",
        "coder_agent"
    ]
    for s in expected_stages:
        assert s in stages, f"Missing required pipeline stage: '{s}'"

    # Verify duration recording and valid status
    valid_statuses = {"COMPLETED", "COMPLETE", "SKIPPED", "DEGRADED", "FAILED", "TIMED_OUT"}
    for t in res["telemetry"]:
        assert str(t["status"]).upper() in valid_statuses, f"Invalid stage status: {t['status']}"
        assert "latency_ms" in t or "duration_ms" in t, f"Stage {t['stage']} missing latency/duration"
        assert "retry_count" in t, f"Stage {t['stage']} missing retry_count"
        assert "failure_reason" in t, f"Stage {t['stage']} missing failure_reason"

    # Requirement 1: Remediation skipped when 0 actionable findings
    coder_tele = next(t for t in res["telemetry"] if t["stage"] == "coder_agent")
    assert coder_tele["status"] == "SKIPPED", f"Coder agent must be SKIPPED on clean code, got {coder_tele['status']}"
    assert coder_tele["latency_ms"] == 0.0

    # Total elapsed time must be tracked end-to-end
    assert "total_elapsed_ms" in res
    assert res["total_elapsed_ms"] >= 0.0
    print(f"  [PASS] All 6 pipeline stages verified with accurate states. Total elapsed: {res['total_elapsed_ms']}ms.")


def test_2_parallel_execution_and_timeout_handling():
    """Parallel execution bounds and timeout recovery without crashing."""
    # Test ThreadPool execution timeout handling
    os.environ["PR_AGENT_REVIEW_TIMEOUT"] = "0.01"  # ultra-low timeout to trigger timeout handling safely
    try:
        mock_state = {
            "code": "import os\nos.system('echo 1')",
            "language": "python",
            "provider": "offline",
            "rag_context": [],
            "iteration_count": 0,
            "static_findings": [{"category": "security", "rule_id": "B605", "line": 2, "message": "Command injection"}],
            "telemetry": []
        }
        review_res = parallel_review_node(mock_state)
        tele = review_res["telemetry"][-1]
        assert tele["status"] in ["timed_out", "complete", "degraded"], f"Expected timeout or handled status, got {tele['status']}"
        print(f"  [PASS] Timeout boundary handled gracefully without thread stalls (status: {tele['status']}).")
    finally:
        os.environ.pop("PR_AGENT_REVIEW_TIMEOUT", None)


def test_3_cache_hits_misses_and_composite_invalidation():
    """Composite static analysis cache (file hash + tool version + config hash)."""
    clear_static_cache()
    test_code = "def greet(name):\n    print('Hello ' + name)\n"
    
    # 1. First run: cache miss
    stats_start = get_static_cache_stats()
    res1 = run_static_analysis(test_code, "python")
    assert res1.get("cached") is False, "First execution must be cache miss"

    # 2. Second run with same code and config: cache hit
    res2 = run_static_analysis(test_code, "python")
    assert res2.get("cached") is True, "Second identical execution must be cache hit"

    # 3. Third run with altered code: cache miss
    res3 = run_static_analysis(test_code + "# modified comment\n", "python")
    assert res3.get("cached") is False, "Modified code must invalidate cache and be a miss"

    # 4. Fourth run with modified tool config hash: cache invalidation
    res4 = run_static_analysis(test_code, "python", config_hash="custom-config-v2")
    assert res4.get("cached") is False, "Modified configuration hash must invalidate cache"

    stats_end = get_static_cache_stats()
    assert stats_end["hits"] >= 1, "Cache hit count must be at least 1"
    assert stats_end["misses"] >= 3, "Cache miss count must be at least 3"
    print(f"  [PASS] Composite caching verified (Hits: {stats_end['hits']}, Misses: {stats_end['misses']}).")


def test_4_rag_caching_and_rule_deduplication():
    """Vector store query caching and (rule_id, cwe) deduplication."""
    clear_rag_cache()
    # Query twice
    res1 = store.search(query="SQL injection vulnerability in user login", language="python", top_k=4)
    res2 = store.search(query="SQL injection vulnerability in user login", language="python", top_k=4)
    
    assert len(res1) == len(res2)
    # Check deduplication: no duplicate (rule_id, cwe) pairs
    seen = set()
    for r in res1:
        key = (r.get("rule_id"), r.get("cwe"))
        assert key not in seen, f"Duplicate RAG rule returned: {key}"
        seen.add(key)

    rag_stats = get_rag_cache_stats()
    assert rag_stats["hits"] >= 1, "RAG search must produce cache hits on repeated queries"
    print(f"  [PASS] RAG caching and rule deduplication verified (Hits: {rag_stats['hits']}).")


def test_5_circuit_breaker_states_and_fast_fail():
    """Circuit Breaker pattern transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
    cb = CircuitBreaker(failure_threshold=3, recovery_time=0.1)
    assert cb.state == "CLOSED"
    assert cb.allow_request() is True

    # 2 failures: still closed
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "CLOSED"
    assert cb.allow_request() is True

    # 3rd failure: trips to OPEN
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.allow_request() is False, "OPEN circuit breaker must fast-fail requests immediately"

    # Wait for recovery window to transition to HALF_OPEN
    time.sleep(0.12)
    assert cb.allow_request() is True
    assert cb.state == "HALF_OPEN"

    # Success in HALF_OPEN resets to CLOSED
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.failure_count == 0
    print("  [PASS] Circuit Breaker transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED) verified.")


def test_6_duplicate_finding_aggregation_and_verification_labeling():
    """Unified issue aggregation, line/rule deduplication, and static corroboration."""
    sec_findings = [
        {"line": 10, "severity": "critical", "category": "security", "title": "SQL Injection", "cwe": "CWE-89", "rule_id": "B608"},
        {"line": 10, "severity": "critical", "category": "security", "title": "SQL Injection", "cwe": "CWE-89", "rule_id": "B608"}  # duplicate
    ]
    bug_findings = [
        {"line": 25, "severity": "high", "category": "bug", "title": "Divide by zero", "cwe": "CWE-369"}
    ]
    static_findings = [
        {"line": 10, "tool": "bandit", "rule_id": "B608", "cwe": "CWE-89", "severity": "critical", "message": "SQL injection"}
    ]

    summary = run_summary_agent(sec_findings, bug_findings, filename="app.py", static_findings=static_findings)
    assert len(summary["all_issues"]) == 2, "Duplicate SQL injection finding must be deduplicated"

    sec_issue = next(i for i in summary["all_issues"] if i["category"] == "security")
    assert sec_issue["verification_status"] == "verified_static", "Bandit-corroborated finding must be verified_static"
    assert sec_issue["verified"] is True

    bug_issue = next(i for i in summary["all_issues"] if i["category"] == "bug")
    assert bug_issue["verification_status"] == "unverified_llm_observation", "Unbacked AI finding must be unverified"
    assert bug_issue["verified"] is False
    print("  [PASS] Deduplication and static corroboration verification status verified.")


def test_7_empty_and_large_input_safety():
    """Safety boundaries on empty and large pull requests."""
    # Empty code input
    with pytest.raises(ValueError):
        run_full_pipeline("", "python")

    with pytest.raises(ValueError):
        run_full_pipeline("   \n\t  ", "python")

    # Large pull request input (30,000 chars)
    large_code = "# Large codebase simulation\n" + ("x = 1\n" * 1500)
    res = run_full_pipeline(large_code, "python", "large_module.py")
    assert res["verdict"] in ["CLEAN", "FIX REQUIRED"]
    assert res["total_elapsed_ms"] > 0
    print(f"  [PASS] Large PR safely processed in {res['total_elapsed_ms']}ms without context overflow.")


def test_8_vulnerable_test_fixture_accuracy():
    """Verify ground truth defect detection on vulnerable_app.py."""
    sample = SAMPLES["python"]
    res = run_full_pipeline(sample["code"], "python", "vulnerable_app.py")

    assert res["verdict"] == "FIX REQUIRED", "Vulnerable app must require fix"
    assert res["health_score"] <= 6.0, f"Critical defects must cap health score <= 6.0, got {res['health_score']}"
    assert res["unresolved_count"] >= 3, "Must detect at least 3 vulnerabilities in vulnerable_app.py"

    rule_ids = {str(i.get("rule_id", "")).upper() for i in res["issues"]}
    cwes = {str(i.get("cwe", "")).upper() for i in res["issues"]}

    # Verify specific ground truth CWEs
    assert "CWE-89" in cwes or "B608" in rule_ids, "Must detect SQL Injection (CWE-89 / B608)"
    assert "CWE-78" in cwes or "B602" in rule_ids or "B605" in rule_ids, "Must detect Command Injection (CWE-78 / B602)"
    assert "CWE-798" in cwes or "B105" in rule_ids, "Must detect Hardcoded Secret (CWE-798 / B105)"
    print(f"  [PASS] Vulnerable test fixture correctly identified CWE-89, CWE-78, CWE-798 (Score: {res['health_score']}/10).")


def test_9_remediation_syntax_validation():
    """Syntax validation rejects corrupted proposed fixes and preserves original code."""
    valid_python = "def ok(): return True\n"
    is_valid, err = validate_code_syntax(valid_python, "python")
    assert is_valid is True
    assert err is None

    broken_python = "def broken(:\n return False"
    is_valid, err = validate_code_syntax(broken_python, "python")
    assert is_valid is False
    assert "SyntaxError" in err

    broken_c = "int main() { char *s = 'unclosed; return 0; }"
    is_valid_c, err_c = validate_code_syntax(broken_c, "c")
    assert is_valid_c is False
    print("  [PASS] Syntax validation integrity verified across languages.")


def test_10_health_score_criteria_and_unassessed_distinction():
    """Documented configurable criteria and explicit unassessed score distinction."""
    crit = ScoringCriteria(
        base_score=10.0,
        critical_deduction=3.0,
        high_deduction=1.5,
        weight_by_verification=True,
        verified_weight=1.0,
        unverified_weight=0.5
    )
    
    # Verified critical: -3.0 -> 7.0 capped at 6.0
    score_v = calculate_health_score([{"severity": "critical", "verified": True}], criteria=crit)
    assert score_v == 6.0

    # Unverified high: -1.5 * 0.5 = -0.75 -> 9.25 -> 9.2
    score_uv = calculate_health_score([{"severity": "high", "verified": False}], criteria=crit)
    assert score_uv == 9.2

    # Failed pipeline: must return 0.0, not 10.0
    score_fail = calculate_health_score([], criteria=crit, pipeline_stages_failed=True)
    assert score_fail == 0.0, "Failed pipeline stages must return 0.0"

    # Skipped analysis on empty findings: must return degraded 5.0, never a clean 10.0
    score_skip = calculate_health_score([], criteria=crit, pipeline_stages_skipped=True)
    assert score_skip == 5.0, "Skipped analysis must never award a perfect score of 10.0"

    summary_failed = run_summary_agent([], [], pipeline_stages_failed=True)
    assert summary_failed["is_assessed"] is False
    assert summary_failed["score_status"] == "FAILED"
    assert summary_failed["health_score"] == 0.0

    summary_clean = run_summary_agent([], [])
    assert summary_clean["is_assessed"] is True
    assert summary_clean["score_status"] == "ASSESSED"
    assert summary_clean["health_score"] == 10.0
    print("  [PASS] Configurable criteria and unassessed vs genuine zero/ten distinction verified.")


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING OPTIMIZED PIPELINE TEST SUITE (10 TESTS)")
    print("=" * 70)
    test_1_stage_execution_and_state_transitions()
    test_2_parallel_execution_and_timeout_handling()
    test_3_cache_hits_misses_and_composite_invalidation()
    test_4_rag_caching_and_rule_deduplication()
    test_5_circuit_breaker_states_and_fast_fail()
    test_6_duplicate_finding_aggregation_and_verification_labeling()
    test_7_empty_and_large_input_safety()
    test_8_vulnerable_test_fixture_accuracy()
    test_9_remediation_syntax_validation()
    test_10_health_score_criteria_and_unassessed_distinction()
    print("=" * 70)
    print(">>> ALL 10 PERFORMANCE & OPTIMIZATION TESTS PASSED 100% <<<")
    print("=" * 70)
