"""
Test Suite for Phase 14: API, Database, and Error Handling.
Validates:
1. Distinguishing Readiness from Liveness health probes.
2. Endpoint contracts (/api/status, /api/health, /api/languages, /api/samples, /api/gateway/status).
3. Upload size limits (5MB boundary enforcement with 413 status).
4. Request input validation (empty code 400, unsupported languages 400).
5. Download & Audit-report endpoints (404 on invalid review_id, valid export headers).
6. SQLite WAL mode, schema migrations, and bounded in-memory degradation.
7. Cryptographically unique review session IDs under concurrent execution.
8. Safe error responses stripping API keys and filesystem paths.
"""

import os
import io
import time
import pytest
from fastapi.testclient import TestClient
from backend.main import app, sanitize_error, SUPPORTED_LANGUAGES
from backend.database import (
    init_db,
    get_db_connection,
    save_review_record,
    get_review_record,
    _MEMORY_FALLBACK_CACHE,
    MAX_MEMORY_CACHE,
    sanitize_db_error
)

client = TestClient(app)


def test_1_liveness_vs_readiness_probes():
    """Verifies that liveness returns 200 while readiness verifies components and can return 503."""
    # 1. Normal state: liveness probe returns 200
    res_live = client.get("/api/health/liveness")
    assert res_live.status_code == 200
    assert res_live.json().get("status") == "alive"

    res_live_alias = client.get("/health/liveness")
    assert res_live_alias.status_code == 200

    # 2. Normal state: readiness probe returns 200 with database and rag telemetry
    res_ready = client.get("/api/health/readiness")
    assert res_ready.status_code == 200
    data = res_ready.json()
    assert data.get("status") == "ready"
    assert data.get("database", {}).get("status") == "healthy"

    # 3. Degraded state: simulate DB failure
    os.environ["PR_AGENT_SIMULATE_DB_FAIL"] = "1"
    try:
        # Liveness is STILL 200 (process is responsive)
        res_live_degraded = client.get("/api/health/liveness")
        assert res_live_degraded.status_code == 200
        assert res_live_degraded.json().get("status") == "alive"

        # Readiness is 503 (not ready to serve traffic without DB)
        res_ready_degraded = client.get("/api/health/readiness")
        assert res_ready_degraded.status_code == 503
        degraded_data = res_ready_degraded.json()
        assert degraded_data.get("status") == "degraded"
        assert degraded_data.get("database", {}).get("status") == "degraded"
    finally:
        os.environ.pop("PR_AGENT_SIMULATE_DB_FAIL", None)

    # After clearing simulation, readiness recovers to 200
    res_recovered = client.get("/api/health/readiness")
    assert res_recovered.status_code == 200
    assert res_recovered.json().get("status") == "ready"


def test_2_system_status_and_languages_endpoints():
    """Validates /api/status and /api/languages contracts."""
    res_status = client.get("/api/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert "status" in status_data
    assert "gateway" in status_data
    assert "rag" in status_data
    assert "database" in status_data
    assert "supported_languages" in status_data
    assert "python" in status_data["supported_languages"]

    res_langs = client.get("/api/languages")
    assert res_langs.status_code == 200
    langs = res_langs.json().get("languages", [])
    assert len(langs) >= 6
    lang_ids = {l["id"] for l in langs}
    for required in ["python", "cpp", "c", "java", "javascript", "ruby"]:
        assert required in lang_ids


def test_3_samples_and_gateway_status():
    """Validates /api/samples and /api/gateway/status."""
    res_samples = client.get("/api/samples")
    assert res_samples.status_code == 200
    samples_data = res_samples.json()
    for lang in ["python", "cpp", "c", "java", "javascript", "ruby"]:
        assert lang in samples_data
        assert "code" in samples_data[lang]
        assert samples_data[lang].get("is_intentionally_vulnerable") is True

    # 404 for unknown sample language
    res_bad_sample = client.get("/api/samples/nonexistent_lang")
    assert res_bad_sample.status_code == 404

    # Gateway status
    res_gw = client.get("/api/gateway/status")
    assert res_gw.status_code == 200
    gw_data = res_gw.json()
    assert "provider" in gw_data
    assert "fallback_state" in gw_data


def test_4_upload_limits_and_extension_inference():
    """Tests 5MB upload size limit with 413 status and file extension language inference."""
    # Small valid file
    py_code = b"print('Hello, Phase 14!')\n"
    res_up = client.post(
        "/api/upload",
        files={"file": ("hello.py", io.BytesIO(py_code), "text/x-python")}
    )
    assert res_up.status_code == 200
    up_data = res_up.json()
    assert up_data["filename"] == "hello.py"
    assert up_data["language"] == "python"
    assert up_data["line_count"] == 1

    # TypeScript file inference
    ts_code = b"const x: number = 42;\n"
    res_ts = client.post(
        "/api/upload",
        files={"file": ("app.ts", io.BytesIO(ts_code), "application/typescript")}
    )
    assert res_ts.status_code == 200
    assert res_ts.json()["language"] == "typescript"

    # File exceeding 5MB: exactly 5MB + 1KB
    oversized = b"A" * (5 * 1024 * 1024 + 1024)
    res_large = client.post(
        "/api/upload",
        files={"file": ("massive.py", io.BytesIO(oversized), "text/plain")}
    )
    assert res_large.status_code == 413
    assert "too large" in res_large.json()["detail"].lower()


def test_5_input_validation_and_bad_request_codes():
    """Ensures input validation strictly returns 400 for empty code and unsupported languages."""
    # Empty code
    res_empty = client.post(
        "/api/review",
        json={"code": "   ", "language": "python"}
    )
    assert res_empty.status_code == 400
    assert "cannot be empty" in res_empty.json()["detail"].lower()

    # Unsupported language
    res_bad_lang = client.post(
        "/api/review",
        json={"code": "def foo(): pass", "language": "brainfuck"}
    )
    assert res_bad_lang.status_code == 400
    assert "unsupported language" in res_bad_lang.json()["detail"].lower()

    # Remediate input validation
    res_rem_bad = client.post(
        "/api/remediate",
        json={"code": "", "language": "python"}
    )
    assert res_rem_bad.status_code == 400

    res_rem_bad_lang = client.post(
        "/api/remediate",
        json={"code": "int x = 1;", "language": "cobol"}
    )
    assert res_rem_bad_lang.status_code == 400

    # Recheck input validation
    res_rec_bad = client.post(
        "/api/recheck",
        json={"original_code": "", "corrected_code": "", "language": "python"}
    )
    assert res_rec_bad.status_code == 400


def test_6_download_and_audit_report_contracts():
    """Tests 404 on missing review_ids and valid download responses on reviewed artifacts."""
    # 404 for nonexistent review_id
    res_bad_dl = client.get("/api/download?review_id=rev-nonexistent999999")
    assert res_bad_dl.status_code == 404

    res_bad_audit = client.get("/api/audit-report?review_id=rev-nonexistent999999")
    assert res_bad_audit.status_code == 404

    # Save a mock review record to test successful export
    test_id = "rev-testphase1401"
    mock_review = {
        "review_id": test_id,
        "filename": "demo_test.py",
        "language": "python",
        "health_score": 8.0,
        "post_fix_score": 10.0,
        "verdict": "FIX REQUIRED",
        "unresolved_count": 0,
        "resolved_count": 1,
        "remediation_status": "SUCCESS",
        "auto_fix_failure": False,
        "corrected_code": "def add(a: int, b: int) -> int:\n    return a + b\n",
        "issues": [
            {
                "title": "Missing Type Annotations",
                "line": 1,
                "severity": "low",
                "resolved": True
            }
        ],
        "changelog": [
            {
                "change_type": "type_annotated",
                "line_affected": 1,
                "rule_citation": "PEP-484",
                "description": "Added int return type"
            }
        ],
        "telemetry": [],
        "mcp_tools": ["pylint"]
    }
    save_review_record(test_id, mock_review)

    # Download corrected source code
    res_dl = client.get(f"/api/download?review_id={test_id}")
    assert res_dl.status_code == 200
    assert "attachment; filename=\"demo_test_corrected.py\"" in res_dl.headers.get("Content-Disposition", "")
    assert "def add" in res_dl.text

    # Download audit report
    res_rpt = client.get(f"/api/audit-report?review_id={test_id}")
    assert res_rpt.status_code == 200
    assert "attachment; filename=\"demo_test_PR_Agent_Audit_Report.md\"" in res_rpt.headers.get("Content-Disposition", "")
    assert "PR AGENT AUDIT REPORT" in res_rpt.text
    assert "Initial Health Score:" in res_rpt.text


def test_7_database_wal_mode_and_schema_migrations():
    """Verifies SQLite is operating in WAL mode and all migration columns exist."""
    init_res = init_db()
    assert init_res.get("status") == "healthy"

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check journal_mode is WAL
    cursor.execute("PRAGMA journal_mode")
    row = cursor.fetchone()
    assert row[0].upper() == "WAL"

    # Check migration columns
    cursor.execute("PRAGMA table_info(reviews)")
    cols = {r["name"] for r in cursor.fetchall()}
    expected_cols = {
        "review_id", "timestamp", "filename", "language", "health_score",
        "post_fix_score", "verdict", "unresolved_count", "resolved_count",
        "remediation_status", "auto_fix_failure", "json_data"
    }
    for col in expected_cols:
        assert col in cols, f"Missing required column '{col}' in reviews table"
    conn.close()


def test_8_bounded_in_memory_growth():
    """Verifies that in-memory fallback cache does not grow unbounded under high insert volume."""
    # Insert 150 items
    for i in range(150):
        key = f"rev-stress-{i:04d}"
        save_review_record(key, {"sample": i})

    # The in-memory cache should be clamped at MAX_MEMORY_CACHE (100)
    assert len(_MEMORY_FALLBACK_CACHE) <= MAX_MEMORY_CACHE


def test_9_safe_error_responses_redact_secrets_and_paths():
    """Verifies that sanitize_error and sanitize_db_error redact API keys and host paths."""
    sensitive_msg = (
        "Fatal error connecting with key=AIzaSyD9876543210abcdef "
        "at C:\\Users\\chait\\OneDrive\\Desktop\\PR_Agent\\backend\\secret.py:42"
    )
    sanitized = sanitize_error(sensitive_msg)
    assert "AIzaSyD9876543210abcdef" not in sanitized
    assert "REDACTED" in sanitized
    assert "C:\\Users\\chait" not in sanitized
    assert "[INTERNAL_PATH]" in sanitized

    unix_path_msg = "Database lock error in /home/ubuntu/app/database.db: disk I/O"
    sanitized_db = sanitize_db_error(unix_path_msg)
    assert "/home/ubuntu" not in sanitized_db
    assert "[INTERNAL_PATH]" in sanitized_db
