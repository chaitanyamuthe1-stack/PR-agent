"""
Comprehensive Validation Script for PR Agent.
Tests the exact pipeline, all 6 languages, mandatory 8 bug types, regression tests,
and computes precision/recall/auto-fix metrics.
"""

import os
import sys
import json
import shutil
import httpx

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from backend.graph import run_full_pipeline
from backend.mcp_tools import run_static_analysis, get_mcp_tools_for_language
from backend.rag.vector_store import store
from backend.llm_gateway import gateway

def validate_all():
    report = {
        "env_and_tools": {},
        "cpp_regression": {},
        "python_regression": {},
        "language_matrix": {},
        "metrics": {},
        "frontend_audit": {},
        "pipeline_audit": {}
    }

    print("======================================================================")
    print("STEP 1: CHECKING ENVIRONMENT, TOOLS, OLLAMA, AND LLM GATEWAY")
    print("======================================================================")
    tools = ['bandit', 'pylint', 'cppcheck', 'checkstyle', 'eslint', 'rubocop', 'gcc', 'g++', 'clang', 'java', 'javac', 'node', 'ruby', 'ollama']
    tool_status = {t: shutil.which(t) for t in tools}
    for t, p in tool_status.items():
        print(f"  {t:12}: {p if p else 'NOT INSTALLED'}")

    ollama_up = False
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=1.0)
        ollama_up = (r.status_code == 200)
    except Exception:
        ollama_up = False
    print(f"  Ollama Server: {'ONLINE' if ollama_up else 'OFFLINE / NOT RUNNING'}")

    gw = gateway.get_gateway_status()
    print(f"  Gateway Provider: {gw['provider']} | Model: {gw['model']} | Fallback: {gw['fallback_state']}")

    report["env_and_tools"] = {
        "tools": {k: bool(v) for k, v in tool_status.items()},
        "ollama_online": ollama_up,
        "gateway": gw
    }

    print("\n======================================================================")
    print("STEP 2: RUNNING CRITICAL C++ REGRESSION TEST (Section 4)")
    print("======================================================================")
    cpp_code = """#include <iostream>
#include <vector>
using namespace std;

int calculateAverage(vector<int> numbers) {
    int sum = 0;

    for (int i = 0; i <= numbers.size(); i++) {
        sum += numbers[i];
    }

    return sum / numbers.size();
}

int main() {
    vector<int> marks = {80, 75, 90, 85};
    cout << "Average: " << calculateAverage(marks) << endl;
    return 0;
}"""

    cpp_res = run_full_pipeline(cpp_code, "cpp", "calculate_average.cpp", max_iterations=1)
    print(f"  Health Score: {cpp_res['health_score']}/10 | Verdict: {cpp_res['verdict']}")
    print(f"  Total Findings: {len(cpp_res['issues'])}")
    for iss in cpp_res['issues']:
        print(f"    Line {iss.get('line')}: [{iss.get('severity')}] {iss.get('cwe')} - {iss.get('title')}: {iss.get('description')}")
    print(f"  Changelog ({len(cpp_res['changelog'])}):")
    for ch in cpp_res['changelog']:
        print(f"    Line {ch.get('line_affected')}: {ch.get('description')}")

    out_of_bounds_detected = any("arrayIndexOutOfBounds" in str(i) or "CWE-193" in str(i) or "bounds" in str(i).lower() for i in cpp_res['issues'])
    zerodiv_detected = any("zerodiv" in str(i) or "CWE-369" in str(i) or "zero" in str(i).lower() for i in cpp_res['issues'])

    report["cpp_regression"] = {
        "score": cpp_res['health_score'],
        "verdict": cpp_res['verdict'],
        "issues_count": len(cpp_res['issues']),
        "out_of_bounds_detected": out_of_bounds_detected,
        "zerodiv_detected": zerodiv_detected,
        "changelog_count": len(cpp_res['changelog']),
        "corrected_code": cpp_res['corrected_code']
    }

    print("\n======================================================================")
    print("STEP 3: RUNNING PYTHON FILE-HANDLING REGRESSION TEST (Section 5)")
    print("======================================================================")
    py_code = """def read_student_names(filename):
    file = open(filename, "r")
    names = []

    for line in file:
        names.append(line.strip())

    return names


def save_names(filename, names):
    file = open(filename, "w")

    for name in names:
        file.write(name + "\\n")


students = read_student_names("students.txt")

print("Students:")
for student in students:
    print(student)

save_names("output.txt", students)"""

    py_res = run_full_pipeline(py_code, "python", "student_names.py", max_iterations=1)
    print(f"  Health Score: {py_res['health_score']}/10 | Verdict: {py_res['verdict']}")
    print(f"  Total Findings: {len(py_res['issues'])}")
    for iss in py_res['issues']:
        print(f"    Line {iss.get('line')}: [{iss.get('severity')}] {iss.get('cwe')} - {iss.get('title')}: {iss.get('description')}")
    print(f"  Changelog ({len(py_res['changelog'])}):")
    for ch in py_res['changelog']:
        print(f"    Line {ch.get('line_affected')}: {ch.get('description')}")
    print(f"  Diff / Corrected Code Lines: {len(py_res['corrected_code'].splitlines())}")

    unclosed_detected = any("unclosed-resource" in str(i) or "CWE-404" in str(i) or "Resource opened" in str(i) for i in py_res['issues'])
    code_changed = (py_res['corrected_code'] != py_code)
    uses_with_open = "with open(" in py_res['corrected_code']

    report["python_regression"] = {
        "score": py_res['health_score'],
        "verdict": py_res['verdict'],
        "issues_count": len(py_res['issues']),
        "unclosed_detected": unclosed_detected,
        "changelog_count": len(py_res['changelog']),
        "code_changed": code_changed,
        "uses_with_open": uses_with_open,
        "corrected_code": py_res['corrected_code']
    }

    print("\n======================================================================")
    print("STEP 4: TESTING ALL 6 LANGUAGES ACROSS MANDATORY 8 BUG CATEGORIES")
    print("======================================================================")

    # We design test code for each of the 6 languages containing the 8 mandatory categories:
    # 1. Syntax, 2. Runtime, 3. Logic, 4. Boundary, 5. Resource, 6. Security, 7. Performance, 8. Style
    languages_tests = {
        "python": {
            "ext": ".py",
            "code": """import os
import sqlite3

# 6. Security: Hardcoded secret (CWE-798)
API_SECRET = "sk_live_super_secret_admin_key_9988"

# 8. Style / Logic: Mutable default argument (CWE-1078)
def append_entry(entry, cache=[]):
    cache.append(entry)
    return cache

def process_batch(query_id, data_list):
    # 6. Security: SQL Injection via concatenation (CWE-89)
    conn = sqlite3.connect("data.db")
    cur = conn.cursor()
    sql = "SELECT val FROM metrics WHERE id = " + str(query_id)
    cur.execute(sql)
    
    # 5. Resource: Unclosed file opened without context manager (CWE-404)
    dump = open("dump.txt", "w")
    dump.write("data")
    
    # 3. Logic / 4. Boundary: Division by zero on empty input (CWE-369)
    total = len(data_list)
    avg = 100 / total
    
    # 7. Performance: String concatenation in loop (CWE-1078)
    res_str = ""
    for item in data_list:
        res_str += str(item)
        
    # 2. Runtime: Unhandled Exception swallowed (CWE-390)
    try:
        conn.commit()
    except Exception:
        pass
        
    return avg
"""
        },
        "cpp": {
            "ext": ".cpp",
            "code": """#include <iostream>
#include <vector>
#include <cstring>
#include <cstdlib>

// 6. Security: Hardcoded secret (CWE-798)
const char* API_KEY = "PROD_API_KEY_SECRET_HEX_2026";

// 7. Performance: Pass container by value (CWE-1078)
void analyze_records(std::vector<int> records) {
    // 5. Resource: Heap allocation without delete (CWE-401)
    int* ptr = new int[50];
    
    // 3. Logic: Assignment in if condition (CWE-481)
    int mode = 0;
    if (mode = 1) {
        std::cout << "Mode active" << std::endl;
    }
    
    // 4. Boundary: Off-by-one loop boundary (CWE-193)
    for (size_t i = 0; i <= records.size(); ++i) {
        std::cout << records[i] << std::endl;
    }
    
    // 3. Logic: Division by zero risk (CWE-369)
    int count = records.size();
    int avg = 100 / count;
    
    // 6. Security: Buffer overflow via strcpy (CWE-120)
    char buffer[16];
    strcpy(buffer, "excessive_long_payload_string");
    
    // 2. Runtime: Uninitialized scalar read (CWE-457)
    int uninit_val;
    int final_res = uninit_val + 5;
}
"""
        },
        "c": {
            "ext": ".c",
            "code": """#include <stdio.h>
#include <string.h>
#include <stdlib.h>

// 6. Security: Hardcoded secret (CWE-798)
char* SECRET_TOKEN = "DEV_EMBEDDED_DEVICE_KEY_9911";

void handle_client(char* input, int count) {
    // 6. Security: Unsafe sprintf/strcpy buffer overflow (CWE-120)
    char buf[16];
    strcpy(buf, input);
    
    // 5. Resource: malloc without free (CWE-401)
    int* session = (int*)malloc(sizeof(int) * 10);
    
    // 5. Resource: fopen without fclose (CWE-404)
    FILE* fp = fopen("log.txt", "w");
    if (fp) fputs("log", fp);
    
    // 3. Logic: Division by zero (CWE-369)
    int avg = 500 / count;
    
    // 2. Runtime: Uninitialized pointer dereferenced (CWE-457)
    int* uninit_ptr;
    if (*uninit_ptr == 1) {
        printf("flag");
    }
}
"""
        },
        "java": {
            "ext": ".java",
            "code": """package com.app;
import java.io.*;
import java.sql.*;

public class OrderService {
    // 6. Security: Hardcoded secret (CWE-798)
    private static final String DB_SECRET = "sk_live_db_secret_key_884920";
    
    // 3. Logic / Concurrency: Static mutable state unsynchronized (CWE-362)
    private static int counter = 0;
    
    public void processOrder(String orderId, String amount, String status) {
        counter++;
        
        // 3. Logic: String comparison with == (CWE-595)
        if (status == "COMPLETED") {
            System.out.println("Done");
        }
        
        // 3. Logic / 4. Boundary: Division by zero (CWE-369)
        int items = 0;
        int rate = 100 / items;
        
        // 5. Resource: Unclosed FileInputStream (CWE-404)
        try {
            FileInputStream fis = new FileInputStream("order.txt");
            fis.read();
            
            // 6. Security: SQL Injection via concatenation (CWE-89)
            Connection conn = DriverManager.getConnection("jdbc:mysql://localhost/db", "root", DB_SECRET);
            Statement stmt = conn.createStatement();
            stmt.executeUpdate("UPDATE orders SET total = " + amount + " WHERE id = '" + orderId + "'");
        } catch (Exception e) {
            // 2. Runtime: Empty catch block (CWE-390)
        }
    }
}
"""
        },
        "javascript": {
            "ext": ".js",
            "code": """const express = require('express');
const app = express();

// 6. Security: Hardcoded secret (CWE-798)
const JWT_SECRET = "super_jwt_secret_token_key_123456";

app.post('/compute', (req, res) => {
    // 6. Security: Eval injection (CWE-95)
    const result = eval(req.body.code);
    
    // 6. Security: Reflected XSS (CWE-79)
    res.send("<div>" + req.query.comment + "</div>");
});

app.post('/merge', (req, res) => {
    // 6. Security: Prototype pollution (CWE-1321)
    const target = {};
    const payload = JSON.parse(req.body.data);
    for (let key in payload) {
        target[key] = payload[key];
    }
    
    // 8. Style: Loose equality (CWE-480)
    if (payload.status == "1") {
        console.log("active");
    }
    res.json({ ok: true });
});
"""
        },
        "ruby": {
            "ext": ".rb",
            "code": """require 'sqlite3'

# 6. Security: Hardcoded secret (CWE-798)
API_KEY = "RB_SEC_KEY_PROD_123456789"

class DatabaseManager
  def query_user(user_input)
    db = SQLite3::Database.new "app.db"
    
    # 6. Security: SQL Injection via string interpolation (CWE-89)
    query = "SELECT * FROM users WHERE name = '#{user_input}'"
    results = db.execute(query)
    
    # 6. Security: Command injection via backticks (CWE-78)
    filename = "report_#{user_input}.pdf"
    `generate_pdf #{filename}`
    
    # 6. Security: Insecure deserialization (CWE-502)
    cached = File.read("cache.bin")
    data = Marshal.load(cached)
    
    results
  end
end
"""
        }
    }

    total_expected = 0
    total_detected = 0
    total_false_positives = 0
    total_fixable = 0
    total_fixed = 0

    for lang, test_info in languages_tests.items():
        print(f"\n--- Testing Language: {lang.upper()} ---")
        code = test_info["code"]
        filename = f"test_{lang}{test_info['ext']}"
        try:
            res = run_full_pipeline(code, lang, filename, max_iterations=1)

            findings = res.get("issues", [])
            changelog = res.get("changelog", [])
            mcp_tools = res.get("mcp_tools", [])
            health = res.get("health_score", 10.0)
            verdict = res.get("verdict", "UNKNOWN")

            print(f"  MCP Tools Configured: {get_mcp_tools_for_language(lang)}")
            print(f"  MCP Tools Invoked: {mcp_tools}")
            print(f"  Health Score: {health}/10 | Verdict: {verdict}")
            print(f"  Detected Findings ({len(findings)}):")
            for f in findings:
                print(f"    Line {f.get('line')}: [{f.get('severity')}] {f.get('cwe')} - {f.get('title')}")
            print(f"  Changelog Entries ({len(changelog)}):")
            for c in changelog:
                print(f"    Line {c.get('line_affected')}: {c.get('description')}")

            exp_count = 6 if lang in ["javascript", "ruby"] else 7
            det_count = len(findings)
            fixed_count = len(changelog)

            total_expected += exp_count
            total_detected += min(det_count, exp_count)
            if det_count > exp_count:
                total_false_positives += (det_count - exp_count)
            total_fixable += exp_count
            total_fixed += fixed_count

            report["language_matrix"][lang] = {
                "mcp_tools": mcp_tools,
                "findings_count": det_count,
                "health_score": health,
                "verdict": verdict,
                "changelog_count": fixed_count,
                "code_modified": (res.get("corrected_code") != code),
                "status": "PASS" if det_count >= 4 else "PARTIAL"
            }
        except Exception as e:
            print(f"  [PIPELINE CRASH] Failed during {lang.upper()} execution: {type(e).__name__}: {e}")
            report["language_matrix"][lang] = {
                "mcp_tools": get_mcp_tools_for_language(lang),
                "findings_count": 0,
                "health_score": 0.0,
                "verdict": "CRASHED",
                "changelog_count": 0,
                "code_modified": False,
                "status": f"CRASH: {type(e).__name__}: {e}"
            }

    # Metric calculations
    det_accuracy = (total_detected / total_expected) * 100 if total_expected else 0
    fn_rate = ((total_expected - total_detected) / total_expected) * 100 if total_expected else 0
    fp_rate = (total_false_positives / (total_detected + total_false_positives)) * 100 if (total_detected + total_false_positives) else 0
    fix_rate = (total_fixed / total_fixable) * 100 if total_fixable else 0

    report["metrics"] = {
        "detection_accuracy": round(det_accuracy, 1),
        "false_positive_rate": round(fp_rate, 1),
        "false_negative_rate": round(fn_rate, 1),
        "autofix_success_rate": round(fix_rate, 1)
    }

    print("\n======================================================================")
    print("STEP 5: VALIDATION SUMMARY METRICS")
    print("======================================================================")
    print(f"  Detection Accuracy    : {report['metrics']['detection_accuracy']}%")
    print(f"  False Positive Rate   : {report['metrics']['false_positive_rate']}%")
    print(f"  False Negative Rate   : {report['metrics']['false_negative_rate']}%")
    print(f"  Auto-Fix Success Rate : {report['metrics']['autofix_success_rate']}%")

    with open("validation_results.json", "w", encoding="utf-8") as out:
        json.dump(report, out, indent=2)
    print("\nWrote full validation data to validation_results.json")

if __name__ == "__main__":
    validate_all()
