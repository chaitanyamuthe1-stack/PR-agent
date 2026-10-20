"""
Phase 13 Automated Test Suite: Benchmark Engine and Multi-Language Sample System.
Verifies:
1. Working sample code across all six languages (Python, C, C++, Java, JS, Ruby).
2. Intentional vulnerability labeling, warning banners, and defect category coverage.
3. Documented ground-truth dataset integrity (synthetic fixtures vs real-world benchmarks).
4. Rigorous ground-truth matching algorithm (TP, FP, FN, Precision, Recall, F1).
5. Isolated, bounded benchmark execution and total crash prevention.
6. Truthful reporting of tool availability and provider limitations without fabrication.
7. RAG vector store benchmark execution and Precision@1 retrieval.
8. Benchmark API endpoints in FastAPI server.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.samples import SAMPLES
from backend.benchmark import (
    GROUND_TRUTH_DATASET,
    evaluate_ground_truth_matching,
    run_isolated_benchmark_case,
    run_rag_benchmark
)
from backend.main import app

client = TestClient(app)


def test_1_sample_code_six_languages_complete():
    """Verifies all six languages have working samples with required defect categories and warning banners."""
    expected_langs = ["python", "cpp", "c", "java", "javascript", "ruby"]
    required_defect_classes = {"security", "boundary", "runtime", "resource", "performance"}

    for lang in expected_langs:
        assert lang in SAMPLES, f"Missing sample for language: {lang}"
        sample = SAMPLES[lang]

        # Verify basic structure
        assert sample["language"] == lang
        assert len(sample["code"].strip()) > 50, f"Sample code for {lang} is too short or empty"
        assert sample["filename"], f"Missing filename for {lang}"
        assert len(sample["tools"]) >= 1, f"Missing tool configuration for {lang}"

        # Requirement: Clearly label intentionally vulnerable sample code
        assert sample.get("is_intentionally_vulnerable") is True, f"Sample {lang} must be labeled as intentionally vulnerable"
        assert "WARNING: INTENTIONALLY VULNERABLE" in sample["code"], f"Missing warning banner in code for {lang}"

        # Requirement: Include examples of common syntax, boundary, runtime, resource, performance, and security problems
        categories = set(sample.get("defect_categories", []))
        overlap = categories.intersection(required_defect_classes)
        assert len(overlap) >= 4, f"Language {lang} only covers {categories}; expected coverage of {required_defect_classes}"

        # Documented ground-truth defect list
        expected_defects = sample.get("expected_defects", [])
        assert len(expected_defects) >= 4, f"Language {lang} must document at least 4 ground-truth defects"
        for defect in expected_defects:
            assert "category" in defect
            assert "cwe" in defect or "rule_id" in defect
            assert "line_hint" in defect
            assert "title" in defect


def test_2_ground_truth_dataset_integrity():
    """Verifies documented ground-truth dataset has synthetic fixtures and real-world benchmarks."""
    assert len(GROUND_TRUTH_DATASET) >= 18, f"Expected at least 18 benchmark cases, found {len(GROUND_TRUTH_DATASET)}"

    real_world_cases = [c for c in GROUND_TRUTH_DATASET.values() if c["suite_type"] == "real_world"]
    synthetic_cases = [c for c in GROUND_TRUTH_DATASET.values() if c["suite_type"] == "synthetic"]

    assert len(real_world_cases) == 6, "Expected 6 real-world application benchmark cases"
    assert len(synthetic_cases) >= 12, "Expected at least 12 synthetic fixture cases (6 vuln, 6 clean)"

    langs_covered = {c["language"] for c in real_world_cases}
    assert langs_covered == {"python", "cpp", "c", "java", "javascript", "ruby"}

    clean_controls = [c for c in synthetic_cases if not c["is_intentionally_vulnerable"]]
    assert len(clean_controls) == 6, "Expected 6 clean negative control fixtures across all 6 languages"


def test_3_ground_truth_matching_algorithm():
    """Validates mathematical TP/FP/FN/Precision/Recall/F1 matching algorithm."""
    expected_defects = [
        {"category": "security", "cwe": "CWE-89", "rule_id": "B608", "line_hint": 15, "title": "SQLi"},
        {"category": "security", "cwe": "CWE-78", "rule_id": "B605", "line_hint": 30, "title": "Command Injection"},
        {"category": "runtime", "cwe": "CWE-369", "rule_id": "zerodiv", "line_hint": 22, "title": "Div by zero"},
        {"category": "resource", "cwe": "CWE-404", "rule_id": "unclosed", "line_hint": 26, "title": "Resource leak"}
    ]

    # Scenario A: Perfect detection (4 TP, 0 FP, 0 FN -> Precision=1.0, Recall=1.0)
    actual_perfect = [
        {"id": "1", "category": "security", "cwe": "CWE-89", "rule_id": "B608", "line": 15, "title": "SQL Injection"},
        {"id": "2", "category": "security", "cwe": "CWE-78", "rule_id": "B605", "line": 30, "title": "OS Command"},
        {"id": "3", "category": "runtime", "cwe": "CWE-369", "rule_id": "zerodiv", "line": 22, "title": "Zero div"},
        {"id": "4", "category": "resource", "cwe": "CWE-404", "rule_id": "unclosed", "line": 26, "title": "Unclosed fd"}
    ]
    res_a = evaluate_ground_truth_matching(actual_perfect, expected_defects)
    assert res_a["true_positives"] == 4
    assert res_a["false_positives"] == 0
    assert res_a["false_negatives"] == 0
    assert res_a["precision"] == 1.0
    assert res_a["recall"] == 1.0
    assert res_a["f1_score"] == 1.0

    # Scenario B: Partial detection with 1 FP (2 TP, 1 FP, 2 FN)
    actual_partial = [
        {"id": "1", "category": "security", "cwe": "CWE-89", "rule_id": "B608", "line": 15, "title": "SQLi"},
        {"id": "2", "category": "security", "cwe": "CWE-78", "rule_id": "B605", "line": 31, "title": "Command"},
        {"id": "3", "category": "style", "cwe": "CWE-999", "rule_id": "flake8:E501", "line": 99, "title": "Line too long"}
    ]
    res_b = evaluate_ground_truth_matching(actual_partial, expected_defects)
    assert res_b["true_positives"] == 2
    assert res_b["false_positives"] == 1
    assert res_b["false_negatives"] == 2
    assert res_b["precision"] == round(2 / 3, 3)
    assert res_b["recall"] == round(2 / 4, 3)

    # Scenario C: Clean code negative control (0 actual, 0 expected -> 1.0 precision/recall)
    res_c = evaluate_ground_truth_matching([], [])
    assert res_c["precision"] == 1.0
    assert res_c["recall"] == 1.0
    assert res_c["f1_score"] == 1.0


def test_4_isolated_bounded_execution_and_crash_prevention():
    """Verifies that malformed test cases or exceptions never crash the application."""
    malformed_case = {
        "id": "ERR-TEST-01",
        "name": "Corrupted Test Case",
        "language": "unsupported_lang",
        "code": None,  # Will trigger safe catch
        "filename": "broken.xyz",
        "is_intentionally_vulnerable": True,
        "expected_defects": [{"category": "security", "cwe": "CWE-89", "line_hint": 1}]
    }

    # Should execute without raising uncaught exceptions
    result = run_isolated_benchmark_case(malformed_case)
    assert result["id"] == "ERR-TEST-01"
    assert result["status"] == "error"
    assert "Benchmark case execution failed safely" in result["error_message"]
    assert result["verdict"] == "BENCHMARK_ERROR"
    assert result["precision"] == 0.0


def test_5_tool_availability_and_provider_limitations_reporting():
    """Verifies that tool availability and provider limitations are reported truthfully."""
    test_case = GROUND_TRUTH_DATASET["REAL-PY-01"]
    result = run_isolated_benchmark_case(test_case)

    # Must report native tools for python
    assert "bandit" in result["native_tools"]
    assert isinstance(result["missing_tools"], list)
    assert "provider_notes" in result
    assert isinstance(result["provider_notes"], list)


def test_6_rag_benchmark_execution():
    """Verifies in-memory RAG vector retrieval benchmark executes and produces real metrics."""
    res = run_rag_benchmark()
    assert res["total_queries"] >= 6
    assert "average_latency_ms" in res
    assert res["average_latency_ms"] >= 0.0
    assert "precision_at_1" in res
    assert res["vector_count"] >= 10
    assert res["embedding_dimension"] == 128
    assert len(res["runs"]) == res["total_queries"]

    for run in res["runs"]:
        assert "target" in run
        assert "similarity" in run
        assert "latency_ms" in run


def test_7_remediation_syntax_validation_verification():
    """Verifies that clean controls produce valid syntax, zero false negatives, and completed status."""
    clean_py = GROUND_TRUTH_DATASET["SYNTH-PY-CLEAN"]
    result = run_isolated_benchmark_case(clean_py)

    assert result["is_intentionally_vulnerable"] is False
    assert result["syntax_valid"] is True
    assert result["status"] == "completed"
    assert result["expected_issues_count"] == 0
    assert result["false_negatives"] == 0
    assert result["latency_ms"] > 0.0


def test_8_benchmark_api_endpoints():
    """Verifies FastAPI benchmark endpoints return proper HTTP 200 telemetry."""
    # 1. /api/benchmark/catalog
    resp_cat = client.get("/api/benchmark/catalog")
    assert resp_cat.status_code == 200
    cat_data = resp_cat.json()
    assert "catalog" in cat_data
    assert cat_data["total_test_cases"] >= 18

    # 2. /api/benchmark/status
    resp_stat = client.get("/api/benchmark/status")
    assert resp_stat.status_code == 200
    stat_data = resp_stat.json()
    assert "llm_provider" in stat_data
    assert "all_tools_status" in stat_data
    assert stat_data["total_dataset_cases"] >= 18

    # 3. /api/samples
    resp_samp = client.get("/api/samples")
    assert resp_samp.status_code == 200
    samp_data = resp_samp.json()
    assert "python" in samp_data
    assert "cpp" in samp_data
    assert "c" in samp_data
    assert "java" in samp_data
    assert "javascript" in samp_data
    assert "ruby" in samp_data
    assert samp_data["python"]["is_intentionally_vulnerable"] is True

    # 4. /api/benchmark/rag/run
    resp_rag = client.get("/api/benchmark/rag/run")
    assert resp_rag.status_code == 200
    rag_data = resp_rag.json()
    assert "precision_at_1" in rag_data
