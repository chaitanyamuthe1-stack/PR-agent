"""
Test Suite Evaluation Harness for PR Agent.
Verifies detection accuracy, bug coverage, and ensures corrected code
matches the actual input test files without substituting preset samples.
"""

import os
import sys

# Ensure workspace root is in sys.path
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from backend.graph import run_full_pipeline

EXPECTED_BUGS = {
    "python": {
        "file": "test.py",
        "expected_count": 10,
        "cwes": ["CWE-89", "CWE-78", "CWE-798", "CWE-22", "CWE-369", "CWE-404", "CWE-1078", "CWE-390", "CWE-754"],
        "disallowed_content": ["def get_user_profile", "admin_token = \"AG_SECRET_ROOT_API_KEY_9921_X\""],
        "required_content": ["def calculate_analytics", "def register_user_tags", "def archive_reports"]
    },
    "cpp": {
        "file": "test.cpp",
        "expected_count": 10,
        "cwes": ["CWE-120", "CWE-798", "CWE-401", "CWE-476", "CWE-193", "CWE-457", "CWE-404", "CWE-338", "CWE-1078", "CWE-416"],
        "disallowed_content": ["void process_packet(const char* packet_data, int size)"],
        "required_content": ["void process_telemetry", "void process_network_packet"]
    },
    "java": {
        "file": "Test.java",
        "expected_count": 10,
        "cwes": ["CWE-89", "CWE-798", "CWE-404", "CWE-390", "CWE-595", "CWE-476", "CWE-1078", "CWE-22", "CWE-369", "CWE-362"],
        "disallowed_content": ["public class UserPaymentService"],
        "required_content": ["public class Test", "public void processAccount"]
    }
}

def run_evaluation():
    print("=" * 70)
    print("PR AGENT - MULTI-LANGUAGE TEST SUITE EVALUATION")
    print("=" * 70)

    test_dir = os.path.dirname(os.path.abspath(__file__))
    all_passed = True

    for lang, config in EXPECTED_BUGS.items():
        file_path = os.path.join(test_dir, config["file"])
        print(f"\n[+] Testing Language: {lang.upper()} ({config['file']})")
        print("-" * 50)

        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Run pipeline
        result = run_full_pipeline(
            code=code,
            language=lang,
            filename=config["file"],
            max_iterations=1
        )

        detected_issues = result.get("issues", [])
        corrected_code = result.get("corrected_code", "")
        changelog = result.get("changelog", [])
        health_score = result.get("health_score", 10.0)
        verdict = result.get("verdict", "UNKNOWN")

        print(f"  • Initial Health Score: {health_score}/10 (Verdict: {verdict})")
        print(f"  • Issues Detected: {len(detected_issues)} (Expected: ~{config['expected_count']})")
        print(f"  • Changelog Fixes: {len(changelog)}")

        # 1. Verify that the output does NOT substitute the preset sample!
        sample_leak = False
        for bad_snippet in config["disallowed_content"]:
            if bad_snippet in corrected_code:
                print(f"  [FAIL] Detected preset sample snippet in output: '{bad_snippet}'")
                sample_leak = True
                all_passed = False

        if not sample_leak:
            print("  [PASS] Corrected code does NOT contain preset sample code (no sample substitution).")

        # 2. Verify that the output contains the actual test file functions/classes
        content_preserved = True
        for req_snippet in config["required_content"]:
            if req_snippet not in corrected_code:
                print(f"  [FAIL] Missing original code content in output: '{req_snippet}'")
                content_preserved = False
                all_passed = False

        if content_preserved:
            print("  [PASS] Corrected code preserves original test file structure and signatures.")

        # 3. Check CWE coverage
        detected_cwes = set()
        for issue in detected_issues:
            cwe = issue.get("cwe")
            if cwe:
                detected_cwes.add(cwe)

        print(f"  • Detected CWEs: {sorted(list(detected_cwes))}")
        matched_cwes = [c for c in config["cwes"] if c in detected_cwes]
        recall = (len(matched_cwes) / len(config["cwes"])) * 100
        print(f"  • Target CWE Coverage: {len(matched_cwes)}/{len(config['cwes'])} ({recall:.1f}%)")

        if recall >= 70.0:
            print(f"  [PASS] {lang.upper()} bug detection coverage passed threshold (>= 70%).")
        else:
            print(f"  [WARN] {lang.upper()} bug detection coverage below 70%.")

    print("\n" + "=" * 70)
    if all_passed:
        print(">>> ALL TEST SUITE EVALUATIONS PASSED SUCCESSFULLY! <<<")
    else:
        print(">>> SOME CHECKS FAILED - REVIEW LOGS ABOVE <<<")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)
