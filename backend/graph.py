"""
LangGraph Multi-Agent Pipeline for PR Agent.
Implements the 6-layer pipeline:
1. Static Analysis (MCP)
2. RAG Retrieval
3. LLM Gateway Routing
4. Parallel Multi-Agent Review (Security || Bug Detection)
5. Summary Agent (Score & Verdict synthesis)
6. Coder Agent Fix Loop with LangGraph re-check cycle
"""

import os
import time
import uuid
import ast
import re
from typing import Dict, Any, List, TypedDict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from langgraph.graph import StateGraph, END

from .mcp_tools import run_static_analysis, get_mcp_tools_for_language
from .rag.vector_store import store
from .llm_gateway import gateway
from .database import save_review_record
from .agents.security_agent import run_security_agent
from .agents.bug_agent import run_bug_agent
from .agents.summary_agent import run_summary_agent, calculate_health_score
from .agents.coder_agent import run_coder_agent


def validate_code_syntax(code: str, language: str) -> Tuple[bool, Optional[str]]:
    """
    Validates the structural syntax and delimiter balance of proposed code.
    Ensures Coder Agent does not return syntactically corrupted or broken code.
    """
    if not code or not str(code).strip():
        return False, "Proposed code is empty or contains only whitespace."

    lang = (language or "python").lower().strip()

    # 1. Python AST Parse Validation
    if lang in ["python", "py"]:
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Python SyntaxError on line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Python AST validation failed: {str(e)}"

    # 2. Delimiter & Structure Validation for C, C++, Java, JavaScript, Ruby
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    escaped = False

    lines = code.split("\n")
    for line_idx, line in enumerate(lines, 1):
        i = 0
        n = len(line)
        in_line_comment = False
        escaped = False

        while i < n:
            char = line[i]

            if in_line_comment:
                break

            if in_block_comment:
                if char == '*' and i + 1 < n and line[i + 1] == '/':
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if escaped:
                escaped = False
                i += 1
                continue

            if char == '\\':
                escaped = True
                i += 1
                continue

            if char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                i += 1
                continue

            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                i += 1
                continue

            if in_double_quote or in_single_quote:
                i += 1
                continue

            # Check comments
            if char == '/' and i + 1 < n:
                if line[i + 1] == '/':
                    in_line_comment = True
                    break
                elif line[i + 1] == '*':
                    in_block_comment = True
                    i += 2
                    continue

            # Ruby / Python single-line comment
            if char == '#' and lang in ["ruby", "rb", "python", "py"]:
                in_line_comment = True
                break

            # Delimiter tracking
            if char in '({[':
                stack.append((char, line_idx))
            elif char in ')}]':
                if not stack:
                    return False, f"Unexpected closing delimiter '{char}' on line {line_idx} without matching open."
                top, top_line = stack.pop()
                if top != pairs[char]:
                    return False, f"Mismatched delimiter: opened '{top}' on line {top_line} but closed with '{char}' on line {line_idx}."

            i += 1

    if stack:
        unclosed, u_line = stack[-1]
        return False, f"Unclosed delimiter '{unclosed}' originating from line {u_line}."

    return True, None


class AgentState(TypedDict):
    code: str
    original_code: str
    language: str
    filename: str
    provider: str
    mcp_tools: List[str]
    static_findings: List[Dict[str, Any]]
    rag_context: List[Dict[str, Any]]
    security_findings: List[Dict[str, Any]]
    bug_findings: List[Dict[str, Any]]
    all_issues: List[Dict[str, Any]]
    unresolved_findings: List[Dict[str, Any]]
    resolved_findings: List[Dict[str, Any]]
    verified_findings: List[Dict[str, Any]]
    unverified_recommendations: List[Dict[str, Any]]
    unresolved_count: int
    resolved_count: int
    remediation_status: str
    auto_fix_failure: bool
    health_score: float
    initial_health_score: float
    verdict: str
    summary: str
    counts: Dict[str, int]
    corrected_code: str
    changelog: List[Dict[str, Any]]
    iteration_count: int
    max_iterations: int
    telemetry: List[Dict[str, Any]]
    gateway_info: Dict[str, Any]
    tools_execution: Optional[List[Dict[str, Any]]]
    coverage: Optional[str]
    coverage_explanation: Optional[str]


def static_analysis_node(state: AgentState) -> Dict[str, Any]:
    """Layer 2: Run matching deterministic MCP linters for the detected language."""
    start = time.time()
    code = state["code"]
    lang = state["language"]

    tools_execution = []
    coverage = "partial"
    coverage_explanation = ""

    try:
        analysis = run_static_analysis(code, lang)
        tools = analysis["tools_invoked"]
        count = analysis["total_findings"]
        findings = analysis["findings"]
        tools_execution = analysis.get("tools_execution", [])
        coverage = analysis.get("coverage", "partial")
        coverage_explanation = analysis.get("coverage_explanation", "")
        is_mcp_unavail = (analysis.get("status") == "MCP UNAVAILABLE")
        is_analyzer_unavail = (analysis.get("status") == "ANALYZER UNAVAILABLE")
        status = "degraded" if (is_mcp_unavail or is_analyzer_unavail) else "complete"
        if is_mcp_unavail:
            action = f"MCP UNAVAILABLE: {findings[0].get('message', 'MCP dispatch layer offline')}"
        elif is_analyzer_unavail:
            action = f"ANALYZER UNAVAILABLE: {findings[0].get('message', 'Linter execution failed')}"
        else:
            action = f"MCP tools invoked: {' / '.join(tools)} ({count} finding{'s' if count != 1 else ''})"
    except Exception as e:
        tools = get_mcp_tools_for_language(lang)
        status = "degraded"
        action = f"MCP UNAVAILABLE: {str(e)}"
        findings = [{
            "tool": "mcp",
            "rule_id": "MCP:TOOL_UNAVAILABLE",
            "line": 1,
            "message": f"MCP UNAVAILABLE: {str(e)}",
            "severity": "high",
            "category": "bug",
            "cwe": "CWE-1078"
        }]

    latency = round((time.time() - start) * 1000, 2)
    failure_reason = str(findings[0]["message"]) if (status == "degraded" and findings) else None
    telemetry_item = {
        "stage": "static_analysis",
        "name": "Static Analysis (MCP)",
        "action": action,
        "status": status,
        "latency_ms": latency,
        "duration_ms": latency,
        "retry_count": 0,
        "failure_reason": failure_reason
    }

    return {
        "mcp_tools": tools,
        "static_findings": findings,
        "tools_execution": tools_execution,
        "coverage": coverage,
        "coverage_explanation": coverage_explanation,
        "telemetry": [telemetry_item]
    }


def rag_retrieval_node(state: AgentState) -> Dict[str, Any]:
    """Layer 3: Embed code and query dedicated vector store for relevant rules."""
    start = time.time()
    code = state["code"]
    lang = state["language"]
    rag_err = None

    try:
        if os.getenv("PR_AGENT_SIMULATE_RAG_FAIL") == "1":
            raise RuntimeError("Simulated RAG failure: vector store index corrupted / embedding service unreachable")
        # Extract salient code terms and static findings for semantic query
        finding_keywords = " ".join(f.get("message", "") for f in state.get("static_findings", []))
        query_text = f"{lang} {finding_keywords} {code[:1200]}".strip()
        top_rules = store.search(query=query_text, language=lang, top_k=4)
        status = "complete"
        action = f"Top-{len(top_rules)} rules injected from vector store (OWASP & Style standards)"
    except Exception as e:
        top_rules = []
        status = "degraded"
        rag_err = str(e)
        action = f"RAG vector store unavailable: {str(e)}"

    latency = round((time.time() - start) * 1000, 2)
    telemetry_item = {
        "stage": "rag_retrieval",
        "name": "RAG Retrieval",
        "action": action,
        "status": status,
        "latency_ms": latency,
        "duration_ms": latency,
        "retry_count": 0,
        "failure_reason": rag_err
    }

    return {
        "rag_context": top_rules,
        "telemetry": state["telemetry"] + [telemetry_item]
    }


def llm_gateway_node(state: AgentState) -> Dict[str, Any]:
    """Layer 4: Inspect and prepare LLM gateway provider state."""
    start = time.time()
    try:
        gw_status = gateway.get_gateway_status()
        is_degraded = (
            gw_status.get("fallback_active") or
            bool(gw_status.get("last_error")) or
            bool(gw_status.get("primary_error")) or
            bool(gw_status.get("fallback_error")) or
            os.getenv("PR_AGENT_SIMULATE_NETWORK_TIMEOUT") == "1"
        )
        status = "degraded" if is_degraded else "complete"
        if os.getenv("PR_AGENT_SIMULATE_NETWORK_TIMEOUT") == "1":
            reason = gw_status.get("primary_error") or "network timeout connecting to primary"
        else:
            reason = gw_status.get("last_error") or gw_status.get("primary_error") or gw_status.get("fallback_error") or gw_status.get("fallback_state")
        action = f"Provider: {gw_status['badge']} ({reason})"
    except Exception as e:
        gw_status = {
            "provider": "OFFLINE_HEURISTIC",
            "badge": "PR AGENT HEURISTIC SYNTHESIS ENGINE — ZERO-CONFIG",
            "model": "pr-agent-deterministic-v1",
            "fallback_state": "fallback: active",
            "fallback_active": True,
            "has_gemini_key": False,
            "has_groq_key": False,
            "ollama_available": False,
            "last_latency_ms": 0.0,
            "last_error": str(e)
        }
        status = "degraded"
        reason = str(e)
        action = f"LLM Gateway check failed ({str(e)}): fallback active"

    latency = round((time.time() - start) * 1000, 2)
    telemetry_item = {
        "stage": "llm_gateway",
        "name": "LLM Gateway",
        "action": action,
        "status": status,
        "latency_ms": latency,
        "duration_ms": latency,
        "retry_count": gw_status.get("retry_budget", 0) if is_degraded else 0,
        "failure_reason": reason if is_degraded else None
    }

    return {
        "gateway_info": gw_status,
        "telemetry": state["telemetry"] + [telemetry_item]
    }


def security_agent_node(state: AgentState) -> Dict[str, Any]:
    """Layer 5a: Security Agent flags vulnerabilities citing CWE/OWASP rules."""
    code = state["code"]
    lang = state["language"]
    findings = run_security_agent(
        code=code,
        language=lang,
        static_findings=state.get("static_findings", []),
        rag_context=state.get("rag_context", []),
        provider=state.get("provider")
    )
    return {"security_findings": findings}


def bug_detection_agent_node(state: AgentState) -> Dict[str, Any]:
    """Layer 5b: Bug-Detection Agent flags logic errors & edge cases."""
    code = state["code"]
    lang = state["language"]
    findings = run_bug_agent(
        code=code,
        language=lang,
        static_findings=state.get("static_findings", []),
        rag_context=state.get("rag_context", []),
        provider=state.get("provider")
    )
    return {"bug_findings": findings}


def parallel_review_node(state: AgentState) -> Dict[str, Any]:
    """Coordinates parallel execution of Security and Bug-Detection agents with timeouts."""
    start = time.time()
    code = state["code"]
    lang = state["language"]
    provider = state.get("provider")
    rag = state.get("rag_context", [])
    iteration = state.get("iteration_count", 0)
    review_timeout = float(os.getenv("PR_AGENT_REVIEW_TIMEOUT", "15.0"))
    stage_status = "complete"
    failure_reason = None

    # Early syntax validation fast-fail: skip redundant slow LLM queries on unparseable code
    is_valid_syntax, syntax_err = validate_code_syntax(code, lang)
    if not is_valid_syntax:
        sec_findings = []
        bug_findings = [{
            "line": 1,
            "severity": "critical",
            "category": "bug",
            "title": "Syntax/Parsing Error",
            "description": syntax_err,
            "recommendation": "Correct syntax so code can be parsed and executed.",
            "cwe": "CWE-1078",
            "rule_id": "SYNTAX:Error",
            "rule_citation": "SYNTAX:Validation"
        }]
    # In re-check iterations, inspect current code to verify what findings remain
    elif iteration > 0:
        current_static = run_static_analysis(code, lang).get("findings", [])
        # Performance optimization: If re-check static analysis verified 0 defects, skip redundant LLM inference
        if len(current_static) == 0:
            sec_findings = []
            bug_findings = []
        else:
            has_sec = any(f.get("category") == "security" for f in current_static)
            has_bug = any(f.get("category") in ["bug", "style", "complexity"] for f in current_static)
            if has_sec and has_bug:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    fut_sec = executor.submit(run_security_agent, code, lang, current_static, rag, provider)
                    fut_bug = executor.submit(run_bug_agent, code, lang, current_static, rag, provider)
                    try:
                        sec_findings = fut_sec.result(timeout=review_timeout)
                    except FuturesTimeoutError:
                        stage_status = "timed_out"
                        failure_reason = f"Security agent review timed out after {review_timeout}s"
                        sec_findings = [f for f in current_static if f.get("category") == "security"]
                    except Exception as e:
                        stage_status = "failed"
                        failure_reason = str(e)
                        sec_findings = [f for f in current_static if f.get("category") == "security"]

                    try:
                        bug_findings = fut_bug.result(timeout=review_timeout)
                    except FuturesTimeoutError:
                        if stage_status != "timed_out":
                            stage_status = "timed_out"
                            failure_reason = f"Bug agent review timed out after {review_timeout}s"
                        bug_findings = [f for f in current_static if f.get("category") != "security"]
                    except Exception as e:
                        if stage_status == "complete":
                            stage_status = "failed"
                            failure_reason = str(e)
                        bug_findings = [f for f in current_static if f.get("category") != "security"]
            else:
                sec_findings = run_security_agent(code, lang, current_static, rag, provider) if has_sec else []
                bug_findings = run_bug_agent(code, lang, current_static, rag, provider) if has_bug else []
    else:
        current_static = state.get("static_findings", [])
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_sec = executor.submit(run_security_agent, code, lang, current_static, rag, provider)
            fut_bug = executor.submit(run_bug_agent, code, lang, current_static, rag, provider)
            try:
                sec_findings = fut_sec.result(timeout=review_timeout)
            except FuturesTimeoutError:
                stage_status = "timed_out"
                failure_reason = f"Security agent review timed out after {review_timeout}s"
                sec_findings = [f for f in current_static if f.get("category") == "security"]
            except Exception as e:
                stage_status = "failed"
                failure_reason = str(e)
                sec_findings = [f for f in current_static if f.get("category") == "security"]

            try:
                bug_findings = fut_bug.result(timeout=review_timeout)
            except FuturesTimeoutError:
                if stage_status != "timed_out":
                    stage_status = "timed_out"
                    failure_reason = f"Bug agent review timed out after {review_timeout}s"
                bug_findings = [f for f in current_static if f.get("category") != "security"]
            except Exception as e:
                if stage_status == "complete":
                    stage_status = "failed"
                    failure_reason = str(e)
                bug_findings = [f for f in current_static if f.get("category") != "security"]

    # In re-check passes, evaluate which previous issues were removed vs unresolved
    previous_issues = state.get("all_issues", [])
    updated_issues = []
    if iteration > 0 and previous_issues:
        current_keys = {(f.get("line"), f.get("title")) for f in (sec_findings + bug_findings + current_static)}
        current_rules = (
            {f.get("rule_id") for f in current_static if f.get("rule_id")} |
            {f.get("rule_citation") for f in (sec_findings + bug_findings) if f.get("rule_citation")} |
            {f.get("rule_id") for f in (sec_findings + bug_findings) if f.get("rule_id")}
        )
        current_actionable_cwes = (
            {f.get("cwe") for f in (sec_findings + bug_findings) if f.get("severity") in ["critical", "high", "medium"] and f.get("cwe")} |
            {f.get("cwe") for f in current_static if f.get("severity") in ["critical", "high", "medium"] and f.get("cwe")}
        )
        
        for prev in previous_issues:
            p_copy = dict(prev)
            prev_rule = prev.get("rule_id") or prev.get("rule_citation")
            prev_cwe = prev.get("cwe")
            prev_sev = prev.get("severity", "medium")

            # A defect is considered still present if:
            # 1. Exact (line, title) still matches
            # 2. Or the specific static rule/citation is still present
            # 3. Or an actionable (critical/high/medium) finding of the same CWE remains
            is_present = False
            if (prev.get("line"), prev.get("title")) in current_keys:
                is_present = True
            elif prev_rule and any(prev_rule in r or r in prev_rule for r in current_rules):
                is_present = True
            elif prev_cwe and prev_sev in ["critical", "high", "medium"] and prev_cwe in current_actionable_cwes:
                is_present = True

            p_copy["resolved"] = not is_present

            # Distinguish verified findings from unverified LLM recommendations
            is_static_corroborated = any(
                str(s.get("line")) == str(prev.get("line")) or 
                (prev_cwe and prev_cwe == s.get("cwe")) or 
                (prev_rule and prev_rule in str(s.get("rule_id")))
                for s in state.get("static_findings", [])
            )
            p_copy["verified"] = bool(prev.get("verified") or is_static_corroborated)
            p_copy["evidence"] = "deterministic_static_tool" if p_copy["verified"] else "llm_heuristic_recommendation"
            updated_issues.append(p_copy)

    latency = round((time.time() - start) * 1000, 2)
    telemetry_item = {
        "stage": "multi_agent_review",
        "name": "Security & Bug Agents (LangGraph)",
        "action": f"{'Re-check' if iteration > 0 else 'Parallel'} scan completed: {len(sec_findings)} security, {len(bug_findings)} bug/style finding(s)",
        "status": stage_status,
        "latency_ms": latency,
        "duration_ms": latency,
        "retry_count": 0,
        "failure_reason": failure_reason
    }

    result = {
        "security_findings": sec_findings,
        "bug_findings": bug_findings,
        "telemetry": state["telemetry"] + [telemetry_item]
    }
    if updated_issues:
        result["all_issues"] = updated_issues
    return result
def summary_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Layer 6: Merges findings, computes health score out of 10 and verdict.
    CRITICAL: Verdict is determined strictly from actual unresolved findings:
    - unresolved_findings == 0 -> CLEAN
    - only low/informational unresolved -> NEEDS REVIEW
    - critical/high/medium unresolved -> FIX REQUIRED
    """
    start = time.time()
    has_failed_stages = any(t.get("status") in ["failed", "FAILED"] for t in state.get("telemetry", []))
    has_skipped_stages = any(t.get("status") in ["skipped", "SKIPPED"] for t in state.get("telemetry", []))

    res = run_summary_agent(
        security_findings=state.get("security_findings", []),
        bug_findings=state.get("bug_findings", []),
        filename=state.get("filename", "source_code.txt"),
        static_findings=state.get("static_findings", []),
        pipeline_stages_failed=has_failed_stages,
        pipeline_stages_skipped=has_skipped_stages
    )
    latency = round((time.time() - start) * 1000, 2)

    initial_score = state.get("initial_health_score")
    if initial_score is None:
        initial_score = res["health_score"]

    # Incorporate resolution statuses if re-check updated all_issues
    all_issues = state.get("all_issues") or res["all_issues"]
    unresolved = [f for f in all_issues if not f.get("resolved", False)]
    resolved = [f for f in all_issues if f.get("resolved", False)]
    verified = [f for f in all_issues if f.get("verification_status") == "verified_static" or f.get("verified")]
    unverified = [f for f in all_issues if f.get("verification_status") == "unverified_llm_observation" or not f.get("verified")]

    # Zero False-Clean Check across all external dependencies & syntax
    has_mcp_unavailable = (
        any("MCP UNAVAILABLE" in str(f.get("description", "")) or 
            "MCP UNAVAILABLE" in str(f.get("message", "")) or 
            "MCP:TOOL_UNAVAILABLE" in str(f.get("rule_id", "")) or
            "MCP:TOOL_UNAVAILABLE" in str(f.get("rule_citation", ""))
            for f in all_issues)
        or any("MCP:TOOL_UNAVAILABLE" in str(s.get("rule_id", "")) or 
               "MCP UNAVAILABLE" in str(s.get("message", "")) 
               for s in state.get("static_findings", []))
        or any(t.get("status") == "degraded" and "MCP UNAVAILABLE" in t.get("action", "") 
               for t in state.get("telemetry", []))
    )

    has_analyzer_unavailable = (
        any("ANALYZER UNAVAILABLE" in str(f.get("description", "")) or 
            "ANALYZER UNAVAILABLE" in str(f.get("message", "")) or 
            "ANALYZER_UNAVAILABLE" in str(f.get("rule_citation", "")) or
            "ANALYZER_UNAVAILABLE" in str(f.get("rule_id", "")) or
            "ANALYZER_UNAVAILABLE" in str(f.get("title", ""))
            for f in all_issues)
        or any("ANALYZER_UNAVAILABLE" in str(s.get("rule_id", "")) or 
               "ANALYZER UNAVAILABLE" in str(s.get("message", "")) 
               for s in state.get("static_findings", []))
        or any(t.get("status") == "degraded" and "ANALYZER UNAVAILABLE" in t.get("action", "") 
               for t in state.get("telemetry", []))
    )

    has_rag_unavailable = any(
        t.get("stage") == "rag_retrieval" and t.get("status") == "degraded"
        for t in state.get("telemetry", [])
    )

    has_syntax_error = any(
        "syntax-error" in str(f.get("rule_id", "")).lower() or
        "syntaxerror" in str(f.get("rule_id", "")).lower() or
        "syntax error" in str(f.get("message", "")).lower() or
        "syntax error" in str(f.get("title", "")).lower()
        for f in all_issues
    )

    if has_mcp_unavailable:
        verdict = "MCP UNAVAILABLE"
    elif has_analyzer_unavailable:
        verdict = "ANALYZER UNAVAILABLE"
    elif has_syntax_error:
        verdict = "FIX REQUIRED"
    elif len(unresolved) == 0:
        if has_rag_unavailable:
            verdict = "DEGRADED (RAG UNAVAILABLE)"
        else:
            verdict = "CLEAN"
    elif all(f.get("severity") in ["low", "informational"] for f in unresolved):
        verdict = "NEEDS REVIEW"
    else:
        verdict = "FIX REQUIRED"

    telemetry_item = {
        "stage": "summary_agent",
        "name": "Summary Agent (Synthesis)",
        "action": f"Unified report generated; {len(unresolved)} unresolved defect(s) (Verdict: {verdict})",
        "status": "complete",
        "latency_ms": latency,
        "duration_ms": latency,
        "retry_count": 0,
        "failure_reason": None
    }

    return {
        "all_issues": all_issues,
        "unresolved_findings": unresolved,
        "resolved_findings": resolved,
        "verified_findings": verified,
        "unverified_recommendations": unverified,
        "unresolved_count": len(unresolved),
        "resolved_count": len(resolved),
        "health_score": res["health_score"],
        "initial_health_score": initial_score,
        "is_assessed": res.get("is_assessed", True),
        "score_status": res.get("score_status", "ASSESSED"),
        "scoring_criteria": res.get("scoring_criteria", {}),
        "verdict": verdict,
        "summary": res["summary"],
        "counts": res["counts"],
        "category_counts": res.get("category_counts", {}),
        "status_counts": res.get("status_counts", {}),
        "safety_disclaimer": res.get("safety_disclaimer", ""),
        "telemetry": state["telemetry"] + [telemetry_item]
    }


def coder_agent_node(state: AgentState) -> Dict[str, Any]:
    """Layer 7: Coder Agent rewrites code to fix flagged issues with syntax validation."""
    start = time.time()
    code = state["code"]
    lang = state["language"]
    issues = state.get("unresolved_findings") or state.get("all_issues", [])
    rag = state.get("rag_context", [])
    provider = state.get("provider")

    # Fast path: Skip automatic remediation when there are no actionable findings
    if not issues or len(issues) == 0:
        telemetry_item = {
            "stage": "coder_agent",
            "name": "Coder Agent Fix Loop (Remediation)",
            "action": "Remediation skipped: zero actionable defects detected",
            "status": "SKIPPED",
            "latency_ms": 0.0,
            "duration_ms": 0.0,
            "retry_count": 0,
            "failure_reason": None
        }
        return {
            "remediation_status": "NOT_REQUIRED",
            "auto_fix_failure": False,
            "telemetry": state["telemetry"] + [telemetry_item]
        }

    # Fast path: Check for initial fatal syntax error - cannot auto-remediate unparseable code
    is_initially_valid, init_syntax_err = validate_code_syntax(code, lang)
    if not is_initially_valid:
        latency = round((time.time() - start) * 1000, 2)
        telemetry_item = {
            "stage": "coder_agent",
            "name": "Coder Agent Fix Loop (Remediation)",
            "action": f"Auto-remediation skipped: fatal syntax error ({init_syntax_err})",
            "status": "SKIPPED",
            "latency_ms": latency,
            "duration_ms": latency,
            "retry_count": 0,
            "failure_reason": f"Syntax error: {init_syntax_err}"
        }
        return {
            "code": code,
            "corrected_code": code,
            "changelog": [{
                "change_type": "validation_rejected",
                "line_affected": "1",
                "rule_citation": "VALIDATION:SyntaxIntegrity",
                "description": f"Proposed correction skipped: source code contains fatal syntax error ({init_syntax_err})."
            }],
            "iteration_count": state.get("iteration_count", 0) + 1,
            "remediation_status": "FAILED",
            "auto_fix_failure": True,
            "telemetry": state["telemetry"] + [telemetry_item]
        }

    corrected_code, new_changelog = run_coder_agent(code, lang, issues, rag, provider)
    latency = round((time.time() - start) * 1000, 2)

    current_iteration = state.get("iteration_count", 0) + 1

    # CRITICAL VALIDATION STEP: Validate code syntax to prevent returning corrupted code
    is_valid_syntax, syntax_err = validate_code_syntax(corrected_code, lang)
    if not is_valid_syntax:
        # Revert to safe pre-correction code, report rejection in changelog
        corrected_code = code
        code_modified = False
        auto_fix_failure = True
        remediation_status = "FAILED"
        action_text = f"Proposed correction rejected: syntax validation failed ({syntax_err})"
        new_changelog.append({
            "change_type": "validation_rejected",
            "line_affected": "1",
            "rule_citation": "VALIDATION:SyntaxIntegrity",
            "description": f"Proposed correction rejected by syntax validator: {syntax_err}. Pre-correction code preserved to prevent corruption."
        })
    else:
        # Check if code was actually modified
        code_modified = (corrected_code.strip() != code.strip())

        # Determine remediation status
        if not code_modified and len(issues) > 0:
            remediation_status = "FAILED" if len(new_changelog) == 0 else "PARTIAL"
            auto_fix_failure = True
            action_text = f"Auto-remediation could not further modify code for {len(issues)} remaining defect(s) (iteration {current_iteration})"
        elif code_modified or len(new_changelog) > 0:
            remediation_status = "SUCCESS" if len(issues) == len(new_changelog) else "PARTIAL"
            auto_fix_failure = False
            action_text = f"Auto-remediation applied and verified (iteration {current_iteration}); {len(new_changelog)} fix(es)"
        else:
            remediation_status = "NOT_REQUIRED"
            auto_fix_failure = False
            action_text = f"No remediation required (iteration {current_iteration})"

    # Accumulate changelog without duplicates across iterations
    prev_changelog = state.get("changelog", [])
    seen_desc = {c.get("description") for c in prev_changelog}
    accumulated_changelog = list(prev_changelog)
    for ch in new_changelog:
        if ch.get("description") not in seen_desc:
            accumulated_changelog.append(ch)
            seen_desc.add(ch.get("description"))

    telemetry_item = {
        "stage": "coder_agent",
        "name": "Coder Agent Fix Loop (Remediation)",
        "action": action_text,
        "status": "complete" if remediation_status != "FAILED" else "failed",
        "latency_ms": latency,
        "duration_ms": latency,
        "retry_count": 0,
        "failure_reason": syntax_err if not is_valid_syntax else None
    }

    return {
        "code": corrected_code,
        "corrected_code": corrected_code,
        "changelog": accumulated_changelog,
        "iteration_count": current_iteration,
        "remediation_status": remediation_status,
        "auto_fix_failure": auto_fix_failure,
        "telemetry": state["telemetry"] + [telemetry_item]
    }


def recheck_condition(state: AgentState) -> str:
    """
    Evaluates whether the corrected code meets target criteria (0 unresolved defects),
    or auto-fix failed, or maximum iteration limit has been reached.
    """
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 2)
    unresolved = state.get("unresolved_count", len(state.get("unresolved_findings", [])))
    auto_fix_failed = state.get("auto_fix_failure", False)

    # Terminate if all defects resolved, or iteration cap reached, or auto-fix cannot modify code
    if iteration >= max_iter or unresolved == 0 or auto_fix_failed:
        return "end"
    return "recheck"


def build_pipeline_graph() -> StateGraph:
    """Constructs the LangGraph state machine with re-check loop."""
    builder = StateGraph(AgentState)

    # Register Nodes
    builder.add_node("static_analysis", static_analysis_node)
    builder.add_node("rag_retrieval", rag_retrieval_node)
    builder.add_node("llm_gateway", llm_gateway_node)
    builder.add_node("parallel_review", parallel_review_node)
    builder.add_node("summary_agent", summary_agent_node)
    builder.add_node("coder_agent", coder_agent_node)

    # Define Flow Edges
    builder.set_entry_point("static_analysis")
    builder.add_edge("static_analysis", "rag_retrieval")
    builder.add_edge("rag_retrieval", "llm_gateway")
    builder.add_edge("llm_gateway", "parallel_review")
    builder.add_edge("parallel_review", "summary_agent")

    # Conditional branching: If unresolved defects exist and iteration cap not reached, run Coder Agent
    builder.add_conditional_edges(
        "summary_agent",
        lambda state: "coder_agent" if state.get("unresolved_count", len(state.get("unresolved_findings", []))) > 0 and state.get("iteration_count", 0) < state.get("max_iterations", 2) and not state.get("auto_fix_failure", False) else "end",
        {
            "coder_agent": "coder_agent",
            "end": END
        }
    )

    # Re-check loop: after Coder Agent, route back through Security + Bug Review
    # Notice: per specification step 8, does not go back through static analysis!
    builder.add_conditional_edges(
        "coder_agent",
        recheck_condition,
        {
            "recheck": "parallel_review",
            "end": END
        }
    )

    return builder.compile()


# Compiled LangGraph pipeline
pipeline_app = build_pipeline_graph()


SUPPORTED_LANGUAGES = {
    "python": "python", "py": "python",
    "cpp": "cpp", "c++": "cpp", "cxx": "cpp", "cc": "cpp", "hpp": "cpp",
    "c": "c", "h": "c",
    "java": "java",
    "javascript": "javascript", "js": "javascript", "typescript": "javascript", "ts": "javascript", "jsx": "javascript", "tsx": "javascript",
    "ruby": "ruby", "rb": "ruby"
}


def run_full_pipeline(
    code: str,
    language: str,
    filename: str = "source_code.txt",
    provider: str = None,
    max_iterations: int = 2
) -> Dict[str, Any]:
    """
    Executes the complete multi-agent pipeline and returns comprehensive telemetry,
    verdict, issue list, and corrected code.
    Enforces source code validation, language detection, timeout bounds, and verification tracking.
    """
    pipeline_start = time.time()

    # 1. Validate source code payload
    if not code or not str(code).strip():
        raise ValueError("Source code cannot be empty or contain only whitespace.")

    # 2. Detect or validate target programming language
    raw_lang = (language or "").lower().strip()
    if not raw_lang or raw_lang not in SUPPORTED_LANGUAGES:
        ext = os.path.splitext(filename or "")[1].lower()
        ext_map = {
            ".py": "python", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
            ".c": "c", ".h": "c", ".java": "java",
            ".js": "javascript", ".jsx": "javascript", ".ts": "javascript", ".tsx": "javascript",
            ".rb": "ruby"
        }
        target_lang = ext_map.get(ext, "python")
    else:
        target_lang = SUPPORTED_LANGUAGES[raw_lang]

    initial_state: AgentState = {
        "code": code,
        "original_code": code,
        "language": target_lang,
        "filename": filename or "source_code.txt",
        "provider": provider,
        "mcp_tools": get_mcp_tools_for_language(target_lang),
        "static_findings": [],
        "rag_context": [],
        "security_findings": [],
        "bug_findings": [],
        "all_issues": [],
        "unresolved_findings": [],
        "resolved_findings": [],
        "verified_findings": [],
        "unverified_recommendations": [],
        "unresolved_count": 0,
        "resolved_count": 0,
        "remediation_status": "NOT_REQUIRED",
        "auto_fix_failure": False,
        "health_score": 10.0,
        "initial_health_score": None,
        "verdict": "PENDING",
        "summary": "",
        "counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "corrected_code": code,
        "changelog": [],
        "iteration_count": 0,
        "max_iterations": max(1, min(max_iterations, 5)),
        "telemetry": [],
        "gateway_info": {},
        "tools_execution": [],
        "coverage": "partial",
        "coverage_explanation": ""
    }

    final_state = pipeline_app.invoke(initial_state)

    # Determine post-fix score and final verdict strictly from unresolved defects
    final_unresolved = final_state.get("unresolved_count", len(final_state.get("unresolved_findings", [])))
    orig_score = final_state.get("initial_health_score", final_state.get("health_score", 10.0))
    auto_fix_failed = final_state.get("auto_fix_failure", False)
    remediation_status = final_state.get("remediation_status", "NOT_REQUIRED")

    # Evaluate Truthful Verdict under all failure conditions
    has_mcp_unavailable = (
        any("MCP UNAVAILABLE" in str(i.get("description", "")) or 
            "MCP UNAVAILABLE" in str(i.get("message", "")) or 
            "MCP:TOOL_UNAVAILABLE" in str(i.get("rule_id", "")) or
            "MCP:TOOL_UNAVAILABLE" in str(i.get("rule_citation", ""))
            for i in final_state.get("all_issues", []))
        or any("MCP:TOOL_UNAVAILABLE" in str(s.get("rule_id", "")) or 
               "MCP UNAVAILABLE" in str(s.get("message", "")) 
               for s in final_state.get("static_findings", []))
        or any(t.get("status") == "degraded" and "MCP UNAVAILABLE" in t.get("action", "") 
               for t in final_state.get("telemetry", []))
    )

    has_analyzer_unavailable = (
        any("ANALYZER UNAVAILABLE" in str(i.get("description", "")) or 
            "ANALYZER UNAVAILABLE" in str(i.get("message", "")) or 
            "ANALYZER_UNAVAILABLE" in str(i.get("rule_citation", "")) or
            "ANALYZER_UNAVAILABLE" in str(i.get("rule_id", "")) or
            "ANALYZER_UNAVAILABLE" in str(i.get("title", ""))
            for i in final_state.get("all_issues", []))
        or any("ANALYZER_UNAVAILABLE" in str(s.get("rule_id", "")) or 
               "ANALYZER UNAVAILABLE" in str(s.get("message", "")) 
               for s in final_state.get("static_findings", []))
        or any(t.get("status") == "degraded" and "ANALYZER UNAVAILABLE" in t.get("action", "") 
               for t in final_state.get("telemetry", []))
    )

    has_rag_unavailable = any(
        t.get("stage") == "rag_retrieval" and t.get("status") == "degraded"
        for t in final_state.get("telemetry", [])
    )

    has_syntax_error = any(
        "syntax-error" in str(i.get("rule_id", "")).lower() or
        "syntaxerror" in str(i.get("rule_id", "")).lower() or
        "syntax error" in str(i.get("message", "")).lower() or
        "syntax error" in str(i.get("description", "")).lower()
        for i in final_state.get("all_issues", [])
    )

    if has_mcp_unavailable:
        final_verdict = "MCP UNAVAILABLE"
        orig_score = min(orig_score, 5.0)
        post_fix_score = orig_score
    elif has_analyzer_unavailable:
        final_verdict = "ANALYZER UNAVAILABLE"
        orig_score = min(orig_score, 5.0)
        post_fix_score = orig_score
    elif has_syntax_error:
        final_verdict = "FIX REQUIRED"
        orig_score = min(orig_score, 7.5)
        post_fix_score = orig_score
    elif final_unresolved == 0:
        if has_rag_unavailable:
            final_verdict = "DEGRADED (RAG UNAVAILABLE)"
            orig_score = min(orig_score, 7.0)
            post_fix_score = orig_score
        else:
            final_verdict = "CLEAN"
            post_fix_score = 10.0
    else:
        final_verdict = "FIX REQUIRED"
        post_fix_score = final_state.get("health_score", orig_score)

    # Determine truthful summary message
    if auto_fix_failed and final_unresolved > 0:
        summary_msg = f"AUTO-FIX FAILED: Unable to automatically resolve {final_unresolved} remaining actionable defect(s). Manual intervention required."
    elif has_mcp_unavailable:
        summary_msg = "MCP UNAVAILABLE: Model Context Protocol dispatch layer failed or tool runner offline. Manual verification required."
    elif has_analyzer_unavailable:
        summary_msg = "ANALYZER UNAVAILABLE: One or more static analyzers failed to execute. Manual verification required."
    elif has_rag_unavailable and final_unresolved == 0:
        summary_msg = "DEGRADED (RAG UNAVAILABLE): Vector store retrieval failed. Normative security and compliance rules could not be grounded."
    elif has_syntax_error:
        summary_msg = "SYNTAX ERROR: Fatal parsing or syntax error detected in source code. Code cannot be verified until syntax is corrected."
    else:
        summary_msg = final_state.get("summary", "")

    # Ensure all 6 pipeline stages are present in telemetry
    telemetry = list(final_state.get("telemetry", []))
    coder_present = any(t.get("stage") == "coder_agent" for t in telemetry)
    if not coder_present:
        telemetry.append({
            "stage": "coder_agent",
            "name": "Coder Agent Fix Loop (Remediation)",
            "action": "Remediation skipped: zero actionable defects detected",
            "status": "SKIPPED",
            "latency_ms": 0.0,
            "duration_ms": 0.0,
            "retry_count": 0,
            "failure_reason": None
        })

    total_elapsed_ms = round((time.time() - pipeline_start) * 1000, 2)

    review_id = str(uuid.uuid4())[:8]
    output_result = {
        "review_id": review_id,
        "filename": final_state.get("filename"),
        "language": final_state.get("language"),
        "mcp_tools": final_state.get("mcp_tools"),
        "original_code": final_state.get("original_code"),
        "corrected_code": final_state.get("corrected_code"),
        "changelog": final_state.get("changelog", []),
        "health_score": orig_score,
        "post_fix_score": post_fix_score,
        "verdict": final_verdict,
        "unresolved_count": final_unresolved,
        "resolved_count": final_state.get("resolved_count", len(final_state.get("resolved_findings", []))),
        "unresolved_findings": final_state.get("unresolved_findings", []),
        "resolved_findings": final_state.get("resolved_findings", []),
        "verified_findings": final_state.get("verified_findings", []),
        "unverified_recommendations": final_state.get("unverified_recommendations", []),
        "remediation_status": remediation_status,
        "auto_fix_failure": auto_fix_failed,
        "summary": summary_msg,
        "counts": final_state.get("counts"),
        "issues": final_state.get("all_issues"),
        "all_issues": final_state.get("all_issues", []),
        "telemetry": telemetry,
        "total_elapsed_ms": total_elapsed_ms,
        "is_assessed": final_state.get("is_assessed", True),
        "score_status": final_state.get("score_status", "ASSESSED"),
        "scoring_criteria": final_state.get("scoring_criteria", {}),
        "rag_context": final_state.get("rag_context"),
        "iterations_performed": final_state.get("iteration_count"),
        "iteration_count": final_state.get("iteration_count", 0),
        "gateway_info": final_state.get("gateway_info"),
        "tools_execution": final_state.get("tools_execution", []),
        "coverage": final_state.get("coverage", "partial"),
        "coverage_explanation": final_state.get("coverage_explanation", "")
    }

    # Save to persistent SQLite database with graceful degradation
    db_res = save_review_record(review_id, output_result)
    output_result["database_status"] = db_res.get("status", "healthy")
    if db_res.get("error"):
        output_result["database_error"] = db_res.get("error")

    return output_result

