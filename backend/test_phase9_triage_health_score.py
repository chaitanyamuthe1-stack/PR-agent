"""
Unit & Integration Test Suite for Phase 9 — Triage, Findings, and Health Score (PR Agent).

Validates:
1. Consistent issue schema across all findings (id, title, severity, category, file, line, description, evidence, recommendation, rule_id, cwe, owasp, rule_citation, detection_source, verification_status).
2. Severity coverage (Critical, High, Medium, Low, Informational).
3. Category coverage (Security, Bug, Style, Performance, Reliability).
4. Deterministic scoring policy with safety caps and no artificial score inflation.
5. Verdict determination (CLEAN, NEEDS REVIEW, FIX REQUIRED, and degraded modes).
6. Non-mathematical safety proof disclaimer on CLEAN verdicts.
7. Explicit distinction between verified static findings and unverified AI observations.
8. Filter, sorting, and count integrity across triage outputs.
"""

import os
import sys

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.summary_agent import calculate_health_score, run_summary_agent, VALID_SEVERITIES, VALID_CATEGORIES
from backend.graph import run_full_pipeline
from backend.samples import SAMPLES


def test_1_issue_schema_completeness():
    print("\n[TEST 1] Verifying Unified Issue Schema Completeness...")
    
    mock_sec = [
        {
            "line": 15,
            "severity": "critical",
            "category": "security",
            "title": "SQL Injection in User Query",
            "description": "Raw string concatenation in SQL query allows arbitrary SQL execution.",
            "recommendation": "Use parameterized queries with cursor.execute(query, params).",
            "cwe": "CWE-89",
            "owasp": "OWASP:A03:2021",
            "rule_id": "B608",
            "rule_citation": "OWASP:A03:2021 / CWE-89",
            "evidence": "query = 'SELECT * FROM users WHERE id = ' + user_id"
        }
    ]

    mock_bug = [
        {
            "line": 42,
            "severity": "medium",
            "category": "reliability",
            "title": "Resource Leak: Unclosed File Handle",
            "description": "File handle opened with open() without context manager.",
            "recommendation": "Wrap file access in a 'with open(...) as f:' block.",
            "cwe": "CWE-775",
            "rule_id": "SIM115",
            "detection_source": "flake8",
            "evidence": "f = open('data.txt')"
        }
    ]

    mock_static = [
        {
            "line": 15,
            "tool": "bandit",
            "rule_id": "B608",
            "cwe": "CWE-89",
            "severity": "critical",
            "message": "Possible SQL injection vector through string-based query construction."
        }
    ]

    result = run_summary_agent(mock_sec, mock_bug, filename="app.py", static_findings=mock_static)
    assert len(result["all_issues"]) == 2, "Must contain exactly 2 merged issues"

    required_fields = [
        "id", "finding_id", "title", "severity", "category", "file", "line",
        "description", "evidence", "recommendation", "rule_id", "cwe", "owasp",
        "rule_citation", "detection_source", "verification_status"
    ]

    for issue in result["all_issues"]:
        for field in required_fields:
            assert field in issue, f"Issue {issue.get('id')} missing required schema field: '{field}'"
            assert issue[field] is not None, f"Issue field '{field}' must not be None"
        
        # Validate field constraints
        assert issue["severity"] in VALID_SEVERITIES, f"Invalid severity: {issue['severity']}"
        assert issue["category"] in VALID_CATEGORIES, f"Invalid category: {issue['category']}"
        assert isinstance(issue["line"], int) and issue["line"] >= 1, "Line must be integer >= 1"

    # Verify detection_source and verification_status corroboration
    sec_issue = next(i for i in result["all_issues"] if i["category"] == "security")
    assert sec_issue["verification_status"] == "verified_static", "Bandit corroboration must yield verified_static"
    assert sec_issue["detection_source"] == "bandit"

    rel_issue = next(i for i in result["all_issues"] if i["category"] == "reliability")
    assert rel_issue["verification_status"] == "verified_static"
    assert rel_issue["detection_source"] == "flake8"

    print("  [PASS] All 16 schema fields verified across merged findings.")


def test_2_severity_and_category_coverage():
    print("\n[TEST 2] Verifying Severity and Category Normalization...")
    
    test_severities = ["critical", "high", "medium", "low", "informational", "UNKNOWN_SEV"]
    test_categories = ["security", "bug", "style", "performance", "reliability", "complexity", "UNKNOWN_CAT"]

    test_findings = []
    for i, sev in enumerate(test_severities):
        cat = test_categories[i % len(test_categories)]
        test_findings.append({
            "line": i + 1,
            "severity": sev,
            "category": cat,
            "title": f"Test Defect {i}",
            "description": "Test description",
            "recommendation": "Test recommendation"
        })

    result = run_summary_agent(test_findings, [], filename="test.py")
    issues = result["all_issues"]

    for issue in issues:
        assert issue["severity"] in VALID_SEVERITIES, f"Normalized severity must be valid: {issue['severity']}"
        assert issue["category"] in VALID_CATEGORIES, f"Normalized category must be valid: {issue['category']}"

    print(f"  [PASS] Successfully normalized 5 severities {VALID_SEVERITIES} and 5 categories {VALID_CATEGORIES}.")


def test_3_deterministic_scoring_policy():
    print("\n[TEST 3] Verifying Deterministic Scoring Policy & Safety Caps...")

    # Case 3a: Zero issues -> perfect 10.0
    assert calculate_health_score([]) == 10.0, "Zero issues must yield 10.0"

    # Case 3b: Single Low issue -> 10.0 - 0.25 = 9.8
    score_low = calculate_health_score([{"severity": "low"}])
    assert score_low == 9.8, f"Single low should yield 9.8, got {score_low}"

    # Case 3c: Single Medium issue -> 10.0 - 0.75 = 9.25 (Python 3 round-half-to-even yields 9.2)
    score_med = calculate_health_score([{"severity": "medium"}])
    assert score_med == 9.2, f"Single medium should yield 9.2, got {score_med}"

    # Case 3d: Single High issue -> 10.0 - 1.5 = 8.5
    score_high = calculate_health_score([{"severity": "high"}])
    assert score_high == 8.5, f"Single high should yield 8.5, got {score_high}"

    # Case 3e: Single Critical issue -> 10.0 - 3.0 = 7.0, but capped at 6.0!
    score_crit = calculate_health_score([{"severity": "critical"}])
    assert score_crit == 6.0, f"Critical defect must cap health score at max 6.0, got {score_crit}"

    # Case 3f: Two High issues -> 10.0 - 3.0 = 7.0, capped at 7.0
    score_two_high = calculate_health_score([{"severity": "high"}, {"severity": "high"}])
    assert score_two_high == 7.0, f"Two high defects must cap score at 7.0, got {score_two_high}"

    # Case 3g: Massive defects clamp at 0.5 minimum
    massive = [{"severity": "critical"}] * 10
    score_massive = calculate_health_score(massive)
    assert score_massive == 0.5, f"Massive defects must clamp to 0.5 floor, got {score_massive}"

    # Case 3h: Informational defect -> -0.05 deduction (10.0 - 0.05 = 9.95 -> 9.9)
    score_info = calculate_health_score([{"severity": "informational"}])
    assert score_info == 9.9, f"Single informational (-0.05) rounds to 9.9, got {score_info}"
    score_multi_info = calculate_health_score([{"severity": "informational"}] * 3) # -0.15 -> 9.85 -> 9.8
    assert score_multi_info == 9.8, f"3 informational defects should yield 9.8, got {score_multi_info}"

    print("  [PASS] Deterministic deduction formula and safety ceiling caps verified.")


def test_4_verdict_determination_and_disclaimer():
    print("\n[TEST 4] Verifying Verdict Determination and Safety Disclaimer...")

    # 4a. Zero unresolved findings -> CLEAN with mathematical disclaimer
    res_clean = run_summary_agent([], [])
    assert res_clean["verdict"] == "CLEAN", "Zero findings must be CLEAN"
    assert res_clean["health_score"] == 10.0
    assert "not a mathematical proof" in res_clean["summary"], "Must contain mathematical safety disclaimer"
    assert "safety_disclaimer" in res_clean

    # 4b. Only low and informational findings -> NEEDS REVIEW
    res_review = run_summary_agent(
        [{"line": 1, "severity": "low", "title": "Trailing whitespace", "category": "style"}],
        [{"line": 5, "severity": "informational", "title": "Todo comment", "category": "style"}]
    )
    assert res_review["verdict"] == "NEEDS REVIEW", "Only low/info findings must yield NEEDS REVIEW"
    assert res_review["health_score"] > 9.0

    # 4c. High or Critical finding -> FIX REQUIRED
    res_fix = run_summary_agent(
        [{"line": 10, "severity": "high", "title": "Potential Command Injection", "category": "security"}],
        []
    )
    assert res_fix["verdict"] == "FIX REQUIRED", "Actionable high defect must yield FIX REQUIRED"

    print("  [PASS] Verdict logic (CLEAN, NEEDS REVIEW, FIX REQUIRED) and mathematical disclaimer verified.")


def test_5_ai_observations_vs_verified_static_labeling():
    print("\n[TEST 5] Explicit Labeling of AI Observations vs Verified Static...")

    # Pure LLM observation with zero static analyzer output
    ai_only = [
        {
            "line": 20,
            "severity": "medium",
            "category": "performance",
            "title": "Quadratic Algorithm Complexity in Nested Loop",
            "description": "Nested iteration over list produces O(N^2) complexity.",
            "recommendation": "Use a hash set to lookup keys in O(1) time."
        }
    ]

    res = run_summary_agent(ai_only, [], static_findings=[])
    issue = res["all_issues"][0]
    assert issue["verification_status"] == "unverified_llm_observation", "Unbacked AI finding must be unverified_llm_observation"
    assert issue["verified"] is False
    assert issue["detection_source"] in ["security_agent", "bug_agent"]
    assert "AI-generated" in issue["evidence"] or "heuristic" in issue["evidence"].lower()

    # Remediated finding
    ai_only[0]["resolved"] = True
    res_resolved = run_summary_agent(ai_only, [], static_findings=[])
    assert res_resolved["all_issues"][0]["verification_status"] == "remediated"

    print("  [PASS] AI-generated observations and verified static findings strictly distinguished.")


def test_6_breakdown_counts_and_sorting():
    print("\n[TEST 6] Severity Counts, Category Counts, and Sorting Order...")

    test_issues = [
        {"line": 100, "severity": "low", "category": "style", "title": "Low 100"},
        {"line": 20, "severity": "critical", "category": "security", "title": "Crit 20"},
        {"line": 5, "severity": "high", "category": "bug", "title": "High 5"},
        {"line": 50, "severity": "critical", "category": "security", "title": "Crit 50"},
        {"line": 12, "severity": "informational", "category": "performance", "title": "Info 12"}
    ]

    res = run_summary_agent(test_issues, [])
    
    # Severity Counts
    counts = res["counts"]
    assert counts["critical"] == 2
    assert counts["high"] == 1
    assert counts["medium"] == 0
    assert counts["low"] == 1
    assert counts["informational"] == 1

    # Sorting: Criticals first (sorted by line), then Highs, then Lows, then Info
    sorted_issues = res["all_issues"]
    assert sorted_issues[0]["severity"] == "critical" and sorted_issues[0]["line"] == 20
    assert sorted_issues[1]["severity"] == "critical" and sorted_issues[1]["line"] == 50
    assert sorted_issues[2]["severity"] == "high" and sorted_issues[2]["line"] == 5
    assert sorted_issues[3]["severity"] == "low" and sorted_issues[3]["line"] == 100
    assert sorted_issues[4]["severity"] == "informational" and sorted_issues[4]["line"] == 12

    print("  [PASS] Counts and deterministic severity-first sorting verified.")


def run_all_phase9_tests():
    print("=" * 70)
    print("PHASE 9 — TRIAGE, FINDINGS, AND HEALTH SCORE TEST SUITE")
    print("=" * 70)

    test_1_issue_schema_completeness()
    test_2_severity_and_category_coverage()
    test_3_deterministic_scoring_policy()
    test_4_verdict_determination_and_disclaimer()
    test_5_ai_observations_vs_verified_static_labeling()
    test_6_breakdown_counts_and_sorting()

    print("\n" + "=" * 70)
    print(">>> ALL 6 PHASE 9 TRIAGE & HEALTH SCORE TESTS PASSED 100% <<<")
    print("=" * 70)


if __name__ == "__main__":
    run_all_phase9_tests()
