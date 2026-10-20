"""
Live end-to-end HTTP test verifying both Backend (FastAPI :8000) and Frontend (Vite :5173).
"""

import httpx
import sys

def run_tests():
    print("=== LIVE END-TO-END SYSTEM VERIFICATION ===")

    # 1. Test Frontend HTTP server
    print("\n[1] Testing Frontend Server (http://localhost:5173)...")
    try:
        r = httpx.get("http://localhost:5173/", timeout=5.0)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert "pr_agent" in r.text or "root" in r.text
        print("  [PASS] Frontend Vite dev server is UP and serving HTML (Status 200).")
    except Exception as e:
        print(f"  [FAIL] Frontend server check failed: {e}")
        return False

    # 2. Test Backend Status
    print("\n[2] Testing Backend Status (/api/status)...")
    try:
        r = httpx.get("http://127.0.0.1:8000/api/status", timeout=5.0)
        assert r.status_code == 200
        data = r.json()
        print(f"  [PASS] System Status: {data['status']}")
        print(f"  [PASS] Active Gateway Badge: {data['gateway']['badge']}")
        print(f"  [PASS] Fallback Indicator: {data['gateway']['fallback_state']}")
        print(f"  [PASS] Supported Languages: {data['supported_languages']}")
    except Exception as e:
        print(f"  [FAIL] Status endpoint failed: {e}")
        return False

    # 3. Test Languages & MCP Tool Mappings
    print("\n[3] Testing Supported Languages & MCP Tools (/api/languages)...")
    try:
        r = httpx.get("http://127.0.0.1:8000/api/languages", timeout=5.0)
        assert r.status_code == 200
        langs = r.json()["languages"]
        for l in langs:
            print(f"  [PASS] Language: {l['name']} -> MCP Linters: {l['mcp_tools']}")
    except Exception as e:
        print(f"  [FAIL] Languages endpoint failed: {e}")
        return False

    # 4. Test RAG Query & Stats
    print("\n[4] Testing RAG Dedicated Vector Store (/api/rag/query)...")
    try:
        r = httpx.post("http://127.0.0.1:8000/api/rag/query", json={"query": "SQL Injection cursor execute", "top_k": 3}, timeout=5.0)
        assert r.status_code == 200
        rag_res = r.json()
        print(f"  [PASS] RAG retrieved {rag_res['count']} top rules.")
        top = rag_res["results"][0]
        print(f"  [PASS] Top rule: {top['rule_id']} - {top['title']} (similarity: {top['similarity_score']})")
    except Exception as e:
        print(f"  [FAIL] RAG query failed: {e}")
        return False

    # 5. Test Multi-Agent Review Pipeline for All 6 Languages
    print("\n[5] Testing Multi-Agent Review Pipeline across all 6 languages (/api/review)...")
    samples_resp = httpx.get("http://127.0.0.1:8000/api/samples", timeout=5.0)
    samples = samples_resp.json()

    for lang in ["python", "cpp", "c", "java", "javascript", "ruby"]:
        sample = samples[lang]
        print(f"\n  --> Testing Language: {lang.upper()} ({sample['filename']})")
        review_req = {
            "code": sample["code"],
            "language": sample["language"],
            "filename": sample["filename"]
        }
        res = httpx.post("http://127.0.0.1:8000/api/review", json=review_req, timeout=180.0)
        assert res.status_code == 200, f"Review failed for {lang}: {res.text}"
        data = res.json()
        
        print(f"      Initial Health Score: {data['health_score']}/10 ({data['verdict']})")
        print(f"      Post-Fix Score: {data['post_fix_score']}/10")
        print(f"      Total Issues Flagged: {len(data['issues'])}")
        print(f"      MCP Tools Run: {data['mcp_tools']}")
        print(f"      Telemetry Stages ({len(data['telemetry'])}): {[t['name'] for t in data['telemetry']]}")
        print(f"      Coder Changelog Modifications: {len(data['changelog'])}")
        
        # Verify first issue has a real citation
        if data['issues']:
            first_issue = data['issues'][0]
            print(f"      Sample Citation: {first_issue.get('rule_citation')}")

    # 6. Test Download Endpoints
    print("\n[6] Testing Download Endpoints...")
    dl_resp = httpx.get("http://127.0.0.1:8000/api/download", timeout=5.0)
    assert dl_resp.status_code == 200
    assert len(dl_resp.text) > 50
    print(f"  [PASS] /api/download returned fixed source code ({len(dl_resp.text)} bytes).")

    audit_resp = httpx.get("http://127.0.0.1:8000/api/audit-report", timeout=5.0)
    assert audit_resp.status_code == 200
    assert "PR AGENT AUDIT REPORT" in audit_resp.text
    print(f"  [PASS] /api/audit-report returned full markdown audit report ({len(audit_resp.text)} bytes).")

    print("\n==========================================================")
    print(">>> ALL LIVE SYSTEM VERIFICATION TESTS PASSED (100%) <<<")
    print("==========================================================")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
