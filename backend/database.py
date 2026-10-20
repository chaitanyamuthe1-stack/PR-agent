"""
Database persistence layer for PR Agent.
Provides SQLite-backed persistence for review records and audit history.
Designed with graceful degradation:
If the database is locked, permission-denied, disk-full, corrupted, or unavailable,
it falls back seamlessly to a thread-safe in-memory cache without crashing.
"""

import os
import re
import json
import time
import sqlite3
import threading
from typing import Dict, Any, Optional

def sanitize_db_error(msg: Any) -> str:
    """Strips internal host filesystem paths from database errors."""
    if not msg:
        return ""
    text = str(msg)
    text = re.sub(r'[A-Za-z]:\\[^:\n\r\t]+', '[INTERNAL_PATH]', text)
    text = re.sub(r'/(?:home|Users|var|tmp|etc|root)/[^\s:\n\r\t]+', '[INTERNAL_PATH]', text)
    return text

DB_FILE = os.getenv("PR_AGENT_DB_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "pr_agent_audit.db"))

_MEMORY_FALLBACK_CACHE: Dict[str, Any] = {}
MAX_MEMORY_CACHE: int = 100
_DB_LOCK = threading.Lock()
_HEALTH_CACHE: Dict[str, Any] = {"count": 0, "expires_at": 0.0}


def get_db_connection():
    """Establishes an SQLite connection with WAL mode and busy timeout."""
    if os.getenv("PR_AGENT_SIMULATE_DB_FAIL") == "1":
        raise sqlite3.OperationalError("Simulated database failure: connection refused / disk I/O error")

    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
    except Exception:
        pass
    return conn


def init_db() -> Dict[str, Any]:
    """Initializes the SQLite schema with migration safety for audit and review tracking."""
    try:
        with _DB_LOCK:
            conn = get_db_connection()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS reviews (
                        review_id TEXT PRIMARY KEY,
                        timestamp REAL,
                        filename TEXT,
                        language TEXT,
                        health_score REAL,
                        post_fix_score REAL,
                        verdict TEXT,
                        unresolved_count INTEGER,
                        resolved_count INTEGER,
                        remediation_status TEXT,
                        auto_fix_failure INTEGER,
                        json_data TEXT
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_reviews_timestamp ON reviews (timestamp DESC)
                """)

                # Migration check: ensure all columns exist if migrating older schema
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(reviews)")
                existing_cols = {row["name"] for row in cursor.fetchall()}
                expected_cols = {
                    "post_fix_score": "REAL DEFAULT 10.0",
                    "auto_fix_failure": "INTEGER DEFAULT 0",
                    "unresolved_count": "INTEGER DEFAULT 0",
                    "resolved_count": "INTEGER DEFAULT 0",
                    "remediation_status": "TEXT DEFAULT 'NOT_REQUIRED'"
                }
                for col_name, col_type in expected_cols.items():
                    if col_name not in existing_cols:
                        conn.execute(f"ALTER TABLE reviews ADD COLUMN {col_name} {col_type}")

            conn.close()
        return {"status": "healthy", "engine": "sqlite3", "file": os.path.basename(DB_FILE)}
    except Exception as e:
        return {"status": "degraded", "engine": "in-memory-fallback", "error": sanitize_db_error(e)}


def save_review_record(review_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Saves a review record into SQLite.
    If SQLite fails, records to bounded in-memory fallback without raising an unhandled exception.
    """
    with _DB_LOCK:
        _MEMORY_FALLBACK_CACHE[review_id] = data
        if len(_MEMORY_FALLBACK_CACHE) > MAX_MEMORY_CACHE:
            oldest_key = next(iter(_MEMORY_FALLBACK_CACHE))
            del _MEMORY_FALLBACK_CACHE[oldest_key]

    try:
        with _DB_LOCK:
            conn = get_db_connection()
            with conn:
                conn.execute("""
                    INSERT OR REPLACE INTO reviews (
                        review_id, timestamp, filename, language, health_score, post_fix_score,
                        verdict, unresolved_count, resolved_count, remediation_status,
                        auto_fix_failure, json_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    review_id,
                    time.time(),
                    data.get("filename", "unknown"),
                    data.get("language", "unknown"),
                    float(data.get("health_score", 10.0)),
                    float(data.get("post_fix_score", data.get("health_score", 10.0))),
                    str(data.get("verdict", "PENDING")),
                    int(data.get("unresolved_count", 0)),
                    int(data.get("resolved_count", 0)),
                    str(data.get("remediation_status", "NOT_REQUIRED")),
                    1 if data.get("auto_fix_failure") else 0,
                    json.dumps(data)
                ))
            conn.close()
        return {"status": "persisted", "engine": "sqlite3"}
    except Exception as e:
        return {
            "status": "degraded",
            "engine": "in-memory-fallback",
            "error": f"Database failure: {sanitize_db_error(e)}"
        }


def get_review_record(review_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a review record from SQLite or the fallback in-memory cache.
    """
    # Check SQLite first
    try:
        with _DB_LOCK:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT json_data FROM reviews WHERE review_id = ?", (review_id,))
            row = cursor.fetchone()
            conn.close()
            if row and row["json_data"]:
                return json.loads(row["json_data"])
    except Exception:
        pass

    # Fall back to in-memory cache
    with _DB_LOCK:
        return _MEMORY_FALLBACK_CACHE.get(review_id)


def get_db_health() -> Dict[str, Any]:
    """Provides database operational health telemetry with TTL caching to avoid excessive queries."""
    global _HEALTH_CACHE
    if os.getenv("PR_AGENT_SIMULATE_DB_FAIL") == "1":
        return {
            "status": "degraded",
            "engine": "in-memory-fallback",
            "error": "Simulated database failure: connection refused / disk I/O error",
            "in_memory_cached": len(_MEMORY_FALLBACK_CACHE)
        }

    now = time.time()
    try:
        with _DB_LOCK:
            if now < _HEALTH_CACHE["expires_at"]:
                count = _HEALTH_CACHE["count"]
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM reviews")
                count = cursor.fetchone()["count"]
                conn.close()
                _HEALTH_CACHE = {"count": count, "expires_at": now + 5.0}

        return {
            "status": "healthy",
            "engine": "sqlite3",
            "total_records": count,
            "in_memory_cached": len(_MEMORY_FALLBACK_CACHE)
        }
    except Exception as e:
        return {
            "status": "degraded",
            "engine": "in-memory-fallback",
            "error": sanitize_db_error(e),
            "in_memory_cached": len(_MEMORY_FALLBACK_CACHE)
        }


# Auto-initialize on module load
init_db()
