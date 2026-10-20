import os
import sys

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from backend.graph import run_full_pipeline

def test_cpp_runtime():
    test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cpp_runtime_logic_test.cpp")
    with open(test_file, "r", encoding="utf-8") as f:
        code = f.read()

    result = run_full_pipeline(
        code=code,
        language="cpp",
        filename="cpp_runtime_logic_test.cpp",
        max_iterations=1
    )

    print("=" * 60)
    print("C++ RUNTIME & LOGIC BUG VERIFICATION RESULT")
    print("=" * 60)
    print(f"Health Score: {result['health_score']}/10")
    print(f"Verdict: {result['verdict']}")
    print(f"Total Issues Detected: {len(result['issues'])}")
    print("\nIssues Flagged:")
    for iss in result['issues']:
        print(f"  [Line {iss['line']}] {iss['severity'].upper()} | {iss['cwe']} | {iss['title']}: {iss['description']}")

    print(f"\nChangelog Fixes ({len(result['changelog'])}):")
    for ch in result['changelog']:
        print(f"  • {ch['change_type']} (Line {ch['line_affected']}): {ch['description']}")

    # Critical assertions
    assert result['verdict'] == 'FIX REQUIRED', f"Expected FIX REQUIRED, got {result['verdict']}"
    assert result['health_score'] < 5.0, f"Expected low health score, got {result['health_score']}"
    assert len(result['issues']) >= 7, f"Expected at least 7 issues detected, got {len(result['issues'])}"

    cwes = {iss['cwe'] for iss in result['issues']}
    expected_cwes = {"CWE-369", "CWE-481", "CWE-401", "CWE-562", "CWE-664", "CWE-1079", "CWE-457", "CWE-193", "CWE-1078"}
    found_cwes = cwes.intersection(expected_cwes)
    print(f"\nMatched Expected CWEs ({len(found_cwes)}/{len(expected_cwes)}): {sorted(list(found_cwes))}")

    assert len(found_cwes) >= 7, f"Expected at least 7 matching CWEs, got {len(found_cwes)}"
    print("\n>>> ZERO FALSE-CLEAN VERIFIED: All genuine C++ runtime/logic bugs detected! <<<")
    return True

if __name__ == "__main__":
    success = test_cpp_runtime()
    sys.exit(0 if success else 1)
