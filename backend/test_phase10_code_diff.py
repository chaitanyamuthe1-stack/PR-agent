"""
Unit & Integration Test Suite for Phase 10 — Code Diff and Automatic Correction (PR Agent).

Validates:
1. Original Source Preservation: Uploaded original source is preserved without mutation throughout review and auto-fix.
2. Safe Downloads & Path Traversal Prevention: Strict path sanitization on download endpoints, preventing traversal attacks.
3. Silent Empty/Truncated Output Prevention: Download endpoints reject empty or whitespace-only code with HTTP 400.
4. Language Extension Mapping: Proper extension for each supported language (.py, .cpp, .c, .java, .js, .rb).
5. Structural Syntax Validation Rejection: Syntax validator rejects malformed/corrupted rewrites and unclosed delimiters.
6. Coder Agent Rejection Fallback: Rejection of syntactically invalid rewrites preserves original code and logs changelog.
7. Refactoring Changelog Completeness: Verified changelog metadata (change_type, line_affected, rule_citation, description).
8. Re-check Pipeline Execution & Verifiable Evidence: Real MCP analyzer execution verifies defect eradication without false claims.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

# Add workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app, REVIEW_CACHE, CACHE_LOCK, LATEST_REVIEW_CACHE
from backend.graph import validate_code_syntax, coder_agent_node, run_full_pipeline
from backend.agents.coder_agent import run_coder_agent, _apply_deterministic_fixes
from backend.samples import SAMPLES


class TestPhase10CodeDiffAndAutoCorrection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_1_original_source_preservation(self):
        """Verify original uploaded source code is preserved intact throughout the pipeline."""
        original = SAMPLES["python"]["code"]
        
        # Test coder agent directly
        issues = [
            {
                "line": 9,
                "title": "SQL Injection in get_user_profile",
                "severity": "critical",
                "cwe": "CWE-89",
                "rule_citation": "OWASP:A03:2021",
                "recommendation": "Use parameterized queries."
            }
        ]
        det_code, changelog = _apply_deterministic_fixes(original, "python", issues)
        
        self.assertNotEqual(original, det_code, "Deterministic fixer should generate modified code.")
        self.assertGreater(len(changelog), 0, "Changelog must record applied modifications.")

        # Test state machine preservation
        mock_state = {
            "code": original,
            "original_code": original,
            "language": "python",
            "filename": "pr_agent_test.py",
            "provider": "mock",
            "mcp_tools": ["flake8", "bandit"],
            "static_findings": [],
            "rag_context": [],
            "security_findings": issues,
            "bug_findings": [],
            "all_issues": issues,
            "unresolved_findings": issues,
            "resolved_findings": [],
            "verified_findings": [],
            "unverified_recommendations": [],
            "unresolved_count": len(issues),
            "resolved_count": 0,
            "remediation_status": "NOT_REQUIRED",
            "auto_fix_failure": False,
            "health_score": 6.0,
            "initial_health_score": 6.0,
            "verdict": "FIX REQUIRED",
            "summary": "Issues found",
            "counts": {"critical": 1, "high": 0, "medium": 0, "low": 0},
            "corrected_code": original,
            "changelog": [],
            "iteration_count": 0,
            "max_iterations": 2,
            "telemetry": [],
            "gateway_info": {},
            "tools_execution": [],
            "coverage": "partial",
            "coverage_explanation": ""
        }
        res_node = coder_agent_node(mock_state)
        # Verify original code in state remains unmodified
        self.assertEqual(mock_state["original_code"], original, "Original code was mutated in state!")
        self.assertIn("corrected_code", res_node)
        self.assertNotEqual(res_node["corrected_code"], original)

    def test_2_safe_download_path_traversal_prevention(self):
        """Verify download endpoint strips path traversal characters and produces safe filenames."""
        traversal_name = "../../etc/passwd/malicious_script.py"
        sample_code = "import os\nprint('safe corrected source')\n"
        review_id = "test-path-traversal-id"
        
        with CACHE_LOCK:
            REVIEW_CACHE[review_id] = {
                "review_id": review_id,
                "original_code": "print('original')",
                "corrected_code": sample_code,
                "language": "python",
                "filename": traversal_name
            }

        # Request download
        dl_resp = self.client.get(f"/api/download?review_id={review_id}")
        self.assertEqual(dl_resp.status_code, 200)
        
        # Verify Content-Disposition header does NOT contain path traversal characters
        disp = dl_resp.headers.get("Content-Disposition", "")
        self.assertIn("attachment; filename=", disp)
        filename_part = disp.split("filename=")[-1].strip('"')
        
        self.assertNotIn("..", filename_part, "Path traversal sequence '..' detected in filename!")
        self.assertNotIn("/", filename_part, "Path separator '/' detected in filename!")
        self.assertNotIn("\\", filename_part, "Path separator '\\' detected in filename!")
        self.assertEqual(filename_part, "malicious_script_corrected.py")
        
        # Verify downloaded content contains the exact corrected source
        self.assertEqual(dl_resp.content.decode("utf-8"), sample_code)

    def test_3_silent_empty_download_rejection(self):
        """Verify download endpoint rejects empty code with HTTP 400 instead of producing empty files silently."""
        empty_id = "test-empty-code-id"
        with CACHE_LOCK:
            REVIEW_CACHE[empty_id] = {
                "review_id": empty_id,
                "original_code": "def foo(): pass",
                "corrected_code": "   \n\t  ",  # Whitespace only
                "language": "python",
                "filename": "empty_test.py"
            }

        dl_resp = self.client.get(f"/api/download?review_id={empty_id}")
        self.assertEqual(dl_resp.status_code, 400)
        self.assertIn("empty", dl_resp.json()["detail"].lower())

    def test_4_language_extension_mapping_on_download(self):
        """Verify downloads use appropriate language extensions for all supported languages."""
        lang_ext_tests = [
            ("python", ".py"),
            ("cpp", ".cpp"),
            ("c", ".c"),
            ("java", ".java"),
            ("javascript", ".js"),
            ("ruby", ".rb")
        ]

        for lang, expected_ext in lang_ext_tests:
            test_id = f"test-ext-{lang}"
            with CACHE_LOCK:
                REVIEW_CACHE[test_id] = {
                    "review_id": test_id,
                    "original_code": f"// code for {lang}",
                    "corrected_code": f"// safe code for {lang}\nint main() {{ return 0; }}",
                    "language": lang,
                    "filename": f"sample_prog.{lang}"
                }

            resp = self.client.get(f"/api/download?review_id={test_id}")
            self.assertEqual(resp.status_code, 200)
            disp = resp.headers.get("Content-Disposition", "")
            self.assertTrue(disp.endswith(f'{expected_ext}"'), f"Expected extension {expected_ext} in {disp}")

    def test_5_syntax_validation_rejects_corrupted_rewrites(self):
        """Verify validate_code_syntax catches broken syntax and unclosed delimiters."""
        # Valid Python
        valid_py = "def add(a, b):\n    return a + b\n"
        is_val, err = validate_code_syntax(valid_py, "python")
        self.assertTrue(is_val)
        self.assertIsNone(err)

        # Invalid Python syntax
        broken_py = "def broken(\n    return 42\n"
        is_val, err = validate_code_syntax(broken_py, "python")
        self.assertFalse(is_val)
        self.assertIn("SyntaxError", err)

        # Mismatched delimiter in C/C++/Java
        broken_c = "int main() { if (x > 0) { return 1; ] return 0; }"
        is_val, err = validate_code_syntax(broken_c, "cpp")
        self.assertFalse(is_val)
        self.assertIn("Mismatched delimiter", err)

        # Unclosed delimiter in JavaScript
        broken_js = "function process() { const data = [1, 2, 3; return data; }"
        is_val, err = validate_code_syntax(broken_js, "javascript")
        self.assertFalse(is_val)
        self.assertIn("Mismatched delimiter", err)

    def test_6_coder_agent_rejection_fallback(self):
        """Verify coder_agent node rejects invalid syntax and reverts to original code with explanation."""
        mock_state = {
            "code": "def process():\n    return 1\n",
            "language": "python",
            "unresolved_findings": [{"title": "Dummy Issue", "severity": "high", "line": 1}],
            "rag_context": [],
            "provider": "mock",
            "changelog": [],
            "iteration_count": 0,
            "telemetry": []
        }

        # Mock run_coder_agent returning syntax error
        def mock_bad_coder(*args, **kwargs):
            return "def process(:\n    broken syntax!!!", [{"change_type": "bad", "line_affected": "1"}]

        import backend.graph as graph_mod
        orig_runner = graph_mod.run_coder_agent
        try:
            graph_mod.run_coder_agent = mock_bad_coder
            res = coder_agent_node(mock_state)
            
            # Must revert code to pre-correction safe code
            self.assertEqual(res["code"], mock_state["code"])
            self.assertEqual(res["remediation_status"], "FAILED")
            self.assertTrue(res["auto_fix_failure"])
            self.assertTrue(any(ch.get("change_type") == "validation_rejected" for ch in res["changelog"]))
        finally:
            graph_mod.run_coder_agent = orig_runner

    def test_7_refactoring_changelog_structure(self):
        """Verify refactoring changelog contains all required audit fields."""
        python_sample = SAMPLES["python"]["code"]
        issues = [
            {
                "line": 9,
                "title": "SQL Injection in get_user_profile",
                "severity": "critical",
                "cwe": "CWE-89",
                "rule_citation": "OWASP:A03:2021",
                "recommendation": "Use parameterized queries."
            }
        ]
        code_fixed, changelog = _apply_deterministic_fixes(python_sample, "python", issues)
        
        self.assertNotEqual(code_fixed, python_sample, "Deterministic fixer did not modify code.")
        self.assertTrue(len(changelog) > 0, "Changelog must not be empty when code was modified.")
        
        for entry in changelog:
            self.assertIn("change_type", entry)
            self.assertIn("line_affected", entry)
            self.assertIn("rule_citation", entry)
            self.assertIn("description", entry)
            self.assertTrue(len(entry["description"]) > 10)

    def test_8_recheck_api_endpoint_verifies_remediation(self):
        """Verify /api/recheck executes real static analysis and updates verdict accurately."""
        from unittest.mock import patch
        
        # 1. Unfixed code re-checked should have unresolved issues and verdict FIX REQUIRED
        python_sample = SAMPLES["python"]["code"]
        
        # Mock gateway.generate to return fast mock response if LLM fallback triggered
        mock_resp = '{"findings": [{"line": 9, "severity": "critical", "category": "security", "title": "SQL Injection", "description": "SQL Injection", "recommendation": "Use params", "cwe": "CWE-89", "rule_citation": "OWASP:A03:2021"}]}'
        with patch("backend.llm_gateway.gateway.generate", return_value=mock_resp):
            resp_unfixed = self.client.post("/api/recheck", json={
                "original_code": python_sample,
                "corrected_code": python_sample,
                "language": "python",
                "filename": "vuln_sample.py"
            })
            self.assertEqual(resp_unfixed.status_code, 200)
            data_unfixed = resp_unfixed.json()
            self.assertGreater(data_unfixed["unresolved_count"], 0)
            self.assertEqual(data_unfixed["verdict"], "FIX REQUIRED")
            self.assertEqual(data_unfixed["remediation_status"], "PARTIAL")

            # 2. Fixed clean code re-checked should have 0 unresolved issues and verdict CLEAN
            clean_python = (
                "import sqlite3\n\n"
                "def safe_get_user(user_id: int):\n"
                "    conn = sqlite3.connect('database.db')\n"
                "    cursor = conn.cursor()\n"
                "    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))\n"
                "    return cursor.fetchone()\n"
            )
            resp_clean = self.client.post("/api/recheck", json={
                "original_code": python_sample,
                "corrected_code": clean_python,
                "language": "python",
                "filename": "vuln_sample.py"
            })
            self.assertEqual(resp_clean.status_code, 200)
            data_clean = resp_clean.json()
            self.assertEqual(data_clean["unresolved_count"], 0)
            self.assertEqual(data_clean["verdict"], "CLEAN")
            self.assertEqual(data_clean["remediation_status"], "SUCCESS")
            self.assertEqual(data_clean["post_fix_score"], 10.0)


if __name__ == "__main__":
    unittest.main()
