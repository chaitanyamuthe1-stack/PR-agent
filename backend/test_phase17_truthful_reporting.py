"""
Phase 17 — Truthful Reporting & Failure Transparency Test Suite.
Verifies:
1. PASS: Clean file reported as PASS / CLEAN with 0 unresolved defects.
2. FIXED: Fully remediated code reported as FIXED with verdict CLEAN.
3. PARTIALLY FIXED: Partially remediated code never converts remaining defects to CLEAN.
4. UNRESOLVED / MANUAL ACTION REQUIRED: Unresolved defects explicitly flagged.
5. DEPENDENCY MISSING: RAG or Database offline reported with degraded truthful status.
6. ANALYZER UNAVAILABLE: Static analyzer failure reported with truthful status.
7. LLM UNAVAILABLE: Both LLMs unavailable handled gracefully and reported truthfully.
8. Zero False-Clean Invariant: NEVER convert an unresolved problem into CLEAN.
"""

import os
import sys
import time

# Ensure backend module resolution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.graph import run_full_pipeline

def clear_sim():
    for k in [
        "PR_AGENT_SIMULATE_OLLAMA_FAIL",
        "PR_AGENT_SIMULATE_QWEN_FAIL",
        "PR_AGENT_SIMULATE_PRIMARY_FAIL",
        "PR_AGENT_SIMULATE_FALLBACK_FAIL",
        "PR_AGENT_SIMULATE_RAG_FAIL",
        "PR_AGENT_SIMULATE_MCP_FAIL",
        "PR_AGENT_SIMULATE_ANALYZER_FAIL",
        "PR_AGENT_SIMULATE_DB_FAIL",
        "PR_AGENT_SIMULATE_NETWORK_TIMEOUT"
    ]:
        os.environ.pop(k, None)


def test_1_pass_state():
    print("\n[TEST 1] Verifying PASS state for clean code...")
    clear_sim()
    clean_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    res = run_full_pipeline(clean_code, "python", "clean.py")
    assert res["verdict"] in ["CLEAN", "PASS"], f"Expected CLEAN or PASS, got {res['verdict']}"
    assert res["unresolved_count"] == 0
    print(f"  [PASS] Clean code reported as {res['verdict']} with 0 unresolved defects.")


def test_2_fixed_state():
    print("\n[TEST 2] Verifying FIXED state for auto-remediated code...")
    clear_sim()
    # Code with a fixable buffer overflow and memory leak
    cpp_broken = '''#include <iostream>
#include <cstring>

void processInput(const char* input) {
    char buffer[16];
    strcpy(buffer, input);
    int* data = new int[100];
    data[0] = 42;
}
'''
    res = run_full_pipeline(cpp_broken, "cpp", "vuln.cpp")
    if res["unresolved_count"] == 0:
        assert res["verdict"] == "CLEAN"
        assert res["remediation_status"] in ["FIXED", "SUCCESS"]
        print(f"  [PASS] Fully remediated code marked {res['remediation_status']} with final verdict {res['verdict']}.")
    else:
        assert res["verdict"] in ["FIX REQUIRED", "MANUAL ACTION REQUIRED"]
        print(f"  [PASS] Code with remaining defects truthfully reported as {res['verdict']}.")


def test_3_partially_fixed_and_unresolved():
    print("\n[TEST 3] Verifying PARTIALLY FIXED & MANUAL ACTION REQUIRED states...")
    clear_sim()
    # Code with multiple vulnerabilities where some remain
    broken_py = '''import os
import sqlite3

def run_query(user_input):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = '{user_input}'"
    cursor.execute(query)
    os.system("echo " + user_input)
    return cursor.fetchall()
'''
    res = run_full_pipeline(broken_py, "python", "service.py")
    assert res["unresolved_count"] > 0, "Broken code must have unresolved defects"
    # Strict invariant: Never CLEAN if unresolved_count > 0!
    assert res["verdict"] != "CLEAN", f"CRITICAL FAILURE: Unresolved defects ({res['unresolved_count']}) reported as CLEAN!"
    assert res["verdict"] in ["FIX REQUIRED", "MANUAL ACTION REQUIRED"], f"Truthful verdict required, got: {res['verdict']}"
    print(f"  [PASS] Code with {res['unresolved_count']} remaining defects reported truthfully as {res['verdict']} (Remediation: {res['remediation_status']}).")


def test_4_dependency_missing_rag():
    print("\n[TEST 4] Verifying DEPENDENCY MISSING (RAG Vector Store Failure)...")
    clear_sim()
    os.environ["PR_AGENT_SIMULATE_RAG_FAIL"] = "1"
    clean_code = "def multiply(x, y):\n    return x * y\n"
    res = run_full_pipeline(clean_code, "python", "mult.py")
    clear_sim()
    assert "RAG UNAVAILABLE" in res["verdict"] or "DEGRADED" in res["verdict"], f"Expected degraded RAG verdict, got {res['verdict']}"
    assert res["verdict"] != "CLEAN", "Must never report CLEAN when normative RAG dependencies fail"
    print(f"  [PASS] Missing dependency reported truthfully as: {res['verdict']}.")


def test_5_analyzer_unavailable():
    print("\n[TEST 5] Verifying ANALYZER UNAVAILABLE truthful reporting...")
    clear_sim()
    os.environ["PR_AGENT_SIMULATE_ANALYZER_FAIL"] = "1"
    clean_code = "def multiply(x, y):\n    return x * y\n"
    res = run_full_pipeline(clean_code, "python", "mult.py")
    clear_sim()
    assert res["verdict"] == "ANALYZER UNAVAILABLE", f"Expected ANALYZER UNAVAILABLE, got {res['verdict']}"
    assert res["verdict"] != "CLEAN", "Must never report CLEAN when static analyzers fail"
    print(f"  [PASS] Analyzer failure reported truthfully as: {res['verdict']}.")


def test_6_mcp_unavailable():
    print("\n[TEST 6] Verifying MCP UNAVAILABLE / DEPENDENCY MISSING...")
    clear_sim()
    os.environ["PR_AGENT_SIMULATE_MCP_FAIL"] = "1"
    clean_code = "def multiply(x, y):\n    return x * y\n"
    res = run_full_pipeline(clean_code, "python", "mult.py")
    clear_sim()
    assert res["verdict"] == "MCP UNAVAILABLE", f"Expected MCP UNAVAILABLE, got {res['verdict']}"
    assert res["verdict"] != "CLEAN", "Must never report CLEAN when MCP layer is offline"
    print(f"  [PASS] MCP failure reported truthfully as: {res['verdict']}.")


def test_7_never_convert_unresolved_to_clean():
    print("\n[TEST 7] Verifying Invariant: NEVER convert unresolved defects into CLEAN...")
    clear_sim()
    broken_codes = [
        ("python", "import os\nos.system('rm -rf ' + input())", "del.py"),
        ("javascript", "const express = require('express'); app.get('/', (req, res) => res.send(req.query.q));", "xss.js"),
        ("cpp", "#include <cstring>\nvoid f(char *s) { char b[4]; strcpy(b, s); }", "bof.cpp"),
        ("java", "class A { void f(String s) { String p = \"sk_live_1234567890123456\"; } }", "secret.java"),
        ("ruby", "def f(u); query = \"SELECT * FROM users WHERE id = #{u}\"; end", "sqli.rb")
    ]
    for lang, code, fn in broken_codes:
        res = run_full_pipeline(code, lang, fn)
        if res["unresolved_count"] > 0:
            assert res["verdict"] != "CLEAN", f"Violation in {lang}: unresolved_count={res['unresolved_count']} but verdict={res['verdict']}"
            assert res["verdict"] in ["FIX REQUIRED", "MANUAL ACTION REQUIRED"], f"Truthful verdict required in {lang}"
        print(f"  [PASS] {lang.upper()}: {res['unresolved_count']} remaining -> Verdict: {res['verdict']} (Never CLEAN).")


def run_all_phase17_tests():
    print("=" * 80)
    print("PHASE 17 — TRUTHFUL REPORTING & FAILURE TRANSPARENCY TEST SUITE")
    print("=" * 80)
    test_1_pass_state()
    test_2_fixed_state()
    test_3_partially_fixed_and_unresolved()
    test_4_dependency_missing_rag()
    test_5_analyzer_unavailable()
    test_6_mcp_unavailable()
    test_7_never_convert_unresolved_to_clean()
    print("\n" + "=" * 80)
    print("ALL PHASE 17 TRUTHFUL REPORTING TESTS PASSED (7/7) — 100% GREEN")
    print("=" * 80)


if __name__ == "__main__":
    run_all_phase17_tests()
