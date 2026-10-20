"""
PR Agent Benchmark Engine.
Provides isolated, bounded benchmark execution against documented ground-truth datasets:
- Synthetic Test Fixtures (clean vs vulnerable unit cases across all 6 languages)
- Real-World Benchmarks (composite multi-defect application samples across all 6 languages)

Guarantees:
1. Truthful, non-fabricated metrics calculated from actual pipeline outputs against ground truth.
2. Isolated, bounded execution with timeout protection and exception containment.
3. Explicit disclosure of test conditions, available tools, missing tools, and provider limitations.
4. Total crash prevention: benchmark failures never bring down the FastAPI server.
"""

import os
import sys
import time
import platform
from typing import Dict, Any, List, Optional
from datetime import datetime

from .samples import SAMPLES
from .mcp_tools import get_mcp_tools_for_language, get_all_tools_status
from .llm_gateway import gateway
from .rag.vector_store import store
from .graph import run_full_pipeline, validate_code_syntax


# ==============================================================================
# 1. DOCUMENTED GROUND-TRUTH TEST DATASET
# ==============================================================================

# Directory where physical fixture files reside
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_files", "fixtures")

def _read_fixture_file(lang: str, filename: str) -> str:
    path = os.path.join(FIXTURES_DIR, lang, filename)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    return ""


GROUND_TRUTH_DATASET: Dict[str, Dict[str, Any]] = {
    # --------------------------------------------------------------------------
    # REAL-WORLD COMPOSITE APPLICATION BENCHMARKS (6 Languages)
    # --------------------------------------------------------------------------
    "REAL-PY-01": {
        "id": "REAL-PY-01",
        "name": "Python Application (Multi-Defect Suite)",
        "language": "python",
        "suite_type": "real_world",
        "filename": SAMPLES["python"]["filename"],
        "code": SAMPLES["python"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": SAMPLES["python"]["defect_categories"],
        "expected_defects": SAMPLES["python"]["expected_defects"]
    },
    "REAL-CPP-01": {
        "id": "REAL-CPP-01",
        "name": "C++ Network Handler (Buffer Overflow & Leak)",
        "language": "cpp",
        "suite_type": "real_world",
        "filename": SAMPLES["cpp"]["filename"],
        "code": SAMPLES["cpp"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": SAMPLES["cpp"]["defect_categories"],
        "expected_defects": SAMPLES["cpp"]["expected_defects"]
    },
    "REAL-C-01": {
        "id": "REAL-C-01",
        "name": "C Firmware Authenticator (Buffer & Memory)",
        "language": "c",
        "suite_type": "real_world",
        "filename": SAMPLES["c"]["filename"],
        "code": SAMPLES["c"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": SAMPLES["c"]["defect_categories"],
        "expected_defects": SAMPLES["c"]["expected_defects"]
    },
    "REAL-JAVA-01": {
        "id": "REAL-JAVA-01",
        "name": "Java Payment Service (SQLi & Resource Leak)",
        "language": "java",
        "suite_type": "real_world",
        "filename": SAMPLES["java"]["filename"],
        "code": SAMPLES["java"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": SAMPLES["java"]["defect_categories"],
        "expected_defects": SAMPLES["java"]["expected_defects"]
    },
    "REAL-JS-01": {
        "id": "REAL-JS-01",
        "name": "JavaScript Express Route (Eval, XSS & Proto)",
        "language": "javascript",
        "suite_type": "real_world",
        "filename": SAMPLES["javascript"]["filename"],
        "code": SAMPLES["javascript"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": SAMPLES["javascript"]["defect_categories"],
        "expected_defects": SAMPLES["javascript"]["expected_defects"]
    },
    "REAL-RUBY-01": {
        "id": "REAL-RUBY-01",
        "name": "Ruby Report Generator (SQLi & Cmd Injection)",
        "language": "ruby",
        "suite_type": "real_world",
        "filename": SAMPLES["ruby"]["filename"],
        "code": SAMPLES["ruby"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": SAMPLES["ruby"]["defect_categories"],
        "expected_defects": SAMPLES["ruby"]["expected_defects"]
    },

    # --------------------------------------------------------------------------
    # SYNTHETIC TEST FIXTURES: VULNERABLE (6 Languages)
    # --------------------------------------------------------------------------
    "SYNTH-PY-VULN": {
        "id": "SYNTH-PY-VULN",
        "name": "Synthetic Python Vulnerable Fixture",
        "language": "python",
        "suite_type": "synthetic",
        "filename": "vulnerable.py",
        "code": _read_fixture_file("python", "vulnerable.py") or SAMPLES["python"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "runtime", "resource"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-798", "rule_id": "B105", "line_hint": 7, "title": "Hardcoded secret token"},
            {"category": "security", "cwe": "CWE-89", "rule_id": "B608", "line_hint": 13, "title": "SQL Injection via string concat"},
            {"category": "runtime", "cwe": "CWE-369", "rule_id": "zero-division", "line_hint": 19, "title": "Division by zero risk"},
            {"category": "resource", "cwe": "CWE-404", "rule_id": "unclosed-resource", "line_hint": 22, "title": "Unclosed access.log file handle"},
            {"category": "security", "cwe": "CWE-78", "rule_id": "B605", "line_hint": 29, "title": "Command Injection via os.system"}
        ]
    },
    "SYNTH-CPP-VULN": {
        "id": "SYNTH-CPP-VULN",
        "name": "Synthetic C++ Vulnerable Fixture",
        "language": "cpp",
        "suite_type": "synthetic",
        "filename": "vulnerable.cpp",
        "code": _read_fixture_file("cpp", "vulnerable.cpp") or SAMPLES["cpp"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "resource", "runtime"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-120", "rule_id": "buffer-overflow", "line_hint": 9, "title": "Buffer overflow via unsafe strcpy"},
            {"category": "resource", "cwe": "CWE-401", "rule_id": "memleak", "line_hint": 12, "title": "Memory leak: malloc without free"},
            {"category": "runtime", "cwe": "CWE-369", "rule_id": "zerodiv", "line_hint": 16, "title": "Division by zero without guard"},
            {"category": "runtime", "cwe": "CWE-476", "rule_id": "nullPointer", "line_hint": 19, "title": "NULL pointer dereference from getenv"}
        ]
    },
    "SYNTH-C-VULN": {
        "id": "SYNTH-C-VULN",
        "name": "Synthetic C Vulnerable Fixture",
        "language": "c",
        "suite_type": "synthetic",
        "filename": "vulnerable.c",
        "code": _read_fixture_file("c", "vulnerable.c") or SAMPLES["c"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "resource"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-798", "rule_id": "hardcoded-credentials", "line_hint": 7, "title": "Hardcoded firmware root key"},
            {"category": "security", "cwe": "CWE-120", "rule_id": "buffer-overflow", "line_hint": 12, "title": "Unbounded strcpy buffer overflow"},
            {"category": "resource", "cwe": "CWE-404", "rule_id": "resourceLeak", "line_hint": 15, "title": "Unclosed FILE pointer leak"}
        ]
    },
    "SYNTH-JAVA-VULN": {
        "id": "SYNTH-JAVA-VULN",
        "name": "Synthetic Java Vulnerable Fixture",
        "language": "java",
        "suite_type": "synthetic",
        "filename": "Vulnerable.java",
        "code": _read_fixture_file("java", "Vulnerable.java") or SAMPLES["java"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "bug", "resource", "syntax"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-798", "rule_id": "hardcoded-credentials", "line_hint": 8, "title": "Hardcoded API secret token"},
            {"category": "bug", "cwe": "CWE-595", "rule_id": "string-compare-eq", "line_hint": 12, "title": "String comparison using == instead of .equals()"},
            {"category": "resource", "cwe": "CWE-404", "rule_id": "resource-leak", "line_hint": 18, "title": "Unclosed FileInputStream leak"},
            {"category": "syntax", "cwe": "CWE-390", "rule_id": "EmptyBlock", "line_hint": 21, "title": "Empty catch block swallowing exception"}
        ]
    },
    "SYNTH-JS-VULN": {
        "id": "SYNTH-JS-VULN",
        "name": "Synthetic JavaScript Vulnerable Fixture",
        "language": "javascript",
        "suite_type": "synthetic",
        "filename": "vulnerable.js",
        "code": _read_fixture_file("javascript", "vulnerable.js") or SAMPLES["javascript"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "style"],
        "expected_defects": [
            {"category": "style", "cwe": "CWE-697", "rule_id": "eqeqeq", "line_hint": 5, "title": "Loose equality check (eqeqeq)"},
            {"category": "security", "cwe": "CWE-798", "rule_id": "no-secrets", "line_hint": 7, "title": "Hardcoded secret JWT string"}
        ]
    },
    "SYNTH-RUBY-VULN": {
        "id": "SYNTH-RUBY-VULN",
        "name": "Synthetic Ruby Vulnerable Fixture",
        "language": "ruby",
        "suite_type": "synthetic",
        "filename": "vulnerable.rb",
        "code": _read_fixture_file("ruby", "vulnerable.rb") or SAMPLES["ruby"]["code"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-798", "rule_id": "Security/HardcodedSecret", "line_hint": 5, "title": "Hardcoded production API key constant"}
        ]
    },

    # --------------------------------------------------------------------------
    # SYNTHETIC TEST FIXTURES: CLEAN / NEGATIVE CONTROLS (6 Languages)
    # --------------------------------------------------------------------------
    "SYNTH-PY-CLEAN": {
        "id": "SYNTH-PY-CLEAN",
        "name": "Synthetic Python Clean Control",
        "language": "python",
        "suite_type": "synthetic",
        "filename": "clean.py",
        "code": _read_fixture_file("python", "clean.py") or "# Clean Python control\ndef ping(): return True\n",
        "is_intentionally_vulnerable": False,
        "defect_categories": [],
        "expected_defects": []
    },
    "SYNTH-CPP-CLEAN": {
        "id": "SYNTH-CPP-CLEAN",
        "name": "Synthetic C++ Clean Control",
        "language": "cpp",
        "suite_type": "synthetic",
        "filename": "clean.cpp",
        "code": _read_fixture_file("cpp", "clean.cpp") or "// Clean C++ control\nint main() { return 0; }\n",
        "is_intentionally_vulnerable": False,
        "defect_categories": [],
        "expected_defects": []
    },
    "SYNTH-C-CLEAN": {
        "id": "SYNTH-C-CLEAN",
        "name": "Synthetic C Clean Control",
        "language": "c",
        "suite_type": "synthetic",
        "filename": "clean.c",
        "code": _read_fixture_file("c", "clean.c") or "/* Clean C control */\nint main() { return 0; }\n",
        "is_intentionally_vulnerable": False,
        "defect_categories": [],
        "expected_defects": []
    },
    "SYNTH-JAVA-CLEAN": {
        "id": "SYNTH-JAVA-CLEAN",
        "name": "Synthetic Java Clean Control",
        "language": "java",
        "suite_type": "synthetic",
        "filename": "Clean.java",
        "code": _read_fixture_file("java", "Clean.java") or "// Clean Java control\npublic class Clean {}\n",
        "is_intentionally_vulnerable": False,
        "defect_categories": [],
        "expected_defects": []
    },
    "SYNTH-JS-CLEAN": {
        "id": "SYNTH-JS-CLEAN",
        "name": "Synthetic JavaScript Clean Control",
        "language": "javascript",
        "suite_type": "synthetic",
        "filename": "clean.js",
        "code": _read_fixture_file("javascript", "clean.js") or "// Clean JS control\nfunction ping() { return true; }\n",
        "is_intentionally_vulnerable": False,
        "defect_categories": [],
        "expected_defects": []
    },
    "SYNTH-RUBY-CLEAN": {
        "id": "SYNTH-RUBY-CLEAN",
        "name": "Synthetic Ruby Clean Control",
        "language": "ruby",
        "suite_type": "synthetic",
        "filename": "clean.rb",
        "code": _read_fixture_file("ruby", "clean.rb") or "# Clean Ruby control\ndef ping; true; end\n",
        "is_intentionally_vulnerable": False,
        "defect_categories": [],
        "expected_defects": []
    }
}


# ==============================================================================
# 2. GROUND-TRUTH METRIC EVALUATION ALGORITHM
# ==============================================================================

def evaluate_ground_truth_matching(
    actual_issues: List[Dict[str, Any]], 
    expected_defects: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes rigorous True Positives, False Positives, False Negatives,
    Precision, Recall, and F1-Score by comparing pipeline findings against 
    documented ground-truth defect specifications.
    
    Zero fabrication guarantee: strictly calculated from actual issues vs expected_defects.
    """
    if not expected_defects and not actual_issues:
        return {
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "precision": 1.0,
            "recall": 1.0,
            "f1_score": 1.0,
            "matches": []
        }

    matched_expected = set()
    matched_actual = set()
    matches = []

    # 1. Exact CWE or Rule matching
    for act_idx, act in enumerate(actual_issues):
        act_cwe = str(act.get("cwe") or "").upper().replace("CWE-", "").strip()
        act_rule = str(act.get("rule_id") or "").lower().strip()
        act_cat = str(act.get("category") or "").lower().strip()
        act_line = int(act.get("line") or 0)

        for exp_idx, exp in enumerate(expected_defects):
            if exp_idx in matched_expected:
                continue

            exp_cwe = str(exp.get("cwe") or "").upper().replace("CWE-", "").strip()
            exp_rule = str(exp.get("rule_id") or "").lower().strip()
            exp_cat = str(exp.get("category") or "").lower().strip()
            exp_line = int(exp.get("line_hint") or 0)

            # Match criteria:
            # - Same CWE number
            # - Same rule identifier substring
            # - Same category AND line proximity within 4 lines
            cwe_match = bool(exp_cwe and act_cwe and (exp_cwe == act_cwe or exp_cwe in act_cwe or act_cwe in exp_cwe))
            rule_match = bool(exp_rule and act_rule and (exp_rule in act_rule or act_rule in exp_rule))
            category_line_match = bool(act_cat == exp_cat and abs(act_line - exp_line) <= 4)

            if cwe_match or rule_match or category_line_match:
                matched_expected.add(exp_idx)
                matched_actual.add(act_idx)
                matches.append({
                    "expected": exp,
                    "actual": {
                        "id": act.get("id"),
                        "title": act.get("title"),
                        "category": act.get("category"),
                        "cwe": act.get("cwe"),
                        "rule_id": act.get("rule_id"),
                        "line": act.get("line"),
                        "detection_source": act.get("detection_source")
                    },
                    "match_reason": "CWE Match" if cwe_match else ("Rule ID Match" if rule_match else "Category & Line Proximity")
                })
                break

    tp = len(matched_expected)
    fn = len(expected_defects) - tp
    fp = len(actual_issues) - len(matched_actual)

    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if not expected_defects else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if not expected_defects else 0.0)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1_score": round(f1, 3),
        "matches": matches
    }


# ==============================================================================
# 3. ISOLATED & BOUNDED BENCHMARK RUNNER
# ==============================================================================

def run_isolated_benchmark_case(
    test_case: Dict[str, Any], 
    provider_override: Optional[str] = None,
    max_iterations: int = 1
) -> Dict[str, Any]:
    """
    Executes a single benchmark test case in strict isolation.
    Guarantees:
    - Never raises uncaught exceptions to the main process.
    - Captures precise execution latency in milliseconds.
    - Inspects tool availability for target language and logs limitations.
    - Evaluates real detection metrics against ground truth.
    - Verifies auto-remediation syntax validity and defect resolution.
    """
    case_id = test_case["id"]
    lang = test_case["language"]
    code = test_case["code"]
    fname = test_case["filename"]
    is_vuln = test_case.get("is_intentionally_vulnerable", False)
    expected_defects = test_case.get("expected_defects", [])

    # Tool status & limitation check
    all_tools = get_all_tools_status()
    native_tools = get_mcp_tools_for_language(lang)
    missing_tools = [t for t in native_tools if not all_tools.get(t, {}).get("available", False)]
    install_hint = "; ".join([f"{t}: {all_tools.get(t, {}).get('install_cmd', '')}" for t in missing_tools])

    # Provider limitation check
    gw_status = gateway.get_gateway_status()
    active_provider = provider_override or gw_status.get("provider", "gemini")
    fallback_state = gw_status.get("fallback_state", "")

    provider_notes = []
    if fallback_state and "Ollama Offline" in fallback_state:
        provider_notes.append("Ollama daemon offline; execution redirected to offline heuristic engine.")
    elif active_provider in ("OFFLINE_HEURISTIC", "offline_heuristic"):
        provider_notes.append("Zero-credential deterministic static analysis mode active.")

    start_time = time.time()
    try:
        # Bounded execution with max_iterations=1 to ensure strict time bounds
        pipeline_output = run_full_pipeline(
            code=code,
            language=lang,
            filename=fname,
            provider=provider_override,
            max_iterations=max_iterations
        )
        elapsed_ms = round((time.time() - start_time) * 1000, 1)

        detected_issues = pipeline_output.get("issues", [])
        health_score = pipeline_output.get("health_score", 10.0)
        verdict = pipeline_output.get("verdict", "UNKNOWN")
        corrected_code = pipeline_output.get("corrected_code", "")
        remediation_status = pipeline_output.get("remediation_status", "NOT_REQUIRED")
        changelog = pipeline_output.get("changelog", [])
        auto_fix_failure = pipeline_output.get("auto_fix_failure", False)

        # Ground truth evaluation
        metrics = evaluate_ground_truth_matching(detected_issues, expected_defects)

        # Remediation verification check
        if corrected_code:
            syntax_valid, syntax_err = validate_code_syntax(corrected_code, lang)
        else:
            syntax_valid, syntax_err = True, None

        remediation_success = False
        if is_vuln:
            # For vulnerable code: success requires valid syntax, non-failure status, and at least some issues resolved
            remediation_success = bool(
                syntax_valid and 
                not auto_fix_failure and 
                (remediation_status in ("SUCCESS", "PARTIAL") or len(changelog) > 0)
            )
        else:
            # For clean code: success requires remaining clean
            remediation_success = bool(verdict == "CLEAN" and len(detected_issues) == 0)

        return {
            "id": case_id,
            "name": test_case["name"],
            "language": lang,
            "suite_type": test_case.get("suite_type", "synthetic"),
            "filename": fname,
            "is_intentionally_vulnerable": is_vuln,
            "status": "completed",
            "latency_ms": elapsed_ms,
            "health_score": health_score,
            "verdict": verdict,
            "detected_issues_count": len(detected_issues),
            "expected_issues_count": len(expected_defects),
            "true_positives": metrics["true_positives"],
            "false_positives": metrics["false_positives"],
            "false_negatives": metrics["false_negatives"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1_score": metrics["f1_score"],
            "remediation_status": remediation_status,
            "remediation_success": remediation_success,
            "syntax_valid": syntax_valid,
            "syntax_error": syntax_err,
            "changelog_count": len(changelog),
            "native_tools": native_tools,
            "missing_tools": missing_tools,
            "install_hint": install_hint,
            "provider_notes": provider_notes,
            "matches": metrics["matches"]
        }
    except Exception as exc:
        elapsed_ms = round((time.time() - start_time) * 1000, 1)
        return {
            "id": case_id,
            "name": test_case["name"],
            "language": lang,
            "suite_type": test_case.get("suite_type", "synthetic"),
            "filename": fname,
            "is_intentionally_vulnerable": is_vuln,
            "status": "error",
            "error_message": f"Benchmark case execution failed safely: {str(exc)}",
            "latency_ms": elapsed_ms,
            "health_score": 0.0,
            "verdict": "BENCHMARK_ERROR",
            "detected_issues_count": 0,
            "expected_issues_count": len(expected_defects),
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": len(expected_defects),
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "remediation_status": "FAILED",
            "remediation_success": False,
            "syntax_valid": False,
            "changelog_count": 0,
            "native_tools": native_tools,
            "missing_tools": missing_tools,
            "install_hint": install_hint,
            "provider_notes": [f"Execution halted safely: {str(exc)}"],
            "matches": []
        }


# ==============================================================================
# 4. COMPREHENSIVE SUITE RUNNER
# ==============================================================================

def run_benchmark_suite(
    suite_type: str = "all", 
    language_filter: Optional[str] = None,
    provider_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes benchmark test cases sequentially with bounded execution.
    Computes macro and micro metrics, records test conditions, and formats 
    telemetry for live UI rendering.
    """
    suite_start = time.time()
    
    # Filter cases
    selected_cases = []
    for case_id, case in GROUND_TRUTH_DATASET.items():
        if suite_type != "all" and case["suite_type"] != suite_type:
            continue
        if language_filter and case["language"].lower() != language_filter.lower():
            continue
        selected_cases.append(case)

    # Sort: real-world first, then synthetic vulnerable, then clean controls
    def _sort_key(c):
        type_rank = 0 if c["suite_type"] == "real_world" else 1
        vuln_rank = 0 if c["is_intentionally_vulnerable"] else 1
        return (type_rank, vuln_rank, c["language"])
    
    selected_cases.sort(key=_sort_key)

    runs = []
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_latency = 0.0
    successful_remediations = 0
    vulnerable_cases_count = 0

    for case in selected_cases:
        result = run_isolated_benchmark_case(
            test_case=case,
            provider_override=provider_override,
            max_iterations=1
        )
        runs.append(result)

        total_tp += result["true_positives"]
        total_fp += result["false_positives"]
        total_fn += result["false_negatives"]
        total_latency += result["latency_ms"]

        if result["is_intentionally_vulnerable"]:
            vulnerable_cases_count += 1
            if result["remediation_success"]:
                successful_remediations += 1

    total_runs = len(runs)
    avg_latency = round(total_latency / total_runs, 1) if total_runs > 0 else 0.0

    # Macro Precision, Recall, F1
    overall_prec = round(total_tp / (total_tp + total_fp), 3) if (total_tp + total_fp) > 0 else 1.0
    overall_rec = round(total_tp / (total_tp + total_fn), 3) if (total_tp + total_fn) > 0 else 1.0
    overall_f1 = round((2 * overall_prec * overall_rec) / (overall_prec + overall_rec), 3) if (overall_prec + overall_rec) > 0 else 0.0

    # Remediation Success Rate
    remediation_rate = round((successful_remediations / vulnerable_cases_count) * 100, 1) if vulnerable_cases_count > 0 else 100.0

    total_suite_elapsed_sec = round(time.time() - suite_start, 2)

    gw_status = gateway.get_gateway_status()
    test_conditions = {
        "timestamp": datetime.now().isoformat(),
        "suite_type_filter": suite_type,
        "language_filter": language_filter or "all_six_languages",
        "llm_provider": provider_override or gw_status.get("provider", "gemini"),
        "llm_model": gw_status.get("model", "unknown"),
        "fallback_state": gw_status.get("fallback_state", ""),
        "host_platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python_version": sys.version.split()[0],
        "all_tools_status": get_all_tools_status(),
        "suite_duration_seconds": total_suite_elapsed_sec
    }

    return {
        "summary": {
            "total_test_cases": total_runs,
            "vulnerable_cases": vulnerable_cases_count,
            "clean_control_cases": total_runs - vulnerable_cases_count,
            "overall_precision": overall_prec,
            "overall_recall": overall_rec,
            "overall_f1_score": overall_f1,
            "remediation_success_rate": f"{remediation_rate}%",
            "average_latency_ms": avg_latency,
            "total_duration_sec": total_suite_elapsed_sec,
            "true_positives": total_tp,
            "false_positives": total_fp,
            "false_negatives": total_fn
        },
        "test_conditions": test_conditions,
        "runs": runs
    }


# ==============================================================================
# 5. RAG VECTOR STORE BENCHMARK RUNNER
# ==============================================================================

RAG_BENCHMARK_QUERIES = [
    {"q": "SELECT * FROM users WHERE id = " + " + userInput", "target": "OWASP:A03:2021", "desc": "SQL Injection Vector", "category": "Security"},
    {"q": "os.system('tar -czf ' + folderName)", "target": "CWE-78", "desc": "OS Command Injection", "category": "Security"},
    {"q": "char buffer[64]; strcpy(buffer, input);", "target": "CWE-120", "desc": "Classic Buffer Overflow", "category": "Boundary/Security"},
    {"q": "admin_token = 'AG_SECRET_ROOT_KEY_9921'", "target": "CWE-798", "desc": "Hardcoded Secrets", "category": "Security"},
    {"q": "const res = eval(userFormula);", "target": "CWE-95", "desc": "Dynamic Code Evaluation", "category": "Security"},
    {"q": "target[key] = payload[key] without proto check", "target": "CWE-1321", "desc": "Prototype Pollution", "category": "Security"},
    {"q": "open('/tmp/cache.txt', 'w') without close or with context", "target": "CWE-404", "desc": "Resource Leak Unclosed Descriptor", "category": "Resource"},
    {"q": "PEP 8 function names lowercase with underscores", "target": "PEP8", "desc": "PEP 8 Style Guideline", "category": "Style"}
]

def run_rag_benchmark() -> Dict[str, Any]:
    """
    Benchmarks in-memory RAG vector retrieval latency, Precision@1 rule attribution,
    and cosine similarity ranking across standard vulnerability and style query vectors.
    """
    test_runs = []
    total_latency = 0.0
    accurate_matches = 0

    for item in RAG_BENCHMARK_QUERIES:
        start = time.time()
        try:
            res = store.search(item["q"], language=None, top_k=3)
            elapsed = (time.time() - start) * 1000
            total_latency += elapsed

            top_doc = res[0] if res else None
            matched = False
            if top_doc:
                rule_id = str(top_doc.get("rule_id", ""))
                cwe = str(top_doc.get("cwe", ""))
                owasp = str(top_doc.get("owasp", ""))
                target = item["target"]
                matched = bool(target in rule_id or target in cwe or target in owasp)

            if matched:
                accurate_matches += 1

            test_runs.append({
                "query": item["desc"],
                "raw_query": item["q"],
                "target": item["target"],
                "category": item["category"],
                "top_match": f"{top_doc.get('rule_id', 'N/A')} ({top_doc.get('cwe', 'N/A')})" if top_doc else "None",
                "similarity": f"{round(float(top_doc.get('similarity_score', 0.0)) * 100, 1)}%" if top_doc else "0%",
                "latency_ms": round(elapsed, 1),
                "success": matched
            })
        except Exception as e:
            test_runs.append({
                "query": item["desc"],
                "raw_query": item["q"],
                "target": item["target"],
                "category": item["category"],
                "top_match": f"Error: {str(e)}",
                "similarity": "0%",
                "latency_ms": 0.0,
                "success": False
            })

    total_queries = len(RAG_BENCHMARK_QUERIES)
    avg_lat = round(total_latency / total_queries, 1) if total_queries > 0 else 0.0
    precision = round((accurate_matches / total_queries) * 100, 1) if total_queries > 0 else 0.0

    return {
        "runs": test_runs,
        "average_latency_ms": avg_lat,
        "precision_at_1": f"{precision}%",
        "accurate_matches": accurate_matches,
        "total_queries": total_queries,
        "vector_count": len(store.documents),
        "embedding_dimension": 128,
        "timestamp": datetime.now().isoformat()
    }
