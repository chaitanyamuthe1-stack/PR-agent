"""
Complete End-to-End Button & Pipeline Verification Script.
Tests all endpoints corresponding to each frontend button action.
"""

import sys
import os
import json
import httpx

BASE_URL = "http://127.0.0.1:8000"

def run_e2e_test():
    print("=================================================================")
    print("   PR AGENT — COMPLETE BUTTON & PIPELINE END-TO-END TEST")
    print("=================================================================")

    # 1. Test Gateway Status (/api/status)
    print("\n[1] Checking System & Gateway Status (/api/status)...")
    res = httpx.get(f"{BASE_URL}/api/status", timeout=10.0)
    assert res.status_code == 200, f"Failed: {res.text}"
    status_data = res.json()
    print(f"  --> System Status: {status_data.get('status')}")
    print(f"  --> Gateway Badge: {status_data.get('gateway', {}).get('badge')}")
    print(f"  --> Fallback State: {status_data.get('gateway', {}).get('fallback_state')}")
    print(f"  --> Model: {status_data.get('gateway', {}).get('model')}")

    # 2. Test Supported Languages (/api/languages)
    print("\n[2] Checking Supported Languages & Linters (/api/languages)...")
    res = httpx.get(f"{BASE_URL}/api/languages", timeout=10.0)
    assert res.status_code == 200
    langs = res.json().get("languages", [])
    print(f"  --> Supported languages count: {len(langs)}")
    for l in langs:
        print(f"      - {l['name']} ({l['ext']}): {l['mcp_tools']}")

    # 3. Test UPLOAD SOURCE BUTTON (/api/upload with pr_agent_test.py)
    print("\n[3] Testing UPLOAD SOURCE Button with pr_agent_test.py (/api/upload)...")
    with open("pr_agent_test.py", "rb") as f:
        file_bytes = f.read()
    files = {"file": ("pr_agent_test.py", file_bytes, "text/x-python")}
    res = httpx.post(f"{BASE_URL}/api/upload", files=files, timeout=10.0)
    assert res.status_code == 200, f"Upload failed: {res.text}"
    upload_data = res.json()
    print(f"  --> Filename: {upload_data['filename']}")
    print(f"  --> Detected Language: {upload_data['language']}")
    print(f"  --> Line Count: {upload_data['line_count']}")
    print(f"  --> MCP Linters: {upload_data['mcp_tools']}")
    uploaded_code = upload_data["code"]

    # 4. Test RUN REVIEW BUTTON (/api/review with pr_agent_test.py)
    print("\n[4] Testing RUN REVIEW Button (/api/review)...")
    review_payload = {
        "code": uploaded_code,
        "language": upload_data["language"],
        "filename": upload_data["filename"],
        "max_iterations": 1
    }
    res = httpx.post(f"{BASE_URL}/api/review", json=review_payload, timeout=180.0)
    assert res.status_code == 200, f"Review failed: {res.text}"
    review_data = res.json()
    review_id = review_data.get("review_id")
    print(f"  --> Review ID: #{review_id}")
    print(f"  --> Initial Health Score: {review_data.get('health_score')}/10.0")
    print(f"  --> Verdict: {review_data.get('verdict')}")
    print(f"  --> Issues Flagged: {len(review_data.get('issues', []))}")
    print(f"  --> Telemetry Stages: {len(review_data.get('telemetry', []))}")
    for idx, iss in enumerate(review_data.get('issues', [])[:5], 1):
        print(f"      Finding #{idx}: Line {iss.get('line')} [{iss.get('severity')}] {iss.get('title')} ({iss.get('rule_citation')})")

    # 5. Test APPLY FIX BUTTON (/api/remediate)
    print("\n[5] Testing APPLY FIX Button (/api/remediate)...")
    rem_payload = {
        "code": uploaded_code,
        "language": upload_data["language"],
        "filename": upload_data["filename"],
        "issues": review_data.get("issues", []),
        "review_id": review_id
    }
    res = httpx.post(f"{BASE_URL}/api/remediate", json=rem_payload, timeout=180.0)
    assert res.status_code == 200, f"Remediate failed: {res.text}"
    rem_data = res.json()
    print(f"  --> Code Modified: {rem_data.get('modified')}")
    print(f"  --> Remediation Status: {rem_data.get('remediation_status')}")
    print(f"  --> Changelog Count: {len(rem_data.get('changelog', []))}")
    for ch in rem_data.get("changelog", [])[:4]:
        print(f"      * Line {ch.get('line_affected')}: {ch.get('description')}")
    corrected_code = rem_data.get("corrected_code")

    # 6. Test RE-CHECK BUTTON (/api/recheck)
    print("\n[6] Testing RE-CHECK Button (/api/recheck)...")
    recheck_payload = {
        "original_code": uploaded_code,
        "corrected_code": corrected_code,
        "language": upload_data["language"],
        "filename": upload_data["filename"],
        "previous_issues": review_data.get("issues", []),
        "review_id": review_id
    }
    res = httpx.post(f"{BASE_URL}/api/recheck", json=recheck_payload, timeout=180.0)
    assert res.status_code == 200, f"Re-check failed: {res.text}"
    recheck_data = res.json()
    print(f"  --> Re-check Health Score: {recheck_data.get('health_score')}/10.0")
    print(f"  --> Re-check Verdict: {recheck_data.get('verdict')}")
    print(f"  --> Resolved Count: {recheck_data.get('resolved_count')}")
    print(f"  --> Unresolved Count: {recheck_data.get('unresolved_count')}")

    # 7. Test DOWNLOAD SOURCE BUTTON (/api/download)
    print("\n[7] Testing DOWNLOAD SOURCE Button (/api/download)...")
    res = httpx.get(f"{BASE_URL}/api/download?review_id={review_id}", timeout=10.0)
    assert res.status_code == 200, f"Download failed: {res.text}"
    assert len(res.text) > 100
    print(f"  --> Successfully received corrected source code ({len(res.text)} bytes).")

    # 8. Test DOWNLOAD REPORT & COPY REPORT BUTTONS (/api/audit-report)
    print("\n[8] Testing DOWNLOAD & COPY REPORT Buttons (/api/audit-report)...")
    res = httpx.get(f"{BASE_URL}/api/audit-report?review_id={review_id}", timeout=10.0)
    assert res.status_code == 200, f"Audit report failed: {res.text}"
    assert "PR AGENT AUDIT REPORT" in res.text or "AUDIT REPORT" in res.text
    print(f"  --> Successfully received certified Audit Report ({len(res.text)} bytes).")

    # 9. Test RAG BENCHMARK BUTTON (/api/rag/query & /api/rag/stats)
    print("\n[9] Testing RAG Benchmark Buttons (/api/rag/query & /api/rag/stats)...")
    rag_res = httpx.post(f"{BASE_URL}/api/rag/query", json={"query": "SQL injection concatenation", "top_k": 3}, timeout=10.0)
    assert rag_res.status_code == 200
    stats_res = httpx.get(f"{BASE_URL}/api/rag/stats", timeout=10.0)
    assert stats_res.status_code == 200
    print(f"  --> RAG query returned {rag_res.json().get('count')} results.")
    print(f"  --> Total vector catalog size: {stats_res.json().get('stats', {}).get('total_vectors')} vectors.")

    # 10. Test GATEWAY SETTINGS BUTTON (/api/gateway/configure)
    print("\n[10] Testing GATEWAY SETTINGS Configuration Button (/api/gateway/configure)...")
    conf_res = httpx.post(f"{BASE_URL}/api/gateway/configure", json={"provider": "ollama"}, timeout=10.0)
    assert conf_res.status_code == 200
    print(f"  --> Gateway configuration updated: {conf_res.json().get('badge')}")

    print("\n=================================================================")
    print("   [SUCCESS] ALL BUTTON BACKEND APIS VERIFIED 100% FUNCTIONAL!")
    print("=================================================================")
    return True

if __name__ == "__main__":
    success = run_e2e_test()
    sys.exit(0 if success else 1)
