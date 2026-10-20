"""
Phase 6 Automated Test Suite — Static Analysis & Language Support (PR Agent).
Tests:
1. Correct routing of Python, C, C++, Java, JavaScript, and Ruby.
2. Accurate capture of exit codes, execution time, findings, and tool availability.
3. Common finding schema adherence for all findings.
4. Truthful availability reporting (never claiming uninstalled tools ran).
5. Distinguishing clean analysis from unavailable analysis and partial coverage.
6. Safe syntax verification without executing untrusted application logic.
7. Fixture verification on clean and vulnerable code for all 6 languages.
8. Simulation error flags for resilient pipeline degradation.
"""

import os
import sys
import unittest
from backend.mcp_tools import (
    run_static_analysis,
    get_all_tools_status,
    get_mcp_tools_for_language,
    TOOL_CATALOG,
    LANGUAGE_TOOL_MAPPING
)

class TestPhase6StaticAnalysis(unittest.TestCase):
    """Verifies all Phase 6 static analysis requirements."""

    def test_01_tool_catalog_and_status(self):
        """Verifies tool catalog has all required tools and documents installation."""
        status = get_all_tools_status()
        tools = status["tools"]
        expected_tools = ["bandit", "pylint", "cppcheck", "gcc", "g++", "checkstyle", "javac", "eslint", "node", "rubocop", "ruby"]
        for t in expected_tools:
            self.assertIn(t, tools, f"Missing tool {t} in catalog")
            self.assertIn("install_cmd", tools[t])
            self.assertTrue(len(tools[t]["install_cmd"]) > 0)
            self.assertIn("installed", tools[t])

        # Verify language coverage structure
        supported = status["supported_languages"]
        for lang in ["python", "cpp", "c", "java", "javascript", "ruby"]:
            self.assertIn(lang, supported)
            self.assertIn(supported[lang]["coverage"], ["full", "partial"])

    def test_02_truthful_tool_reporting(self):
        """Verifies tools missing in PATH are truthfully reported as unavailable."""
        res_cpp = run_static_analysis("int main() { return 0; }", "cpp")
        execs = res_cpp["tools_execution"]
        cppcheck_exec = next((e for e in execs if e["tool"] == "cppcheck"), None)
        self.assertIsNotNone(cppcheck_exec)

        # On this environment cppcheck is not installed in PATH
        if cppcheck_exec["available"] is False:
            self.assertIsNone(cppcheck_exec["exit_code"])
            self.assertEqual(cppcheck_exec["execution_time_ms"], 0.0)
            self.assertEqual(cppcheck_exec["status"], "unavailable")
            self.assertIn("not found in PATH", cppcheck_exec["error"])
            self.assertEqual(res_cpp["coverage"], "partial")

        # Python linters: bandit & pylint are installed in PATH on this system
        res_py = run_static_analysis("x = 1\n", "python")
        py_execs = res_py["tools_execution"]
        bandit_exec = next((e for e in py_execs if e["tool"] == "bandit"), None)
        self.assertIsNotNone(bandit_exec)
        if bandit_exec["available"] is True:
            self.assertIsNotNone(bandit_exec["exit_code"])
            self.assertTrue(bandit_exec["execution_time_ms"] >= 0.0)
            self.assertIn(bandit_exec["status"], ["clean", "findings_detected"])

    def test_03_common_finding_schema(self):
        """Verifies all findings strictly follow the normalized schema."""
        required_keys = {"tool", "rule_id", "line", "column", "message", "severity", "category", "cwe", "tool_available", "evidence_type"}
        valid_severities = {"critical", "high", "medium", "low", "info"}
        valid_categories = {"security", "bug", "style", "performance", "maintainability"}

        test_cases = [
            ("python", "import os\nos.system('rm -rf ' + path)"),
            ("cpp", "void f(char* p) { char b[4]; strcpy(b, p); }"),
            ("java", "class X { String SECRET_KEY = \"HARDCODED_KEY_1234567890\"; }"),
            ("javascript", "function f(cmd) { eval(cmd); }"),
            ("ruby", "def f(sql); DB.query(\"SELECT * FROM u WHERE id = #{sql}\"); end")
        ]

        for lang, code in test_cases:
            res = run_static_analysis(code, lang)
            self.assertGreater(res["total_findings"], 0, f"Expected findings for vulnerable {lang} sample")
            for f in res["findings"]:
                for key in required_keys:
                    self.assertIn(key, f, f"Finding missing key '{key}' in {lang}")
                self.assertIn(f["severity"], valid_severities)
                self.assertIn(f["category"], valid_categories)
                self.assertTrue(f["cwe"].startswith("CWE-"), f"CWE must start with CWE-: {f['cwe']}")
                self.assertIsInstance(f["line"], int)
                self.assertGreaterEqual(f["line"], 1)
                self.assertIsInstance(f["column"], int)
                self.assertGreaterEqual(f["column"], 1)
                self.assertIsInstance(f["tool_available"], bool)
                self.assertIn(f["evidence_type"], ["native_tool_output", "compiler_syntax_check", "builtin_pattern_rule"])

    def test_04_fixtures_all_languages(self):
        """Verifies clean fixtures have 0 defects and vulnerable fixtures have identified flaws across all 6 languages."""
        fixtures = [
            ("python", "test_files/fixtures/python/clean.py", "test_files/fixtures/python/vulnerable.py"),
            ("cpp", "test_files/fixtures/cpp/clean.cpp", "test_files/fixtures/cpp/vulnerable.cpp"),
            ("c", "test_files/fixtures/c/clean.c", "test_files/fixtures/c/vulnerable.c"),
            ("java", "test_files/fixtures/java/Clean.java", "test_files/fixtures/java/Vulnerable.java"),
            ("javascript", "test_files/fixtures/javascript/clean.js", "test_files/fixtures/javascript/vulnerable.js"),
            ("ruby", "test_files/fixtures/ruby/clean.rb", "test_files/fixtures/ruby/vulnerable.rb"),
        ]

        for lang, clean_path, vuln_path in fixtures:
            self.assertTrue(os.path.exists(clean_path), f"Clean fixture missing: {clean_path}")
            self.assertTrue(os.path.exists(vuln_path), f"Vuln fixture missing: {vuln_path}")

            with open(clean_path, "r", encoding="utf-8") as f:
                clean_code = f.read()
            with open(vuln_path, "r", encoding="utf-8") as f:
                vuln_code = f.read()

            res_clean = run_static_analysis(clean_code, lang)
            res_vuln = run_static_analysis(vuln_code, lang)

            # Clean fixture verification
            self.assertEqual(res_clean["total_findings"], 0, f"Clean fixture for {lang} has findings: {res_clean['findings']}")
            self.assertIn("clean", res_clean["status"].lower())

            # Vulnerable fixture verification
            self.assertGreater(res_vuln["total_findings"], 0, f"Vulnerable fixture for {lang} should have findings")
            self.assertEqual(res_vuln["status"], "findings_detected")
            cwes = {f["cwe"] for f in res_vuln["findings"]}
            self.assertTrue(len(cwes) > 0, f"Vulnerable {lang} fixture must have CWEs")

    def test_05_safe_syntax_check_without_untrusted_execution(self):
        """Verifies syntax check catches errors without executing untrusted payload."""
        # Malicious side effect payload in Python syntax test
        malicious_py = "import os; os.environ['PR_AGENT_EXPLOITED'] = '1'\ndef broken( { pass"
        if "PR_AGENT_EXPLOITED" in os.environ:
            del os.environ["PR_AGENT_EXPLOITED"]

        res_py = run_static_analysis(malicious_py, "python")
        self.assertNotIn("PR_AGENT_EXPLOITED", os.environ, "Untrusted Python code was executed!")
        syntax_findings = [f for f in res_py["findings"] if "syntax" in f["rule_id"].lower() or "syntax" in f["message"].lower()]
        self.assertGreater(len(syntax_findings), 0, "Syntax error was not detected")

        # Malicious side effect in JavaScript
        malicious_js = "process.env.PR_AGENT_EXPLOITED = '1'; function bad( { return; }"
        res_js = run_static_analysis(malicious_js, "javascript")
        self.assertNotIn("PR_AGENT_EXPLOITED", os.environ, "Untrusted JS code was executed!")
        js_syntax = [f for f in res_js["findings"] if "syntax" in f["rule_id"].lower() or "syntax" in f["message"].lower()]
        self.assertGreater(len(js_syntax), 0, "JS syntax error was not detected")

    def test_06_simulation_flags(self):
        """Verifies simulation flags report degraded availability truthfully."""
        os.environ["PR_AGENT_SIMULATE_MCP_FAIL"] = "1"
        try:
            res = run_static_analysis("print('hello')", "python")
            self.assertEqual(res["status"], "MCP UNAVAILABLE")
            self.assertEqual(res["coverage"], "unavailable")
        finally:
            del os.environ["PR_AGENT_SIMULATE_MCP_FAIL"]

        os.environ["PR_AGENT_SIMULATE_ANALYZER_FAIL"] = "1"
        try:
            res = run_static_analysis("print('hello')", "python")
            self.assertEqual(res["status"], "ANALYZER UNAVAILABLE")
            self.assertEqual(res["coverage"], "unavailable")
        finally:
            del os.environ["PR_AGENT_SIMULATE_ANALYZER_FAIL"]


if __name__ == "__main__":
    unittest.main()
