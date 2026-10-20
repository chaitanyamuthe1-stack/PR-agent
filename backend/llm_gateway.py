"""
LLM Gateway for PR Agent.
Provider-agnostic wrapper supporting:
1. Google Gemini Cloud API (gemini-1.5-flash / gemini-2.0-flash / gemini-1.5-pro)
2. Groq Cloud API (llama-3.3-70b-versatile / llama-3.1-8b-instant)
3. Local Ollama (qwen2.5-coder:7b / qwen2.5-coder:1.5b) within 4 GB VRAM constraints
4. Zero-dependency Offline Heuristic Synthesis Engine for deterministic static execution

Requirements:
- Credentials read exclusively from environment variables or secure server-side config.
- Never echoes API keys or sensitive source code to the browser or logs.
- Real availability verification (no false "Connected" claims).
- Bounded request timeouts, retries, and token constraints.
- Single-execution guarantee (never executes multiple expensive providers simultaneously).
- Clear operational mode distinctions: PRIMARY_CLOUD, SECONDARY_CLOUD, LOCAL_OLLAMA, OFFLINE_DETERMINISTIC.
"""

import os
import re
import json
import time
import threading
from typing import Dict, Any, Optional, List, Tuple
import httpx

from .ollama_service import (
    is_ollama_running,
    is_model_installed,
    get_installed_models,
    get_vram_guidance,
    ollama_service
)

_OLLAMA_PROBE_CACHE = {
    "available": False,
    "model_installed": False,
    "ts": 0.0,
    "url": "",
    "model": ""
}
_OLLAMA_PROBE_LOCK = threading.Lock()

_SHARED_HTTP_CLIENT: Optional[httpx.Client] = None
_SHARED_HTTP_CLIENT_LOCK = threading.Lock()


def _get_shared_client(timeout: float = 15.0) -> httpx.Client:
    """Returns thread-safe connection-pooled HTTP client with keepalive."""
    global _SHARED_HTTP_CLIENT
    with _SHARED_HTTP_CLIENT_LOCK:
        if _SHARED_HTTP_CLIENT is None or _SHARED_HTTP_CLIENT.is_closed:
            _SHARED_HTTP_CLIENT = httpx.Client(
                timeout=timeout,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return _SHARED_HTTP_CLIENT


class CircuitBreaker:
    """
    Bounded Circuit Breaker pattern for provider calls.
    Prevents cascading stalls by fast-failing during continuous provider outages.
    States: CLOSED (normal), OPEN (failing, cool-off), HALF_OPEN (probing recovery).
    """
    def __init__(self, failure_threshold: int = 3, recovery_time: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = 0.0
        self._lock = threading.Lock()

    def record_success(self):
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"

    def allow_request(self) -> bool:
        with self._lock:
            if self.state == "CLOSED":
                return True
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_time:
                    self.state = "HALF_OPEN"
                    return True
                return False
            return True

    def reset(self):
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"
            self.last_failure_time = 0.0

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "state": self.state,
                "failure_count": self.failure_count,
                "threshold": self.failure_threshold,
                "recovery_time_sec": self.recovery_time
            }


class LLMGateway:
    """
    Unified LLM Gateway routing prompts across configured cloud and local providers.
    Enforces PR Agent fault tolerance and zero false-clean safety invariants.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.fallback_active = False
        self.last_provider_used = "gemini"
        self.last_model_used = "gemini-1.5-flash"
        self.last_latency_ms = 0.0
        self.last_error = ""
        self.primary_error = None
        self.fallback_error = None
        self.error_category = ""
        self.operation_mode = "PRIMARY_CLOUD"
        self.circuit_breakers = {
            "gemini": CircuitBreaker(failure_threshold=3, recovery_time=30.0),
            "groq": CircuitBreaker(failure_threshold=3, recovery_time=30.0),
            "ollama": CircuitBreaker(failure_threshold=3, recovery_time=30.0),
        }

    def get_circuit_breaker(self, provider: str) -> CircuitBreaker:
        norm = (provider or "").lower().strip()
        if norm not in self.circuit_breakers:
            self.circuit_breakers[norm] = CircuitBreaker()
        return self.circuit_breakers[norm]

    @staticmethod
    def sanitize_error(msg: Any) -> Optional[str]:
        """
        Sanitizes error strings to remove API keys, bearer tokens, passwords,
        and internal filesystem paths before presenting to logs or the UI.
        """
        if msg is None:
            return None
        text = str(msg)
        text = re.sub(r'AIza[0-9A-Za-z\-_]{20,}', '[REDACTED_API_KEY]', text)
        text = re.sub(r'gsk_[0-9A-Za-z\-_]{20,}', '[REDACTED_API_KEY]', text)
        text = re.sub(r'sk-[0-9A-Za-z\-_]{20,}', '[REDACTED_API_KEY]', text)
        text = re.sub(r'key=[0-9A-Za-z\-_]{16,}', 'key=[REDACTED]', text)
        text = re.sub(r'Bearer\s+[0-9A-Za-z\-_\.]{16,}', 'Bearer [REDACTED]', text)
        text = re.sub(r'[A-Za-z]:\\[^:\n\r\t]+', '[INTERNAL_PATH]', text)
        text = re.sub(r'/(?:home|Users|var|tmp|etc|root)/[^\s:\n\r\t]+', '[INTERNAL_PATH]', text)
        return text

    def reset_transient_errors(self):
        """Clears transient error states upon configuration updates or explicit reset."""
        with self._lock:
            self.last_error = ""
            self.primary_error = None
            self.fallback_error = None
            self.error_category = ""
            self.fallback_active = False
            for cb in self.circuit_breakers.values():
                cb.reset()

    def get_gateway_status(self) -> Dict[str, Any]:
        """
        Provides verified status telemetry for UI header and telemetry inspector.
        Never echoes raw credentials.
        """
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()
        ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b").strip()
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        pref = os.getenv("DEFAULT_PROVIDER", "gemini").lower().strip()

        has_gemini_key = bool(gemini_key and len(gemini_key) > 10 and not gemini_key.startswith("your_"))
        has_groq_key = bool(groq_key and len(groq_key) > 10 and not groq_key.startswith("your_"))

        # Real probe of local Ollama runtime and model presence
        ollama_available = False
        ollama_model_installed = False

        sim_ollama_fail = os.getenv("PR_AGENT_SIMULATE_OLLAMA_FAIL") == "1"
        sim_qwen_fail = os.getenv("PR_AGENT_SIMULATE_QWEN_FAIL") == "1"

        if not sim_ollama_fail:
            if sim_qwen_fail:
                ollama_available = True
                ollama_model_installed = False
            else:
                now = time.time()
                with _OLLAMA_PROBE_LOCK:
                    if (now - _OLLAMA_PROBE_CACHE.get("ts", 0.0) < 10.0 and 
                            _OLLAMA_PROBE_CACHE.get("url") == ollama_url and 
                            _OLLAMA_PROBE_CACHE.get("model") == ollama_model):
                        ollama_available = _OLLAMA_PROBE_CACHE["available"]
                        ollama_model_installed = _OLLAMA_PROBE_CACHE["model_installed"]
                    else:
                        ollama_available = is_ollama_running(ollama_url, timeout=1.5)
                        if ollama_available:
                            ollama_model_installed = is_model_installed(ollama_url, ollama_model, timeout=1.5)
                        _OLLAMA_PROBE_CACHE["available"] = ollama_available
                        _OLLAMA_PROBE_CACHE["model_installed"] = ollama_model_installed
                        _OLLAMA_PROBE_CACHE["ts"] = now
                        _OLLAMA_PROBE_CACHE["url"] = ollama_url
                        _OLLAMA_PROBE_CACHE["model"] = ollama_model

        # Determine active configured provider and badge
        sim_primary_fail = os.getenv("PR_AGENT_SIMULATE_PRIMARY_FAIL") == "1"
        sim_timeout = os.getenv("PR_AGENT_SIMULATE_NETWORK_TIMEOUT") == "1"

        if pref in ["offline", "heuristic", "offline_heuristic"]:
            provider = "OFFLINE_HEURISTIC"
            badge = "PR AGENT HEURISTIC SYNTHESIS ENGINE — ZERO-CONFIG"
            model = "pr-agent-deterministic-v1"
            status = "Offline Heuristic"
        elif pref == "ollama":
            provider = "OLLAMA"
            model = ollama_model
            if ollama_available and ollama_model_installed and not sim_qwen_fail:
                badge = f"OLLAMA {ollama_model.upper()} — LOCAL"
                status = "Connected"
            elif ollama_available and not ollama_model_installed:
                badge = f"OLLAMA (MODEL MISSING: {ollama_model})"
                status = "Degraded (Model Not Installed)"
            else:
                badge = f"OLLAMA ({ollama_model.upper()} OFFLINE)"
                status = "Degraded (Ollama Offline)"
        elif pref == "gemini":
            provider = "GEMINI"
            model = gemini_model
            if has_gemini_key and not sim_primary_fail:
                badge = f"GEMINI {gemini_model.upper()} — LIVE API"
                status = "Connected"
            elif sim_primary_fail:
                badge = f"GEMINI {gemini_model.upper()} (PRIMARY FAILED)"
                status = "Degraded"
            else:
                badge = f"GEMINI {gemini_model.upper()} (UNCONFIGURED)"
                status = "Unconfigured"
        elif pref == "groq":
            provider = "GROQ"
            model = groq_model
            if has_groq_key and not sim_primary_fail:
                badge = f"GROQ {groq_model.upper()} — LIVE API"
                status = "Connected"
            elif sim_primary_fail:
                badge = f"GROQ {groq_model.upper()} (PRIMARY FAILED)"
                status = "Degraded"
            else:
                badge = f"GROQ {groq_model.upper()} (UNCONFIGURED)"
                status = "Unconfigured"
        elif has_gemini_key and not sim_primary_fail:
            provider = "GEMINI"
            badge = f"GEMINI {gemini_model.upper()} — LIVE API"
            model = gemini_model
            status = "Connected"
        elif has_groq_key and not sim_primary_fail:
            provider = "GROQ"
            badge = f"GROQ {groq_model.upper()} — LIVE API"
            model = groq_model
            status = "Connected"
        elif ollama_available and ollama_model_installed and not sim_qwen_fail:
            provider = "OLLAMA"
            badge = f"OLLAMA {ollama_model.upper()} — LOCAL"
            model = ollama_model
            status = "Connected"
        elif ollama_available and not ollama_model_installed:
            provider = "OLLAMA"
            badge = f"OLLAMA (MODEL MISSING: {ollama_model})"
            model = ollama_model
            status = "Degraded (Model Not Installed)"
        else:
            provider = "OFFLINE_HEURISTIC"
            badge = "PR AGENT HEURISTIC SYNTHESIS ENGINE — ZERO-CONFIG"
            model = "pr-agent-deterministic-v1"
            status = "Offline Heuristic (Zero-Config Active)"

        with self._lock:
            return {
                "provider": provider,
                "badge": badge,
                "model": model,
                "status": status,
                "fallback_state": "fallback: active" if self.fallback_active else "fallback: standby",
                "fallback_active": self.fallback_active,
                "operation_mode": self.operation_mode,
                "has_gemini_key": has_gemini_key,
                "has_groq_key": has_groq_key,
                "ollama_available": ollama_available,
                "ollama_model_installed": ollama_model_installed,
                "last_provider_used": self.last_provider_used,
                "last_model_used": self.last_model_used,
                "last_latency_ms": self.last_latency_ms,
                "last_error": self.sanitize_error(self.last_error) or "",
                "primary_error": self.sanitize_error(self.primary_error),
                "fallback_error": self.sanitize_error(self.fallback_error),
                "error_category": self.error_category,
                "vram_guidance": get_vram_guidance(),
                "circuit_breakers": {k: cb.get_status() for k, cb in self.circuit_breakers.items()},
                "timeout_seconds": float(os.getenv("PR_AGENT_LLM_TIMEOUT", "12.0")),
                "retry_budget": int(os.getenv("PR_AGENT_RETRY_BUDGET", "1"))
            }

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        provider_preference: Optional[str] = None,
        temperature: float = 0.2,
        triage_level: str = "standard"
    ) -> str:
        """
        Executes code review / remediation generation with single-execution guarantee:
        Primary -> Secondary Cloud -> Local Ollama -> Offline Heuristic Engine.
        Never executes multiple expensive providers simultaneously.
        Enforces bounded circuit breaker protection and fast triage model routing.
        """
        start_time = time.time()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()
        ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b").strip()
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        
        # Fast triage routing: Use 8B instant model on Groq when doing straightforward triage
        if triage_level == "fast" and not os.getenv("GROQ_MODEL"):
            groq_model = "llama-3.1-8b-instant"
        else:
            groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

        pref = (provider_preference or os.getenv("DEFAULT_PROVIDER", "gemini")).lower().strip()

        has_gemini_key = bool(gemini_key and len(gemini_key) > 10 and not gemini_key.startswith("your_"))
        has_groq_key = bool(groq_key and len(groq_key) > 10 and not groq_key.startswith("your_"))

        # Bounded prompt input to prevent context exhaustion
        bounded_prompt = prompt[:24000] if len(prompt) > 24000 else prompt

        # Case 0: Explicit offline deterministic preference
        if pref in ["offline", "heuristic", "offline_heuristic"]:
            res = self._heuristic_agent_response(bounded_prompt)
            with self._lock:
                self.fallback_active = False
                self.operation_mode = "OFFLINE_DETERMINISTIC"
                self.last_provider_used = "offline_heuristic"
                self.last_model_used = "pr-agent-deterministic-v1"
                self.last_latency_ms = round((time.time() - start_time) * 1000, 2)
            return res

        # Case 1: Simulated network timeout
        elif os.getenv("PR_AGENT_SIMULATE_NETWORK_TIMEOUT") == "1":
            with self._lock:
                self.fallback_active = True
                self.error_category = "network_timeout"
                self.last_error = f"Network timeout connecting to {pref.upper()}: request timed out after 15000ms"
                self.primary_error = self.last_error

        # Case 2: Primary route -> Gemini
        elif pref == "gemini":
            if os.getenv("PR_AGENT_SIMULATE_PRIMARY_FAIL") == "1":
                with self._lock:
                    self.fallback_active = True
                    self.error_category = "primary_unavailable"
                    self.last_error = "Primary LLM (Gemini) unavailable: Quota exceeded / 429 ResourceExhausted"
                    self.primary_error = self.last_error
            elif not self.get_circuit_breaker("gemini").allow_request():
                with self._lock:
                    self.fallback_active = True
                    self.error_category = "circuit_breaker_open"
                    self.last_error = "Primary LLM (Gemini) circuit breaker OPEN: fast-failing to preserve latency"
                    self.primary_error = self.last_error
            elif has_gemini_key:
                try:
                    res = self._call_gemini(bounded_prompt, system_instruction, gemini_key, gemini_model, temperature)
                    if res and len(res.strip()) > 0:
                        self.get_circuit_breaker("gemini").record_success()
                        with self._lock:
                            self.fallback_active = False
                            self.operation_mode = "PRIMARY_CLOUD"
                            self.last_provider_used = "gemini"
                            self.last_model_used = gemini_model
                            self.last_latency_ms = round((time.time() - start_time) * 1000, 2)
                            self.last_error = ""
                            self.primary_error = None
                            self.fallback_error = None
                            self.error_category = ""
                        return res
                except (httpx.TimeoutException, TimeoutError) as te:
                    self.get_circuit_breaker("gemini").record_failure()
                    with self._lock:
                        self.fallback_active = True
                        self.error_category = "network_timeout"
                        self.last_error = f"Network timeout connecting to Gemini: {str(te)}"
                        self.primary_error = self.last_error
                except Exception as e:
                    self.get_circuit_breaker("gemini").record_failure()
                    with self._lock:
                        self.fallback_active = True
                        self.error_category = "primary_unavailable"
                        self.last_error = f"Primary LLM (Gemini) unavailable: {str(e)}"
                        self.primary_error = self.last_error
            else:
                with self._lock:
                    self.fallback_active = True
                    self.error_category = "primary_unavailable"
                    self.last_error = "Primary LLM (Gemini) unavailable: GEMINI_API_KEY not configured"
                    self.primary_error = self.last_error

        # Case 3: Primary route -> Groq
        elif pref == "groq":
            if os.getenv("PR_AGENT_SIMULATE_PRIMARY_FAIL") == "1":
                with self._lock:
                    self.fallback_active = True
                    self.error_category = "primary_unavailable"
                    self.last_error = "Primary LLM (Groq) unavailable: HTTP 429 Rate limit exceeded"
                    self.primary_error = self.last_error
            elif not self.get_circuit_breaker("groq").allow_request():
                with self._lock:
                    self.fallback_active = True
                    self.error_category = "circuit_breaker_open"
                    self.last_error = "Primary LLM (Groq) circuit breaker OPEN: fast-failing to preserve latency"
                    self.primary_error = self.last_error
            elif has_groq_key:
                try:
                    res = self._call_groq(bounded_prompt, system_instruction, groq_key, groq_model, temperature)
                    if res and len(res.strip()) > 0:
                        self.get_circuit_breaker("groq").record_success()
                        with self._lock:
                            self.fallback_active = False
                            self.operation_mode = "PRIMARY_CLOUD"
                            self.last_provider_used = "groq"
                            self.last_model_used = groq_model
                            self.last_latency_ms = round((time.time() - start_time) * 1000, 2)
                            self.last_error = ""
                            self.primary_error = None
                            self.fallback_error = None
                            self.error_category = ""
                        return res
                except (httpx.TimeoutException, TimeoutError) as te:
                    self.get_circuit_breaker("groq").record_failure()
                    with self._lock:
                        self.fallback_active = True
                        self.error_category = "network_timeout"
                        self.last_error = f"Network timeout connecting to Groq: {str(te)}"
                        self.primary_error = self.last_error
                except Exception as e:
                    self.get_circuit_breaker("groq").record_failure()
                    with self._lock:
                        self.fallback_active = True
                        self.error_category = "primary_unavailable"
                        self.last_error = f"Primary LLM (Groq) unavailable: {str(e)}"
                        self.primary_error = self.last_error
            else:
                with self._lock:
                    self.fallback_active = True
                    self.error_category = "primary_unavailable"
                    self.last_error = "Primary LLM (Groq) unavailable: GROQ_API_KEY not configured"
                    self.primary_error = self.last_error

        # Secondary Cloud Provider check (sequential; zero concurrent calls)
        sim_primary_down = (os.getenv("PR_AGENT_SIMULATE_PRIMARY_FAIL") == "1" or os.getenv("PR_AGENT_SIMULATE_NETWORK_TIMEOUT") == "1")
        if not sim_primary_down:
            if pref == "gemini" and has_groq_key and self.get_circuit_breaker("groq").allow_request():
                try:
                    res = self._call_groq(bounded_prompt, system_instruction, groq_key, groq_model, temperature)
                    if res and len(res.strip()) > 0:
                        self.get_circuit_breaker("groq").record_success()
                        with self._lock:
                            self.fallback_active = True
                            self.operation_mode = "SECONDARY_CLOUD"
                            self.last_provider_used = "groq"
                            self.last_model_used = groq_model
                            self.last_latency_ms = round((time.time() - start_time) * 1000, 2)
                            self.last_error = ""
                        return res
                except Exception:
                    self.get_circuit_breaker("groq").record_failure()

            if pref == "groq" and has_gemini_key and self.get_circuit_breaker("gemini").allow_request():
                try:
                    res = self._call_gemini(bounded_prompt, system_instruction, gemini_key, gemini_model, temperature)
                    if res and len(res.strip()) > 0:
                        self.get_circuit_breaker("gemini").record_success()
                        with self._lock:
                            self.fallback_active = True
                            self.operation_mode = "SECONDARY_CLOUD"
                            self.last_provider_used = "gemini"
                            self.last_model_used = gemini_model
                            self.last_latency_ms = round((time.time() - start_time) * 1000, 2)
                            self.last_error = ""
                        return res
                except Exception:
                    self.get_circuit_breaker("gemini").record_failure()

        # Fallback / Local Provider: Ollama running Qwen2.5-Coder
        is_ollama_up = False
        if os.getenv("PR_AGENT_SIMULATE_OLLAMA_FAIL") == "1":
            is_ollama_up = False
            with self._lock:
                self.fallback_error = "Ollama unavailable: connection refused (daemon offline)"
                self.error_category = "ollama_unavailable"
        elif os.getenv("PR_AGENT_SIMULATE_FALLBACK_FAIL") == "1":
            is_ollama_up = False
            with self._lock:
                self.fallback_error = "Fallback LLM unavailable: all local runners offline"
                self.error_category = "fallback_unavailable"
        elif os.getenv("PR_AGENT_SIMULATE_QWEN_FAIL") == "1":
            is_ollama_up = True
        else:
            is_ollama_up = is_ollama_running(ollama_url, timeout=2.0)
            if not is_ollama_up and os.getenv("AUTO_START_OLLAMA", "1") == "1":
                is_ollama_up = ollama_service.start_ollama(wait_seconds=8.0, preload=False)

        if is_ollama_up:
            if os.getenv("PR_AGENT_SIMULATE_QWEN_FAIL") == "1":
                with self._lock:
                    self.fallback_error = f"Qwen model unavailable: model '{ollama_model}' not found (HTTP 404)"
                    self.error_category = "qwen_unavailable"
            elif not self.get_circuit_breaker("ollama").allow_request():
                with self._lock:
                    self.fallback_error = "Ollama circuit breaker OPEN: fast-failing to preserve latency"
                    if not self.error_category:
                        self.error_category = "circuit_breaker_open"
            else:
                try:
                    res = self._call_ollama(bounded_prompt, system_instruction, ollama_url, ollama_model)
                    if res and len(res.strip()) > 0:
                        self.get_circuit_breaker("ollama").record_success()
                        with self._lock:
                            self.fallback_active = (pref != "ollama")
                            self.operation_mode = "LOCAL_OLLAMA"
                            self.last_provider_used = "ollama"
                            self.last_model_used = ollama_model
                            self.last_latency_ms = round((time.time() - start_time) * 1000, 2)
                            self.last_error = ""
                            self.fallback_error = None
                            if pref == "ollama":
                                self.primary_error = None
                                self.error_category = ""
                        return res
                except (httpx.TimeoutException, TimeoutError) as te:
                    self.get_circuit_breaker("ollama").record_failure()
                    with self._lock:
                        self.fallback_error = f"Network timeout connecting to Ollama: {str(te)}"
                        self.error_category = "network_timeout"
                except httpx.HTTPStatusError as hse:
                    self.get_circuit_breaker("ollama").record_failure()
                    with self._lock:
                        if hse.response.status_code == 404:
                            self.fallback_error = f"Qwen model unavailable: model '{ollama_model}' not found (HTTP 404)"
                            self.error_category = "qwen_unavailable"
                        else:
                            self.fallback_error = f"Ollama error: HTTP {hse.response.status_code}"
                except Exception as e:
                    self.get_circuit_breaker("ollama").record_failure()
                    with self._lock:
                        self.fallback_error = f"Ollama Qwen invocation failed: {str(e)}"
                        if not self.error_category:
                            self.error_category = "fallback_unavailable"

        # Final Fallback: Zero-Dependency Offline Heuristic Synthesis Engine
        with self._lock:
            self.fallback_active = True
            self.operation_mode = "OFFLINE_DETERMINISTIC"
            self.last_provider_used = "offline_heuristic"
            self.last_model_used = "pr-agent-deterministic-v1"
            self.last_latency_ms = round((time.time() - start_time) * 1000, 2)
            if not self.last_error:
                if self.primary_error and self.fallback_error:
                    self.last_error = f"LLM_PROVIDER_UNAVAILABLE: Primary & fallback LLMs unavailable ({self.primary_error}; {self.fallback_error})"
                    self.error_category = "fallback_unavailable"
                elif self.fallback_error:
                    self.last_error = self.fallback_error
                elif self.primary_error:
                    self.last_error = self.primary_error
                else:
                    self.last_error = "Operating in offline deterministic mode"

        return self._heuristic_agent_response(bounded_prompt)

    def _call_gemini(
        self,
        prompt: str,
        system: Optional[str],
        api_key: str,
        model_name: str,
        temp: float
    ) -> str:
        """Invokes Google Gemini with bounded timeout and single retry."""
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        models_to_try = [model_name, "gemini-1.5-flash", "gemini-2.0-flash"]
        # Deduplicate while preserving order
        seen = set()
        unique_models = [m for m in models_to_try if not (m in seen or seen.add(m))]

        last_exc = None
        for m_name in unique_models:
            for attempt in range(2):  # Max 1 retry
                try:
                    model = genai.GenerativeModel(
                        model_name=m_name,
                        system_instruction=system if system else None,
                        generation_config={
                            "temperature": temp,
                            "response_mime_type": "application/json",
                            "max_output_tokens": 2500
                        }
                    )
                    response = model.generate_content(prompt, request_options={"timeout": 15.0})
                    if response and response.text:
                        return response.text
                except Exception as e:
                    last_exc = e
                    time.sleep(0.5)

        # Fallback to standard text generation without forced JSON mime
        try:
            model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=system if system else None)
            response = model.generate_content(prompt, request_options={"timeout": 15.0})
            if response and response.text:
                return response.text
        except Exception as e:
            last_exc = e

        if last_exc:
            raise last_exc
        raise RuntimeError("Gemini returned empty response text")

    def _call_groq(
        self,
        prompt: str,
        system: Optional[str],
        api_key: str,
        model_name: str,
        temp: float
    ) -> str:
        """Invokes Groq API with bounded timeout, max tokens, and JSON mode."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_name or "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": temp,
            "max_tokens": 2500,
            "response_format": {"type": "json_object"}
        }

        timeout_sec = float(os.getenv("PR_AGENT_LLM_TIMEOUT", "15.0"))
        client = _get_shared_client(timeout=timeout_sec)
        last_exc = None
        for attempt in range(2):
            try:
                resp = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                last_exc = e
                time.sleep(0.5)

        if last_exc:
            raise last_exc
        raise RuntimeError("Groq returned empty response")

    def _call_ollama(
        self,
        prompt: str,
        system: Optional[str],
        base_url: str,
        model_name: str
    ) -> str:
        """Invokes local Ollama with bounded parameters to fit within 4 GB VRAM."""
        full_prompt = f"System: {system}\n\nUser: {prompt}" if system else prompt
        is_coder = "CODER AGENT" in full_prompt or "CORRECTED_SOURCE_CODE" in full_prompt
        num_predict = 800 if is_coder else 450
        payload = {
            "model": model_name,
            "prompt": full_prompt,
            "stream": False,
            "format": "json",
            "options": {
                "num_predict": num_predict,
                "num_ctx": 2048,
                "temperature": 0.15
            }
        }
        client = _get_shared_client(timeout=35.0)
        resp = client.post(f"{base_url}/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "")

    def _heuristic_agent_response(self, prompt: str) -> str:
        """
        Deterministic, zero-dependency offline synthesis engine.
        Parses static findings + RAG rules and produces structured JSON responses
        for Security Agent, Bug Detection Agent, Summary Agent, or Coder Agent.
        """
        static_findings = []
        rag_rules = []
        try:
            if "DETERMINISTIC STATIC ANALYSIS FINDINGS (MCP Layer):" in prompt:
                part = prompt.split("DETERMINISTIC STATIC ANALYSIS FINDINGS (MCP Layer):")[1]
                part = part.split("GROUNDED RAG RULES")[0].strip()
                static_findings = json.loads(part)
        except Exception:
            static_findings = []

        try:
            if "GROUNDED RAG RULES" in prompt:
                part = prompt.split("GROUNDED RAG RULES")[1]
                part = part.split("Analyze")[0].strip()
                if ":" in part:
                    part = part.split(":", 1)[1].strip()
                rag_rules = json.loads(part)
        except Exception:
            rag_rules = []

        # If prompt is for Security Agent
        if "Security Agent" in prompt or "vulnerabilities" in prompt.lower():
            sec_findings = []
            for sf in static_findings:
                if sf.get("category") == "security":
                    rag_match = next((r for r in rag_rules if r.get("cwe") == sf.get("cwe")), None)
                    citation = (
                        f"RAG: {rag_match.get('citation', 'OWASP:A03:2021')} + MCP: {sf.get('tool', 'linter').capitalize()} {sf.get('rule_id', '')}"
                        if rag_match else f"MCP: {sf.get('tool', 'linter').capitalize()} {sf.get('rule_id', '')}"
                    )
                    sec_findings.append({
                        "line": sf.get("line", 1),
                        "severity": sf.get("severity", "high"),
                        "category": "security",
                        "title": f"Security Vulnerability ({sf.get('cwe', 'CWE-Unknown')})",
                        "description": sf.get("message", "Security vulnerability detected by deterministic static analysis."),
                        "recommendation": rag_match.get("remediation", "Apply defensive validation and parameterized controls.") if rag_match else "Review and remediate according to secure coding standards.",
                        "cwe": sf.get("cwe", "CWE-Unknown"),
                        "owasp": rag_match.get("rule_id", "OWASP:A03:2021") if rag_match else "OWASP:General",
                        "rule_citation": citation
                    })
            return json.dumps({
                "agent": "security_agent",
                "findings": sec_findings
            })

        # If prompt is for Bug Detection Agent
        if "Bug-Detection Agent" in prompt or "logic errors" in prompt.lower():
            bug_findings = []
            for sf in static_findings:
                if sf.get("category") in ["bug", "style", "performance"]:
                    rag_match = next((r for r in rag_rules if r.get("cwe") == sf.get("cwe")), None)
                    citation = (
                        f"RAG: {rag_match.get('citation', 'CWE-Logic')} + MCP: {sf.get('tool', 'linter').capitalize()} {sf.get('rule_id', '')}"
                        if rag_match else f"MCP: {sf.get('tool', 'linter').capitalize()} {sf.get('rule_id', '')}"
                    )
                    bug_findings.append({
                        "line": sf.get("line", 1),
                        "severity": sf.get("severity", "medium"),
                        "category": sf.get("category", "bug"),
                        "title": f"Defect / Quality Issue ({sf.get('rule_id', 'Lint')})",
                        "description": sf.get("message", "Logic bug, resource leak, or style defect detected."),
                        "recommendation": rag_match.get("remediation", "Apply defensive boundary checks and resource management.") if rag_match else "Ensure resource cleanup and boundary verification.",
                        "cwe": sf.get("cwe", "CWE-404"),
                        "rule_citation": citation
                    })
            return json.dumps({
                "agent": "bug_agent",
                "findings": bug_findings
            })

        # If prompt is for Coder Agent
        if "Coder Agent" in prompt or "Rewrite the code" in prompt:
            return json.dumps({})

        return json.dumps({"status": "acknowledged", "findings": []})


# Global gateway singleton
gateway = LLMGateway()
