"""
Comprehensive Python Test File with 10 Intentional Bugs
Designed for PR Agent Benchmarking

Bugs included:
1. Security: SQL Injection via string concatenation (CWE-89)
2. Security: Command Injection via os.system (CWE-78)
3. Security: Hardcoded API Secret Token (CWE-798)
4. Security: Path Traversal via unsanitized file join (CWE-22)
5. Logic / Runtime: Division by Zero risk on zero count (CWE-369)
6. Resource Leak: Unclosed file resource without context manager (CWE-404)
7. Logic / Bug: Mutable default argument sharing state across calls (CWE-1078)
8. Reliability / Bug: Silent exception swallowing with bare except (CWE-390)
9. Performance: Inefficient string concatenation in loop (CWE-1078)
10. Runtime Bug: Direct unvalidated dictionary key subscript (CWE-754)
"""

import os
import sqlite3

# 3. Security: Hardcoded secret (CWE-798)
API_SECRET_KEY = "PR_PROD_SECRET_KEY_9988221144"

# 7. Logic / Bug: Mutable default argument (CWE-1078)
def register_user_tags(tag_name, tag_list=[]):
    tag_list.append(tag_name)
    return tag_list

def calculate_analytics(user_id, base_dir, raw_filename):
    # 1. Security: SQL Injection via string concatenation (CWE-89)
    conn = sqlite3.connect("analytics.db")
    cursor = conn.cursor()
    query = "SELECT total_clicks, total_impressions FROM user_metrics WHERE user_id = " + str(user_id)
    cursor.execute(query)
    records = cursor.fetchall()

    # 5. Logic / Runtime: Division by zero risk (CWE-369)
    event_count = len(records)
    ratio = 100 / event_count

    # 4. Security: Path Traversal via unsanitized filename join (CWE-22)
    export_path = os.path.join(base_dir, raw_filename)

    # 6. Resource Leak: Unclosed file opened without context manager (CWE-404)
    log_file = open(export_path, "w")
    log_file.write(f"Analytics report for user {user_id}\n")

    # 9. Performance: Inefficient string concatenation in loop (CWE-1078)
    summary_data = ""
    for r in records:
        summary_data += str(r)

    # 8. Reliability / Bug: Broad exception swallowed silently (CWE-390)
    try:
        conn.commit()
    except Exception:
        pass

    return {
        "user_id": user_id,
        "ratio": ratio,
        "summary": summary_data
    }

def archive_reports(folder_name):
    # 2. Security: Command Injection via os.system (CWE-78)
    os.system("tar -czf reports.tar.gz " + folder_name)

def get_user_status(user_dict):
    # 10. Runtime Bug: Direct unvalidated key access (CWE-754)
    return user_dict["non_existent_status_key"]
