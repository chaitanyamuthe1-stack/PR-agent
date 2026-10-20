"""
Phase 16 — Final Full End-to-End Test Suite.
Executes complete pipeline across:
- Clean Python file
- Broken Python file
- Clean C++ file
- Broken C++ file
- Clean Java file
- Broken Java file
- Clean JavaScript file
- Broken JavaScript file
- Clean Ruby file
- Broken Ruby file

Records for each test:
- Language
- Analyzer used
- Findings detected
- Expected findings
- Actual findings
- LLM provider
- LLM model
- Auto-fix attempted
- Code changed
- Re-check result
- Remaining issues
- Final verdict
"""

import os
import sys
import json
import time

# Ensure backend module resolution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.graph import run_full_pipeline
from backend.mcp_tools import get_mcp_tools_for_language

# --------------------------------------------------------------------------
# Test Test Cases Definition (Clean & Broken across all 5 languages)
# --------------------------------------------------------------------------
TEST_CASES = [
    {
        "id": "py-clean",
        "name": "Clean Python File",
        "lang": "python",
        "filename": "geometry.py",
        "expected_findings": 0,
        "expected_verdict": "CLEAN",
        "code": '''def calculate_area(length: float, width: float) -> float:
    """Calculates the rectangular area given length and width."""
    if length < 0 or width < 0:
        raise ValueError("Dimensions must be non-negative")
    return float(length * width)
'''
    },
    {
        "id": "py-broken",
        "name": "Broken Python File",
        "lang": "python",
        "filename": "vuln_service.py",
        "expected_findings": 2,
        "expected_verdict": "FIX REQUIRED",
        "code": '''import os
import sqlite3

def run_query(user_input):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = '{user_input}'"
    cursor.execute(query)
    os.system("echo " + user_input)
    return cursor.fetchall()
'''
    },
    {
        "id": "cpp-clean",
        "name": "Clean C++ File",
        "lang": "cpp",
        "filename": "SafeCalculator.cpp",
        "expected_findings": 0,
        "expected_verdict": "CLEAN",
        "code": '''#include <iostream>
#include <string>
#include <memory>

class SafeCalculator {
public:
    static double computeArea(double length, double width) {
        if (length < 0.0 || width < 0.0) {
            return 0.0;
        }
        return length * width;
    }
};
'''
    },
    {
        "id": "cpp-broken",
        "name": "Broken C++ File",
        "lang": "cpp",
        "filename": "vuln_buffer.cpp",
        "expected_findings": 2,
        "expected_verdict": "FIX REQUIRED",
        "code": '''#include <iostream>
#include <cstring>

void processInput(const char* input) {
    char buffer[16];
    strcpy(buffer, input);
    int* data = new int[100];
    data[0] = 42;
}
'''
    },
    {
        "id": "java-clean",
        "name": "Clean Java File",
        "lang": "java",
        "filename": "OrderValidator.java",
        "expected_findings": 0,
        "expected_verdict": "CLEAN",
        "code": '''package com.example;

public class OrderValidator {
    public static boolean isValidQuantity(int quantity) {
        return quantity > 0 && quantity <= 10000;
    }
}
'''
    },
    {
        "id": "java-broken",
        "name": "Broken Java File",
        "lang": "java",
        "filename": "BrokenService.java",
        "expected_findings": 2,
        "expected_verdict": "FIX REQUIRED",
        "code": '''package com.example;

import java.sql.Connection;
import java.sql.Statement;

public class BrokenService {
    public void executeQuery(Connection conn, String userInput) throws Exception {
        Statement stmt = conn.createStatement();
        stmt.executeUpdate("DELETE FROM accounts WHERE id = '" + userInput + "'");
        String DB_SECRET = "sk_live_9921388481928371";
    }
}
'''
    },
    {
        "id": "js-clean",
        "name": "Clean JavaScript File",
        "lang": "javascript",
        "filename": "discount.js",
        "expected_findings": 0,
        "expected_verdict": "CLEAN",
        "code": '''export function calculateDiscount(price, rate) {
    if (typeof price !== 'number' || typeof rate !== 'number') {
        throw new TypeError('Arguments must be numbers');
    }
    const safeRate = Math.min(Math.max(rate, 0), 1);
    return Number((price * (1 - safeRate)).toFixed(2));
}
'''
    },
    {
        "id": "js-broken",
        "name": "Broken JavaScript File",
        "lang": "javascript",
        "filename": "server_routes.js",
        "expected_findings": 2,
        "expected_verdict": "FIX REQUIRED",
        "code": '''const express = require('express');
const app = express();

app.get('/search', (req, res) => {
    res.send("<h1>Search Results for: " + req.query.q + "</h1>");
    const API_KEY = "sec_live_9876543210123456";
});
'''
    },
    {
        "id": "ruby-clean",
        "name": "Clean Ruby File",
        "lang": "ruby",
        "filename": "geometry.rb",
        "expected_findings": 0,
        "expected_verdict": "CLEAN",
        "code": '''# frozen_string_literal: true

module Geometry
  def self.rectangle_area(width, height)
    return 0.0 if width.negative? || height.negative?

    width.to_f * height.to_f
  end
end
'''
    },
    {
        "id": "ruby-broken",
        "name": "Broken Ruby File",
        "lang": "ruby",
        "filename": "database_helper.rb",
        "expected_findings": 2,
        "expected_verdict": "FIX REQUIRED",
        "code": '''def search_records(db, user_param)
  query = "SELECT * FROM users WHERE username = '#{user_param}'"
  db.execute(query)
  API_KEY = "sk_live_9988776655443322"
end
'''
    }
]


def run_phase16_full_suite():
    print("=" * 80)
    print("PHASE 16 — FINAL FULL TEST SUITE (END-TO-END EXECUTION)")
    print("=" * 80)

    results = []

    for idx, tc in enumerate(TEST_CASES, 1):
        print(f"\n[{idx}/10] Testing {tc['name']} ({tc['lang'].upper()}) [{tc['filename']}]...")
        start_t = time.time()

        # Run pipeline
        res = run_full_pipeline(
            code=tc["code"],
            language=tc["lang"],
            filename=tc["filename"],
            max_iterations=2
        )
        elapsed = round((time.time() - start_t) * 1000, 2)

        # Telemetry Extraction
        mcp_tools = res.get("mcp_tools", get_mcp_tools_for_language(tc["lang"]))
        analyzer_used = ", ".join(mcp_tools)
        
        all_issues = res.get("all_issues") or res.get("issues") or []
        unresolved_issues = [i for i in all_issues if not i.get("resolved")]
        resolved_issues = [i for i in all_issues if i.get("resolved")]
        
        findings_detected = len(all_issues)
        unresolved_count = len(unresolved_issues)
        
        gw_info = res.get("gateway_info", {})
        llm_provider = gw_info.get("provider", "OFFLINE_HEURISTIC")
        llm_model = gw_info.get("model", "pr-agent-deterministic-v1")
        
        auto_fix_attempted = (res.get("iteration_count", 0) > 0) or (res.get("remediation_status") in ["SUCCESS", "PARTIAL", "FAILED"])
        code_changed = (res.get("corrected_code", "").strip() != tc["code"].strip())
        
        # Re-check result determination
        if not auto_fix_attempted:
            recheck_result = "N/A (No defects)"
        elif unresolved_count == 0 and findings_detected > 0:
            recheck_result = f"PASSED (All {findings_detected} defect(s) resolved)"
        elif res.get("remediation_status") == "SUCCESS":
            recheck_result = "PASSED"
        else:
            recheck_result = f"INCOMPLETE ({unresolved_count} defect(s) remaining)"

        final_verdict = res.get("verdict", "PENDING")

        # Validation assertions
        if tc["expected_verdict"] == "CLEAN":
            assert final_verdict == "CLEAN", f"Expected CLEAN for {tc['name']}, got {final_verdict}"
            assert unresolved_count == 0, f"Expected 0 unresolved for {tc['name']}, got {unresolved_count}"
        else:
            assert findings_detected >= tc["expected_findings"], f"Expected >= {tc['expected_findings']} for {tc['name']}, got {findings_detected}"

        record = {
            "test_id": tc["id"],
            "test_name": tc["name"],
            "language": tc["lang"],
            "analyzer_used": analyzer_used,
            "findings_detected": findings_detected,
            "expected_findings": tc["expected_findings"],
            "actual_findings": findings_detected,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "auto_fix_attempted": auto_fix_attempted,
            "code_changed": code_changed,
            "recheck_result": recheck_result,
            "remaining_issues": unresolved_count,
            "final_verdict": final_verdict,
            "health_score": res.get("health_score"),
            "post_fix_score": res.get("post_fix_score"),
            "latency_ms": elapsed
        }
        results.append(record)

        print(f"  - Analyzer Used:      {analyzer_used}")
        print(f"  - Findings Detected:  {findings_detected} (Expected: {tc['expected_findings']})")
        print(f"  - LLM Provider:       {llm_provider} ({llm_model})")
        print(f"  - Auto-fix Attempted: {auto_fix_attempted} | Code Changed: {code_changed}")
        print(f"  - Re-check Result:    {recheck_result}")
        print(f"  - Remaining Issues:   {unresolved_count}")
        print(f"  - Final Verdict:      {final_verdict} (Initial Score: {res.get('health_score')}, Post-Fix: {res.get('post_fix_score')})")
        print(f"  - Latency:            {elapsed}ms")

    print("\n" + "=" * 80)
    print("PHASE 16 TEST MATRIX SUMMARY TABLE")
    print("=" * 80)
    header = f"{'Language':<11} | {'Test Name':<23} | {'Analyzer':<16} | {'Det':<3} | {'LLM Provider':<18} | {'AutoFix':<7} | {'Changed':<7} | {'Remaining':<9} | {'Verdict':<12}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['language']:<11} | {r['test_name']:<23} | {r['analyzer_used']:<16} | {r['findings_detected']:<3} | {r['llm_provider']:<18} | {str(r['auto_fix_attempted']):<7} | {str(r['code_changed']):<7} | {r['remaining_issues']:<9} | {r['final_verdict']:<12}")

    # Output JSON records to stdout for programmatic parsing if needed
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phase16_test_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Full Phase 16 records saved to: {json_path}")
    print("=" * 80)
    print("ALL 10 END-TO-END TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_phase16_full_suite()
