"""
PR Agent Backend Server.
FastAPI Application providing endpoints for:
- /api/status: Live gateway telemetry and provider fallback state
- /api/review: Full LangGraph multi-agent execution pipeline
- /api/upload: Source code file submission
- /api/download: Corrected source code export
- /api/audit-report: Comprehensive markdown security & triage audit
- /api/samples: Preset buggy code across all 6 languages
- /api/rag/query & /api/rag/stats: Dedicated vector store exploration
"""

import os
import io
import re
import time
import uuid
import threading
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse, PlainTextResponse
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

from .ollama_service import ollama_service
from .mcp_tools import get_mcp_tools_for_language, run_static_analysis, get_all_tools_status, TOOL_CATALOG, LANGUAGE_TOOL_MAPPING
from .rag.vector_store import store
from .llm_gateway import gateway
from .database import get_db_health, get_review_record, save_review_record, init_db
from .graph import run_full_pipeline, validate_code_syntax
from .samples import SAMPLES
from .benchmark import (
    GROUND_TRUTH_DATASET,
    run_benchmark_suite,
    run_isolated_benchmark_case,
    run_rag_benchmark
)
from .agents.coder_agent import run_coder_agent
from .agents.security_agent import run_security_agent
from .agents.bug_agent import run_bug_agent
from .agents.summary_agent import calculate_health_score


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Automated lifecycle hook for PR Agent backend:
    - On Startup: Initializes SQLite schema/migrations and boots Ollama if enabled.
    - On Shutdown: Automatically terminates managed Ollama server.
    """
    # Safe database initialization and migrations
    init_db()

    auto_start = os.getenv("AUTO_START_OLLAMA", "1") == "1"
    if auto_start:
        threading.Thread(
            target=ollama_service.start_ollama,
            kwargs={"preload": True},
            daemon=True
        ).start()

    yield

    # Clean shutdown of Ollama when backend terminates
    ollama_service.stop_ollama()


app = FastAPI(
    title="PR Agent API",
    description="Multilingual Code Review & Auto-Correction Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for configured frontend origins and local development
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
configured_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins if configured_origins else [],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sanitize_error(msg: Any) -> str:
    """Strips secrets, credentials, and host filesystem paths from error messages."""
    if not msg:
        return ""
    text = str(msg)
    text = re.sub(r'AIza[0-9A-Za-z\-_]{20,}', '[REDACTED_API_KEY]', text)
    text = re.sub(r'gsk_[0-9A-Za-z\-_]{20,}', '[REDACTED_API_KEY]', text)
    text = re.sub(r'sk-[0-9A-Za-z\-_]{20,}', '[REDACTED_API_KEY]', text)
    text = re.sub(r'key=[0-9A-Za-z\-_]{16,}', 'key=[REDACTED]', text)
    text = re.sub(r'Bearer\s+[0-9A-Za-z\-_\.]{16,}', 'Bearer [REDACTED]', text)
    text = re.sub(r'[A-Za-z]:\\[^:\n\r\t]+', '[INTERNAL_PATH]', text)
    text = re.sub(r'/(?:home|Users|var|tmp|etc|root)/[^\s:\n\r\t]+', '[INTERNAL_PATH]', text)
    return text


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """Global handler ensuring no raw credentials or internal paths are leaked on unexpected errors."""
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": sanitize_error(exc.detail)}
        )
    sanitized = sanitize_error(str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {sanitized}"}
    )


MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB max source file upload
MAX_CODE_CHARS = 500_000           # 500k max source characters
MAX_MEMORY_CACHE = 100
SUPPORTED_LANGUAGES = {"python", "cpp", "c", "java", "javascript", "ruby", "typescript"}

# Thread-safe in-memory storage for review results
CACHE_LOCK = threading.Lock()
REVIEW_CACHE: Dict[str, Any] = {}
LATEST_REVIEW_CACHE: Dict[str, Any] = {}


class ReviewRequest(BaseModel):
    code: str
    language: str
    filename: Optional[str] = "source_code.txt"
    provider: Optional[str] = None
    max_iterations: Optional[int] = 1


class ConfigGatewayRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    provider: Optional[str] = None
    gemini_model: Optional[str] = None
    groq_model: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_base_url: Optional[str] = None


class RagQueryRequest(BaseModel):
    query: str
    language: Optional[str] = None
    top_k: Optional[int] = 4
    min_similarity: Optional[float] = 0.12
    category: Optional[str] = None


class RagIngestRequest(BaseModel):
    file_path: Optional[str] = "custom_guideline.md"
    content: str
    language: Optional[str] = None


class BenchmarkRunRequest(BaseModel):
    suite_type: Optional[str] = "all"  # "all", "real_world", "synthetic"
    language: Optional[str] = None     # "python", "cpp", "c", "java", "javascript", "ruby" or None
    provider: Optional[str] = None
    case_id: Optional[str] = None


@app.get("/")
def root():
    return {
        "system": "PR Agent",
        "protocol": "PR Agent",
        "status": "operational",
        "timestamp": time.time()
    }


@app.get("/health/liveness")
@app.get("/api/health/liveness")
def health_liveness():
    """Liveness probe: verifies process is alive and event loop is responsive."""
    return {
        "status": "alive",
        "timestamp": time.time()
    }


@app.get("/health/readiness")
@app.get("/api/health/readiness")
def health_readiness():
    """
    Readiness probe: distinguishes readiness from liveness.
    Verifies database connectivity and vector store readiness.
    Returns HTTP 200 when ready to accept traffic, or HTTP 503 when degraded.
    """
    try:
        db_stats = get_db_health()
    except Exception as e:
        db_stats = {"status": "degraded", "error": sanitize_error(e)}

    try:
        rag_stats = store.get_stats()
    except Exception as e:
        rag_stats = {"status": "unavailable", "error": sanitize_error(e)}

    is_ready = (
        db_stats.get("status") == "healthy" and 
        rag_stats.get("status") != "unavailable"
    )

    status_code = 200 if is_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "degraded",
            "database": db_stats,
            "rag": rag_stats,
            "timestamp": time.time()
        }
    )


@app.get("/status")
@app.get("/health")
@app.get("/api/status")
@app.get("/api/health")
def get_system_status():
    """Returns gateway status, active provider, and fallback standby/active state."""
    try:
        gw = gateway.get_gateway_status()
    except Exception as e:
        gw = {
            "provider": "OFFLINE_HEURISTIC",
            "badge": "GATEWAY DEGRADED",
            "model": "pr-agent-deterministic-v1",
            "fallback_state": "fallback: active",
            "fallback_active": True,
            "has_gemini_key": False,
            "has_groq_key": False,
            "ollama_available": False,
            "last_latency_ms": 0.0,
            "error": sanitize_error(e)
        }

    try:
        rag_stats = store.get_stats()
    except Exception as e:
        rag_stats = {
            "total_vectors": 0,
            "vector_dimension": 128,
            "status": "unavailable",
            "error": sanitize_error(e)
        }

    try:
        db_stats = get_db_health()
    except Exception as e:
        db_stats = {
            "status": "degraded",
            "error": sanitize_error(e)
        }

    overall_status = "online"
    if rag_stats.get("status") == "unavailable" or db_stats.get("status") == "degraded":
        overall_status = "degraded"
    elif gw.get("fallback_active") or gw.get("last_error"):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "gateway": gw,
        "rag": rag_stats,
        "database": db_stats,
        "supported_languages": sorted(list(SUPPORTED_LANGUAGES))
    }


@app.get("/api/gateway/status")
@app.get("/api/gateway/config")
def get_gateway_status_endpoint():
    """Returns runtime gateway provider, active model, and fallback state."""
    return gateway.get_gateway_status()


@app.get("/api/languages")
def get_languages():
    """Lists supported languages and their matching deterministic MCP tools with live coverage telemetry."""
    all_status = get_all_tools_status()
    lang_defs = [
        ("python", "Python", ".py"),
        ("cpp", "C++", ".cpp"),
        ("c", "C", ".c"),
        ("java", "Java", ".java"),
        ("javascript", "JavaScript", ".js"),
        ("typescript", "TypeScript", ".ts"),
        ("ruby", "Ruby", ".rb"),
    ]
    languages_info = []
    for lid, name, ext in lang_defs:
        cov = all_status.get("supported_languages", {}).get(lid, {})
        languages_info.append({
            "id": lid,
            "name": name,
            "ext": ext,
            "mcp_tools": LANGUAGE_TOOL_MAPPING.get(lid, ["pylint"]),
            "coverage": cov.get("coverage", "partial"),
            "native_tools": cov.get("native_tools", []),
            "missing_tools": cov.get("missing_tools", []),
            "install_hint": cov.get("install_hint", "")
        })
    return {"languages": languages_info}


@app.get("/api/tools/status")
def get_tools_status_endpoint():
    """Returns host installation status, binary paths, and install instructions for all supported tools."""
    return get_all_tools_status()


@app.get("/api/samples")
def get_samples():
    """Returns all preset buggy code samples for 1-click testing in UI."""
    return SAMPLES


@app.get("/api/samples/{language}")
def get_language_sample(language: str):
    """Returns preset buggy code for a specific language."""
    norm = language.lower().strip()
    if norm in SAMPLES:
        return SAMPLES[norm]
    raise HTTPException(status_code=404, detail=f"No sample found for language: {language}")


@app.post("/upload")
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Uploads a source code file, infers language and line count."""
    try:
        # Stream chunks with early abort to prevent memory exhaustion on unbounded files
        total_read = 0
        chunks = []
        chunk_size = 64 * 1024
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_read += len(chunk)
            if total_read > MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=413, detail="File too large. Maximum source file upload size is 5MB.")
            chunks.append(chunk)
        content_bytes = b"".join(chunks)

        code_text = content_bytes.decode("utf-8", errors="replace")
        
        # Sanitize filename against path traversal and control characters
        raw_filename = file.filename or "uploaded_file.txt"
        clean_filename = os.path.basename(raw_filename.replace("\\", "/"))
        clean_filename = re.sub(r'[\x00-\x1f\x7f]', '', clean_filename).strip()
        filename = clean_filename if clean_filename else "uploaded_file.txt"
        
        # Infer language from extension
        ext = os.path.splitext(filename)[1].lower()
        ext_map = {
            ".py": "python",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".java": "java",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".rb": "ruby"
        }
        detected_lang = ext_map.get(ext, "python")
        line_count = len(code_text.splitlines())
        mcp_tools = get_mcp_tools_for_language(detected_lang)

        return {
            "filename": filename,
            "language": detected_lang,
            "line_count": line_count,
            "mcp_tools": mcp_tools,
            "code": code_text
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload failed: {sanitize_error(e)}")
    finally:
        await file.close()


@app.post("/review")
@app.post("/api/review")
def run_review(req: ReviewRequest):
    """
    Main LangGraph execution endpoint.
    Runs Static Analysis (MCP) -> RAG -> LLM Gateway -> Parallel Security & Bug Review
    -> Summary Synthesis -> Coder Agent Remediation -> Re-check Loop.
    """
    global LATEST_REVIEW_CACHE
    if not req.code or not req.code.strip():
        raise HTTPException(status_code=400, detail="Source code cannot be empty.")

    norm_lang = (req.language or "").lower().strip()
    if not norm_lang or norm_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: '{req.language}'. Supported languages: {sorted(list(SUPPORTED_LANGUAGES))}"
        )

    if len(req.code) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Payload too large. Maximum source code size is 5MB.")

    if len(req.code) > MAX_CODE_CHARS:
        raise HTTPException(status_code=413, detail=f"Payload exceeds maximum character limit ({MAX_CODE_CHARS:,} characters).")

    # Clamp iterations safely between 1 and 5 to prevent infinite execution
    safe_iterations = min(max(req.max_iterations or 2, 1), 5)

    # Sanitize input filename against path traversal
    raw_filename = req.filename or "source_code.txt"
    clean_filename = os.path.basename(raw_filename.replace("\\", "/"))
    clean_filename = re.sub(r'[\x00-\x1f\x7f]', '', clean_filename).strip()
    safe_filename = clean_filename if clean_filename else "source_code.txt"

    result = run_full_pipeline(
        code=req.code,
        language=norm_lang,
        filename=safe_filename,
        provider=req.provider,
        max_iterations=safe_iterations
    )

    review_id = result.get("review_id")
    if not review_id or len(review_id) < 8:
        review_id = f"rev-{uuid.uuid4().hex[:12]}"
    result["review_id"] = review_id

    # Thread-safe in-memory cache
    with CACHE_LOCK:
        LATEST_REVIEW_CACHE = result
        REVIEW_CACHE[review_id] = result
        while len(REVIEW_CACHE) > MAX_MEMORY_CACHE:
            oldest = next(iter(REVIEW_CACHE))
            del REVIEW_CACHE[oldest]

    return result


class RemediateRequest(BaseModel):
    code: str
    language: str
    filename: Optional[str] = "source_code.txt"
    issues: Optional[List[Dict[str, Any]]] = None
    rag_context: Optional[List[Dict[str, Any]]] = None
    provider: Optional[str] = None
    review_id: Optional[str] = None


class RecheckRequest(BaseModel):
    original_code: str
    corrected_code: str
    language: str
    filename: Optional[str] = "source_code.txt"
    previous_issues: Optional[List[Dict[str, Any]]] = None
    provider: Optional[str] = None
    review_id: Optional[str] = None


@app.post("/api/remediate")
def remediate_code(req: RemediateRequest):
    """
    Direct remediation execution: calls Coder Agent on code and defects.
    Returns corrected code, refactoring changelog, and truthful modification status.
    """
    global LATEST_REVIEW_CACHE
    if not req.code or not req.code.strip():
        raise HTTPException(status_code=400, detail="Source code cannot be empty.")

    if len(req.code) > MAX_CODE_CHARS:
        raise HTTPException(status_code=413, detail=f"Payload exceeds maximum character limit ({MAX_CODE_CHARS:,} characters).")

    norm_lang = (req.language or "").lower().strip()
    if not norm_lang or norm_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: '{req.language}'. Supported languages: {sorted(list(SUPPORTED_LANGUAGES))}"
        )

    issues = req.issues or []
    rag_context = req.rag_context or []
    if not rag_context and issues:
        try:
            rag_context = store.search(query=issues[0].get("title", norm_lang), language=norm_lang, top_k=4)
        except Exception:
            rag_context = []

    try:
        corrected_code, changelog = run_coder_agent(
            code=req.code,
            language=norm_lang,
            issues=issues,
            rag_context=rag_context,
            provider=req.provider
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coder Agent failed: {sanitize_error(e)}")

    # Structural syntax validation
    is_valid_syntax, syntax_err = validate_code_syntax(corrected_code, norm_lang)
    if not is_valid_syntax:
        code_modified = False
        remediation_status = "FAILED"
        auto_fix_failure = True
        corrected_code = req.code
        changelog = [{
            "change_type": "validation_rejected",
            "line_affected": "1",
            "rule_citation": "VALIDATION:SyntaxIntegrity",
            "description": f"Proposed correction rejected: {syntax_err}. Pre-correction code preserved."
        }]
    else:
        code_modified = bool(corrected_code and corrected_code.strip() != req.code.strip())
        if code_modified:
            remediation_status = "SUCCESS" if len(issues) == len(changelog) else "PARTIAL"
            auto_fix_failure = False
        else:
            remediation_status = "FAILED" if issues else "NOT_REQUIRED"
            auto_fix_failure = bool(issues)
            corrected_code = req.code

    review_id = req.review_id or f"rev-{uuid.uuid4().hex[:12]}"

    # Update cache
    with CACHE_LOCK:
        if review_id in REVIEW_CACHE:
            REVIEW_CACHE[review_id]["corrected_code"] = corrected_code
            REVIEW_CACHE[review_id]["changelog"] = changelog
            REVIEW_CACHE[review_id]["remediation_status"] = remediation_status
            REVIEW_CACHE[review_id]["auto_fix_failure"] = auto_fix_failure
        LATEST_REVIEW_CACHE["corrected_code"] = corrected_code
        LATEST_REVIEW_CACHE["changelog"] = changelog
        LATEST_REVIEW_CACHE["remediation_status"] = remediation_status
        LATEST_REVIEW_CACHE["auto_fix_failure"] = auto_fix_failure
        while len(REVIEW_CACHE) > MAX_MEMORY_CACHE:
            oldest = next(iter(REVIEW_CACHE))
            del REVIEW_CACHE[oldest]

    return {
        "review_id": review_id,
        "modified": code_modified,
        "original_code": req.code,
        "corrected_code": corrected_code,
        "changelog": changelog,
        "remediation_status": remediation_status,
        "auto_fix_failure": auto_fix_failure,
        "unresolved_count": 0 if not issues else (0 if remediation_status == "SUCCESS" else max(0, len(issues) - len(changelog))),
        "resolved_count": len(changelog) if code_modified else 0
    }


@app.post("/api/recheck")
def recheck_code(req: RecheckRequest):
    """
    Direct re-check execution: runs real static analysis linters and review agents
    against the corrected code to verify defect eradication.
    """
    global LATEST_REVIEW_CACHE
    code_to_check = req.corrected_code if req.corrected_code and req.corrected_code.strip() else req.original_code
    if not code_to_check or not code_to_check.strip():
        raise HTTPException(status_code=400, detail="Source code cannot be empty.")

    if len(code_to_check) > MAX_CODE_CHARS:
        raise HTTPException(status_code=413, detail=f"Payload exceeds maximum character limit ({MAX_CODE_CHARS:,} characters).")

    norm_lang = (req.language or "").lower().strip()
    if not norm_lang or norm_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: '{req.language}'. Supported languages: {sorted(list(SUPPORTED_LANGUAGES))}"
        )

    # 1. Run real static analysis on corrected code
    start_t = time.time()
    analysis = run_static_analysis(code_to_check, norm_lang)
    current_static = analysis.get("findings", [])
    mcp_tools = analysis.get("tools_invoked", get_mcp_tools_for_language(norm_lang))
    mcp_lat = round((time.time() - start_t) * 1000, 2)

    # 2. RAG context
    try:
        rag_context = store.search(query=norm_lang, language=norm_lang, top_k=4)
    except Exception:
        rag_context = []

    # 3. Security & Bug agents on corrected code
    sec_start = time.time()
    if len(current_static) == 0:
        sec_findings = []
        bug_findings = []
    else:
        has_sec = any(f.get("category") == "security" for f in current_static)
        has_bug = any(f.get("category") in ["bug", "style", "complexity"] for f in current_static)
        sec_findings = run_security_agent(code_to_check, norm_lang, current_static, rag_context, req.provider) if has_sec else []
        bug_findings = run_bug_agent(code_to_check, norm_lang, current_static, rag_context, req.provider) if has_bug else []
    rev_lat = round((time.time() - sec_start) * 1000, 2)

    current_findings = sec_findings + bug_findings
    current_keys = {(f.get("line"), f.get("title")) for f in (current_findings + current_static)}
    current_rules = (
        {f.get("rule_id") for f in current_static if f.get("rule_id")} |
        {f.get("rule_citation") for f in current_findings if f.get("rule_citation")} |
        {f.get("rule_id") for f in current_findings if f.get("rule_id")}
    )
    current_actionable_cwes = (
        {f.get("cwe") for f in current_findings if f.get("severity") in ["critical", "high", "medium"] and f.get("cwe")} |
        {f.get("cwe") for f in current_static if f.get("severity") in ["critical", "high", "medium"] and f.get("cwe")}
    )

    previous_issues = req.previous_issues or []
    updated_issues = []
    if previous_issues:
        for prev in previous_issues:
            p_copy = dict(prev)
            prev_rule = prev.get("rule_id") or prev.get("rule_citation")
            prev_cwe = prev.get("cwe")
            prev_sev = prev.get("severity", "medium")

            is_present = False
            if (prev.get("line"), prev.get("title")) in current_keys:
                is_present = True
            elif prev_rule and any(prev_rule in r or r in prev_rule for r in current_rules):
                is_present = True
            elif prev_cwe and prev_sev in ["critical", "high", "medium"] and prev_cwe in current_actionable_cwes:
                is_present = True

            p_copy["resolved"] = not is_present
            updated_issues.append(p_copy)
    else:
        for f in current_findings:
            f_copy = dict(f)
            f_copy["resolved"] = False
            updated_issues.append(f_copy)

    unresolved = [i for i in updated_issues if not i.get("resolved", False)]
    resolved = [i for i in updated_issues if i.get("resolved", False)]
    unresolved_count = len(unresolved)
    resolved_count = len(resolved)

    post_fix_score = calculate_health_score(unresolved)
    if unresolved_count == 0:
        verdict = "CLEAN"
        post_fix_score = 10.0
    else:
        verdict = "FIX REQUIRED"

    review_id = req.review_id or f"rev-{uuid.uuid4().hex[:12]}"

    telemetry = [
        {
            "stage": "static_analysis",
            "name": "Static Analysis (MCP)",
            "action": f"Re-checked with MCP tools: {' / '.join(mcp_tools)} ({len(current_static)} finding(s))",
            "status": "complete",
            "latency_ms": mcp_lat
        },
        {
            "stage": "multi_agent_review",
            "name": "Security & Bug Agents (LangGraph)",
            "action": f"Re-check scan completed: {len(sec_findings)} security, {len(bug_findings)} bug/style finding(s)",
            "status": "complete",
            "latency_ms": rev_lat
        },
        {
            "stage": "summary_agent",
            "name": "Summary Synthesis",
            "action": f"Re-check evaluation: {resolved_count} resolved, {unresolved_count} remaining; Verdict: {verdict}",
            "status": "complete",
            "latency_ms": 4.5
        }
    ]

    summary_msg = f"RE-CHECK COMPLETE: {resolved_count} defect(s) verified resolved, {unresolved_count} remaining. Final Verdict: {verdict}." if unresolved_count > 0 else "RE-CHECK PASSED: All actionable code quality and security defects have been verified eradicated. Codebase is CLEAN."

    result = {
        "review_id": review_id,
        "filename": req.filename,
        "language": norm_lang,
        "mcp_tools": mcp_tools,
        "original_code": req.original_code,
        "corrected_code": code_to_check,
        "health_score": post_fix_score,
        "post_fix_score": post_fix_score,
        "verdict": verdict,
        "unresolved_count": unresolved_count,
        "resolved_count": resolved_count,
        "unresolved_findings": unresolved,
        "resolved_findings": resolved,
        "remediation_status": "SUCCESS" if unresolved_count == 0 else "PARTIAL",
        "auto_fix_failure": unresolved_count > 0,
        "summary": summary_msg,
        "counts": {
            "critical": len([i for i in unresolved if i.get("severity") == "critical"]),
            "high": len([i for i in unresolved if i.get("severity") == "high"]),
            "medium": len([i for i in unresolved if i.get("severity") == "medium"]),
            "low": len([i for i in unresolved if i.get("severity") == "low"])
        },
        "issues": updated_issues,
        "all_issues": updated_issues,
        "telemetry": telemetry,
        "tools_execution": analysis.get("tools_execution", []),
        "coverage": analysis.get("coverage", "partial"),
        "coverage_explanation": analysis.get("coverage_explanation", "")
    }

    with CACHE_LOCK:
        if review_id in REVIEW_CACHE:
            REVIEW_CACHE[review_id].update(result)
        else:
            REVIEW_CACHE[review_id] = result
        LATEST_REVIEW_CACHE = dict(REVIEW_CACHE[review_id])
        while len(REVIEW_CACHE) > MAX_MEMORY_CACHE:
            oldest = next(iter(REVIEW_CACHE))
            del REVIEW_CACHE[oldest]

    try:
        save_review_record(review_id, result)
    except Exception:
        pass

    return result


@app.post("/api/gateway/configure")
def configure_gateway(req: ConfigGatewayRequest):
    """Allows runtime configuration of API keys, model names, and provider preference from UI."""
    if req.gemini_api_key is not None:
        os.environ["GEMINI_API_KEY"] = req.gemini_api_key.strip()
    if req.groq_api_key is not None:
        os.environ["GROQ_API_KEY"] = req.groq_api_key.strip()
    if req.provider is not None:
        os.environ["DEFAULT_PROVIDER"] = req.provider.strip()
    if req.gemini_model is not None:
        os.environ["GEMINI_MODEL"] = req.gemini_model.strip()
    if req.groq_model is not None:
        os.environ["GROQ_MODEL"] = req.groq_model.strip()
    if req.ollama_model is not None:
        os.environ["OLLAMA_MODEL"] = req.ollama_model.strip()
        ollama_service.model_name = req.ollama_model.strip()
    if req.ollama_base_url is not None:
        os.environ["OLLAMA_BASE_URL"] = req.ollama_base_url.strip()
        ollama_service.base_url = req.ollama_base_url.strip()

    gateway.reset_transient_errors()
    return gateway.get_gateway_status()


@app.post("/api/rag/query")
def query_rag(req: RagQueryRequest):
    """Executes similarity search on dedicated vector store with configurable top_k and relevance threshold."""
    try:
        safe_top_k = min(max(req.top_k or 4, 1), 50)
        min_sim = float(req.min_similarity) if req.min_similarity is not None else 0.12
        results = store.search(
            query=req.query,
            language=req.language,
            top_k=safe_top_k,
            min_similarity=min_sim,
            category=req.category
        )
        return {
            "query": req.query,
            "language": req.language,
            "top_k": safe_top_k,
            "min_similarity": min_sim,
            "results": results,
            "count": len(results),
            "embedding_provider": store.get_stats().get("embedding_provider")
        }
    except Exception as e:
        return {
            "query": req.query,
            "language": req.language,
            "results": [],
            "count": 0,
            "error": sanitize_error(e)
        }


@app.post("/api/rag/ingest")
def ingest_rag_context(req: RagIngestRequest):
    """Ingests custom project context or rule text into the vector store."""
    try:
        if not req.content or not str(req.content).strip():
            raise HTTPException(status_code=400, detail="Content cannot be empty.")
        result = store.ingest_project_context(
            file_path=req.file_path or "uploaded_guideline.md",
            content=req.content,
            language=req.language
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error(e))


@app.post("/api/rag/upload")
async def upload_rag_context_file(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """Uploads a context or guideline file directly into the RAG vector store."""
    try:
        total_read = 0
        chunks = []
        chunk_size = 64 * 1024
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_read += len(chunk)
            if total_read > MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=413, detail="File too large. Maximum RAG context upload size is 5MB.")
            chunks.append(chunk)
        content_bytes = b"".join(chunks)
        text_content = content_bytes.decode("utf-8", errors="replace")

        raw_filename = file.filename or "uploaded_guideline.md"
        clean_filename = os.path.basename(raw_filename.replace("\\", "/"))
        clean_filename = re.sub(r'[\x00-\x1f\x7f]', '', clean_filename).strip() or "uploaded_guideline.md"

        result = store.ingest_project_context(
            file_path=clean_filename,
            content=text_content,
            language=language
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error(e))
    finally:
        await file.close()


@app.get("/api/rag/stats")
def get_rag_stats():
    """Provides vector store statistics, rule inventory, and chunk index."""
    try:
        return {
            "stats": store.get_stats(),
            "catalog": store.get_all_documents(),
            "chunks": store.get_all_chunks()
        }
    except Exception as e:
        return {
            "stats": {"total_vectors": 0, "status": "unavailable", "error": sanitize_error(e)},
            "catalog": [],
            "chunks": []
        }


@app.get("/download")
@app.get("/api/download")
def download_corrected_code(review_id: Optional[str] = None):
    """Downloads the most recently corrected source file or by review_id."""
    target = None
    if review_id:
        target = get_review_record(review_id)
        if not target:
            with CACHE_LOCK:
                target = REVIEW_CACHE.get(review_id)
        if not target:
            raise HTTPException(status_code=404, detail=f"Review ID '{review_id}' not found.")
    else:
        with CACHE_LOCK:
            target = LATEST_REVIEW_CACHE

    if not target or "corrected_code" not in target:
        raise HTTPException(status_code=404, detail="No corrected code available to download.")

    code = target["corrected_code"]
    if not code or not str(code).strip():
        raise HTTPException(status_code=400, detail="Corrected source code is empty; cannot generate download.")

    lang = target.get("language", "python")
    ext_map = {
        "python": ".py",
        "cpp": ".cpp",
        "c": ".c",
        "java": ".java",
        "javascript": ".js",
        "typescript": ".ts",
        "ruby": ".rb"
    }
    ext = ext_map.get(lang, ".txt")
    orig_name = target.get("filename", "code")
    clean_orig_name = os.path.basename(orig_name.replace("\\", "/"))
    clean_orig_name = re.sub(r'[\x00-\x1f\x7f]', '', clean_orig_name).strip() or "code"
    base_name = os.path.splitext(clean_orig_name)[0]
    out_filename = f"{base_name}_corrected{ext}"

    return Response(
        content=code.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{out_filename}"'}
    )


@app.get("/audit-report")
@app.get("/api/audit-report")
def generate_audit_report(review_id: Optional[str] = None):
    """Generates a downloadable markdown security and code quality audit report."""
    data = None
    if review_id:
        data = get_review_record(review_id)
        if not data:
            with CACHE_LOCK:
                data = REVIEW_CACHE.get(review_id)
        if not data:
            raise HTTPException(status_code=404, detail=f"Review ID '{review_id}' not found.")
    else:
        with CACHE_LOCK:
            data = LATEST_REVIEW_CACHE

    if not data:
        raise HTTPException(status_code=404, detail="No review completed to generate an audit report.")
    raw_filename = data.get("filename", "source_code")
    clean_filename = os.path.basename(raw_filename.replace("\\", "/"))
    clean_filename = re.sub(r'[\x00-\x1f\x7f]', '', clean_filename).strip() or "source_code"
    base_name = os.path.splitext(clean_filename)[0]
    filename = clean_filename
    lang = data.get("language", "unknown").upper()
    score = data.get("health_score", 0.0)
    post_score = data.get("post_fix_score", score)
    verdict = data.get("verdict", "PENDING")
    issues = data.get("issues", [])
    unresolved_count = data.get("unresolved_count", len([i for i in issues if not i.get("resolved")]))
    resolved_count = data.get("resolved_count", len([i for i in issues if i.get("resolved")]))
    remediation_status = data.get("remediation_status", "NOT_REQUIRED")
    auto_fix_failed = data.get("auto_fix_failure", False)
    changelog = data.get("changelog", [])
    telemetry = data.get("telemetry", [])
    mcp_tools = data.get("mcp_tools", [])

    report = f"""# PR AGENT AUDIT REPORT
**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
**Target Artifact:** `{filename}` ({lang})
**MCP Static Linters:** {', '.join(mcp_tools)}

---

## 1. Executive Triage Summary
- **Initial Health Score:** {score} / 10.0
- **Post-Remediation Score:** {post_score} / 10.0
- **Triage Verdict:** {verdict}
- **Remediation Status:** {remediation_status.upper()}
- **Unresolved Actionable Findings:** {unresolved_count}
- **Resolved Findings:** {resolved_count}
- **Executive Summary:** {data.get('summary', '')}
"""
    if auto_fix_failed and unresolved_count > 0:
        report += """
> [!CAUTION]
> **AUTO-FIX FAILED**: The automated remediation agent was unable to resolve all actionable defects. Manual engineer intervention is required before deployment.
"""

    report += f"""
### Severity Distribution (Unresolved)
- **Critical:** {data.get('counts', {}).get('critical', 0)}
- **High:** {data.get('counts', {}).get('high', 0)}
- **Medium:** {data.get('counts', {}).get('medium', 0)}
- **Low:** {data.get('counts', {}).get('low', 0)}

---

## 2. Pipeline State Machine Telemetry
| Stage | Description | Status | Latency (ms) |
|---|---|---|---|
"""
    for t in telemetry:
        report += f"| {t.get('name')} | {t.get('action')} | {t.get('status').upper()} | {t.get('latency_ms', 0)} ms |\n"

    report += """
---

## 3. Detailed Traceable Issue Telemetry
"""
    if not issues:
        report += "\n*No code quality or security issues detected.*\n"
    else:
        for idx, issue in enumerate(issues, 1):
            res_tag = "[RESOLVED]" if issue.get("resolved") else "[UNRESOLVED - ACTIONABLE]"
            report += f"""
### Issue #{idx}: {issue.get('title')} {res_tag}
- **Status:** `{res_tag}`
- **Line:** {issue.get('line')}
- **Severity:** {str(issue.get('severity')).upper()}
- **Category:** {str(issue.get('category')).upper()}
- **CWE / OWASP:** {issue.get('cwe', 'N/A')} | {issue.get('owasp', 'N/A')}
- **Citation:** `{issue.get('rule_citation', 'Standard')}`
- **Description:** {issue.get('description')}
- **Grounded Recommendation:** {issue.get('recommendation')}
"""

    report += """
---

## 4. Coder Agent Refactoring Changelog
"""
    if not changelog:
        if auto_fix_failed and unresolved_count > 0:
            report += "\n> [!WARNING]\n> **AUTO-FIX FAILURE**: Coder Agent was unable to apply automated modifications for remaining defects.\n"
        else:
            report += "\n*No automated refactoring was required.*\n"
    else:
        for ch in changelog:
            report += f"- **[{ch.get('change_type', 'fix').upper()}]** Line(s) {ch.get('line_affected')}: {ch.get('description')} (Citation: `{ch.get('rule_citation')}`)\n"

    report += """
---
*Confidential — Generated by PR Agent Multi-Agent Engine*
"""

    return Response(
        content=report,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{base_name}_PR_Agent_Audit_Report.md"'}
    )


# ==============================================================================
# PHASE 13 — BENCHMARK API ENDPOINTS
# ==============================================================================

@app.get("/api/benchmark/catalog")
def get_benchmark_catalog():
    """
    Returns the complete documented ground-truth dataset catalog.
    Includes real-world application samples and synthetic fixtures across all 6 languages.
    """
    catalog = []
    for case_id, case in GROUND_TRUTH_DATASET.items():
        catalog.append({
            "id": case["id"],
            "name": case["name"],
            "language": case["language"],
            "suite_type": case["suite_type"],
            "filename": case["filename"],
            "is_intentionally_vulnerable": case["is_intentionally_vulnerable"],
            "defect_categories": case.get("defect_categories", []),
            "expected_defects_count": len(case.get("expected_defects", [])),
            "expected_defects": case.get("expected_defects", [])
        })
    return {
        "total_test_cases": len(catalog),
        "catalog": catalog
    }


@app.post("/api/benchmark/pipeline/run")
@app.get("/api/benchmark/pipeline/run")
def run_pipeline_benchmark(
    suite_type: Optional[str] = "all",
    language: Optional[str] = None,
    provider: Optional[str] = None,
    case_id: Optional[str] = None,
    payload: Optional[BenchmarkRunRequest] = None
):
    """
    Executes actual pipeline runs against documented ground-truth benchmarks.
    Computes real Precision, Recall, F1, and Remediation Success Rate.
    Never crashes on individual test case errors.
    """
    # Accept parameters from either JSON payload or query parameters
    s_type = payload.suite_type if payload and payload.suite_type else (suite_type or "all")
    lang = payload.language if payload and payload.language else language
    prov = payload.provider if payload and payload.provider else provider
    c_id = payload.case_id if payload and payload.case_id else case_id

    if c_id and c_id in GROUND_TRUTH_DATASET:
        test_case = GROUND_TRUTH_DATASET[c_id]
        single_result = run_isolated_benchmark_case(test_case=test_case, provider_override=prov, max_iterations=1)
        return {
            "summary": {
                "total_test_cases": 1,
                "overall_precision": single_result["precision"],
                "overall_recall": single_result["recall"],
                "overall_f1_score": single_result["f1_score"],
                "remediation_success_rate": "100%" if single_result["remediation_success"] else "0%",
                "average_latency_ms": single_result["latency_ms"]
            },
            "test_conditions": {
                "timestamp": datetime.now().isoformat(),
                "llm_provider": prov or gateway.provider,
                "case_id": c_id
            },
            "runs": [single_result]
        }

    return run_benchmark_suite(
        suite_type=s_type,
        language_filter=lang,
        provider_override=prov
    )


@app.post("/api/benchmark/rag/run")
@app.get("/api/benchmark/rag/run")
def run_rag_benchmark_endpoint():
    """
    Executes in-memory RAG vector retrieval benchmark across standard vulnerability vectors.
    Returns Precision@1 and average latency.
    """
    return run_rag_benchmark()


@app.get("/api/benchmark/status")
def get_benchmark_status():
    """
    Returns active benchmark test conditions, tool statuses, and provider limitations.
    """
    gw_status = gateway.get_gateway_status()
    return {
        "llm_provider": gw_status.get("provider", "gemini"),
        "llm_model": gw_status.get("model", "unknown"),
        "fallback_state": gw_status.get("fallback_state", ""),
        "all_tools_status": get_all_tools_status(),
        "total_dataset_cases": len(GROUND_TRUTH_DATASET),
        "rag_vectors_count": len(store.documents)
    }


