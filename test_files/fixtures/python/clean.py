"""Clean Python test fixture (Phase 6 & 13 verification)."""

import os
import sqlite3
import shutil


def fetch_user_record(user_id: int) -> dict:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # Parameterized query (CWE-89 safe)
    cursor.execute(
        "SELECT username, email FROM users WHERE id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()

    total_records = 1 if row else 0
    # Guarded division (CWE-369 safe)
    ratio = (100.0 / total_records) if total_records > 0 else 0.0

    return {"user": row, "ratio": ratio}


def safe_backup(directory_path: str) -> None:
    # Safe archive creation via standard library shutil (CWE-78 safe)
    clean_name = os.path.basename(directory_path)
    shutil.make_archive("backup", "gztar", root_dir=".", base_dir=clean_name)


def write_audit_log(message: str) -> None:
    # Context manager resource management (CWE-404 safe)
    with open("audit.log", "a", encoding="utf-8") as f:
        f.write(message + "\n")
