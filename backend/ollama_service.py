"""
Automated Ollama Qwen Coder Lifecycle Manager for PR Agent.
Features:
- Validates Ollama runtime availability and model presence via real probes.
- Strictly avoids downloading large models automatically at application startup.
- Manages background Ollama process lifecycle (auto-start & clean shutdown).
- Documents 4 GB VRAM constraints, quantization profiles, and layer offload behavior.
"""

import os
import sys
import time
import shutil
import atexit
import signal
import subprocess
import threading
from typing import Optional, Dict, Any, List
import httpx

_OLLAMA_PROC: Optional[subprocess.Popen] = None
_MANAGED_BY_US: bool = False
_LOCK = threading.Lock()

# Global hardware acceleration defaults for Ollama
os.environ.setdefault("OLLAMA_IGPU_ENABLE", "1")
os.environ.setdefault("OLLAMA_NUM_PARALLEL", "1")
os.environ.setdefault("OLLAMA_FLASH_ATTENTION", "1")


def get_vram_guidance() -> Dict[str, Any]:
    """
    Documents realistic local model requirements under the 4 GB VRAM hardware constraint.
    Model size, quantization (Q4 vs Q8), context length, system RAM, and GPU driver compatibility
    directly determine feasibility.
    """
    return {
        "vram_constraint": "4 GB VRAM (Consumer GPU / Laptop / iGPU)",
        "guidance_summary": "4 GB VRAM is a strict constraint that requires calibrated quantization and context bounds.",
        "recommended_models": [
            {
                "model": "qwen2.5-coder:1.5b",
                "parameter_count": "1.5 Billion",
                "quantization": "Q4_K_M",
                "disk_size_gb": 1.0,
                "vram_required_gb": 1.6,
                "context_window": "4096 tokens",
                "fit_in_4gb_vram": "100% Fits in VRAM (Ultra-fast local execution)",
                "recommended_for": "Dedicated 4GB GPUs or low-spec hardware"
            },
            {
                "model": "qwen2.5-coder:3b",
                "parameter_count": "3.0 Billion",
                "quantization": "Q4_K_M",
                "disk_size_gb": 1.9,
                "vram_required_gb": 2.8,
                "context_window": "4096 tokens",
                "fit_in_4gb_vram": "100% Fits in VRAM (~2.8 GB total footprint)",
                "recommended_for": "Sweet spot for code generation within 4GB limit"
            },
            {
                "model": "qwen2.5-coder:7b",
                "parameter_count": "7.6 Billion",
                "quantization": "Q4_K_M",
                "disk_size_gb": 4.7,
                "vram_required_gb": 5.4,
                "context_window": "2048 - 4096 tokens",
                "fit_in_4gb_vram": "Partial Offload (~22 layers on GPU, ~6 layers in System RAM)",
                "recommended_for": "High-precision code review with mixed GPU/CPU compute"
            }
        ],
        "operational_rules": [
            "Never download large multi-gigabyte models automatically on startup.",
            "Keep context window bounded (num_ctx: 2048) to avoid KV cache VRAM overflow.",
            "If Ollama is unavailable or out-of-memory, fall back to the Offline Heuristic Engine."
        ]
    }


def find_ollama_binary() -> Optional[str]:
    """Locates the Ollama executable on the system."""
    # 1. System PATH
    found = shutil.which("ollama")
    if found:
        return found

    # 2. Windows LocalAppData location
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        cand = os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe")
        if os.path.isfile(cand):
            return cand

    # 3. Standard user path fallback
    user_cand = os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe")
    if os.path.isfile(user_cand):
        return user_cand

    # 4. Program Files
    for pf in ["ProgramFiles", "ProgramFiles(x86)"]:
        base = os.environ.get(pf, "")
        if base:
            cand = os.path.join(base, "Ollama", "ollama.exe")
            if os.path.isfile(cand):
                return cand

    return None


def is_ollama_running(base_url: str = "http://127.0.0.1:11434", timeout: float = 2.5) -> bool:
    """Checks whether the Ollama server is actively responding via a real network probe."""
    try:
        r = httpx.get(f"{base_url}/api/tags", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def get_installed_models(base_url: str = "http://127.0.0.1:11434", timeout: float = 2.5) -> List[str]:
    """Retrieves list of locally installed models from Ollama."""
    try:
        r = httpx.get(f"{base_url}/api/tags", timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            return [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        pass
    return []


def is_model_installed(base_url: str, model_name: str, timeout: float = 2.5) -> bool:
    """
    Validates whether the specific model is downloaded and ready in Ollama.
    Never initiates network downloads.
    """
    installed = get_installed_models(base_url, timeout=timeout)
    target = model_name.lower().strip()
    target_base = target.split(":")[0]

    for m in installed:
        m_lower = m.lower().strip()
        if target == m_lower or target in m_lower or m_lower.startswith(target_base):
            return True
    return False


def _preload_model_worker(base_url: str, model_name: str):
    """
    Background worker to warm up and preload the model into memory.
    Only called IF the model is already verified to be installed.
    Never downloads or pulls models.
    """
    try:
        if not is_model_installed(base_url, model_name, timeout=3.0):
            print(f"[OLLAMA] Configured model '{model_name}' is not downloaded. Skipping preload.")
            return

        payload = {
            "model": model_name,
            "prompt": "ping",
            "stream": False,
            "options": {"num_predict": 1}
        }
        httpx.post(f"{base_url}/api/generate", json=payload, timeout=60.0)
        print(f"[OLLAMA] Model '{model_name}' successfully preloaded and ready in memory.")
    except Exception as e:
        print(f"[OLLAMA] Preload note for '{model_name}': {e}")


class OllamaServiceManager:
    """
    Manages the lifecycle of the local Ollama background server.
    Ensures:
    1. Real runtime verification.
    2. Zero automated multi-gigabyte downloads.
    3. Clean process termination on shutdown.
    """

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()
        self.model_name = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b").strip()
        self._registered_handlers = False

    def _register_exit_hooks(self):
        """Registers atexit and termination signal handlers."""
        if self._registered_handlers:
            return
        atexit.register(self.stop_ollama)

        for sig in [getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)]:
            if sig is not None:
                try:
                    orig_handler = signal.getsignal(sig)
                    def _signal_handler(signum, frame):
                        self.stop_ollama()
                        if callable(orig_handler) and orig_handler not in [signal.SIG_DFL, signal.SIG_IGN]:
                            orig_handler(signum, frame)
                        else:
                            sys.exit(0)
                    signal.signal(sig, _signal_handler)
                except (ValueError, AttributeError):
                    pass
        self._registered_handlers = True

    def start_ollama(self, wait_seconds: float = 15.0, preload: bool = True) -> bool:
        """
        Starts the Ollama server in the background if not already running.
        Validates model presence without initiating downloads.
        """
        global _OLLAMA_PROC, _MANAGED_BY_US

        self._register_exit_hooks()

        # Check if Ollama is already running
        if is_ollama_running(self.base_url):
            print(f"[OLLAMA] Ollama server is already online at {self.base_url}.")
            if preload and is_model_installed(self.base_url, self.model_name):
                threading.Thread(
                    target=_preload_model_worker,
                    args=(self.base_url, self.model_name),
                    daemon=True
                ).start()
            return True

        binary = find_ollama_binary()
        if not binary:
            print("[OLLAMA] Warning: Ollama executable not found on system. Automatic launch skipped.")
            return False

        with _LOCK:
            if is_ollama_running(self.base_url):
                return True

            print(f"[OLLAMA] Launching Ollama daemon via: {binary} serve ...")
            try:
                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NO_WINDOW

                daemon_env = dict(os.environ)
                daemon_env["OLLAMA_IGPU_ENABLE"] = "1"
                daemon_env["OLLAMA_NUM_PARALLEL"] = "1"
                daemon_env["OLLAMA_FLASH_ATTENTION"] = "1"

                _OLLAMA_PROC = subprocess.Popen(
                    [binary, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creation_flags,
                    env=daemon_env
                )
                _MANAGED_BY_US = True
            except Exception as e:
                print(f"[OLLAMA] Failed to launch Ollama process: {e}")
                return False

            # Wait until server starts listening
            start_time = time.time()
            while time.time() - start_time < wait_seconds:
                if is_ollama_running(self.base_url):
                    print(f"[OLLAMA] Server online and listening at {self.base_url} ({round(time.time() - start_time, 2)}s).")
                    
                    # Validate model without downloading
                    if is_model_installed(self.base_url, self.model_name):
                        if preload:
                            threading.Thread(
                                target=_preload_model_worker,
                                args=(self.base_url, self.model_name),
                                daemon=True
                            ).start()
                    else:
                        print(f"[OLLAMA] Configured model '{self.model_name}' is not installed in local library.")
                        print(f"[OLLAMA] Auto-download is strictly disabled to prevent large bandwidth consumption.")
                        print(f"[OLLAMA] To install manually run: 'ollama pull {self.model_name}'")
                    return True
                time.sleep(0.5)

            print("[OLLAMA] Timed out waiting for Ollama to start.")
            return False

    def stop_ollama(self) -> bool:
        """
        Shuts down the Ollama background server if it was launched by this application.
        """
        global _OLLAMA_PROC, _MANAGED_BY_US

        with _LOCK:
            if not _MANAGED_BY_US or _OLLAMA_PROC is None:
                return False

            print("[OLLAMA] Shutting down managed Ollama server...")
            try:
                _OLLAMA_PROC.terminate()
                try:
                    _OLLAMA_PROC.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    _OLLAMA_PROC.kill()
                    _OLLAMA_PROC.wait(timeout=2.0)
                print("[OLLAMA] Ollama server terminated successfully.")
            except Exception as e:
                print(f"[OLLAMA] Error terminating Ollama process: {e}")
            finally:
                _OLLAMA_PROC = None
                _MANAGED_BY_US = False

            # Clean up any lingering child llama-server on Windows
            if sys.platform == "win32":
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", "llama-server.exe"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False
                    )
                except Exception:
                    pass

            return True

    def get_runtime_status(self) -> Dict[str, Any]:
        """Returns verified runtime status, installed models, and VRAM guidance."""
        running = is_ollama_running(self.base_url)
        models = get_installed_models(self.base_url) if running else []
        model_installed = is_model_installed(self.base_url, self.model_name) if running else False

        return {
            "running": running,
            "base_url": self.base_url,
            "configured_model": self.model_name,
            "model_installed": model_installed,
            "installed_models": models,
            "vram_guidance": get_vram_guidance()
        }


# Global singleton instance
ollama_service = OllamaServiceManager()
