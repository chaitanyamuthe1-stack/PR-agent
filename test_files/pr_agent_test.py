"""
PR Agent Comprehensive Test File (pr_agent_test.py)
Designed for PR Agent Multi-Agent Code Review & Auto-Correction Benchmarking

Bugs & Security Weaknesses Included:
1.  Security: SQL Injection via string concatenation (CWE-89)
2.  Security: Command Injection via os.system (CWE-78)
3.  Security: Hardcoded Credentials / API Token (CWE-798)
4.  Security: Path Traversal via unsanitized filename join (CWE-22)
5.  Security: Insecure Deserialization via pickle (CWE-502)
6.  Security: Weak Cryptographic Hashing via MD5 (CWE-328)
7.  Logic / Runtime: Division by Zero risk on zero count (CWE-369)
8.  Logic / Runtime: IndexError on array access without bounds check (CWE-129)
9.  Resource Leak: Unclosed file opened without context manager (CWE-404)
10. Reliability: Silent exception swallowing with bare except (CWE-390)
11. Logic / Bug: Mutable default argument sharing state across calls (CWE-1078)
12. Network / DoS: Missing HTTP request timeout (CWE-400)
13. Compatibility / Bug: Missing file encoding in text file open (PEP 597)
14. Runtime Bug: Direct unvalidated dictionary key subscript (CWE-754)
"""

import os
import sys
import pickle
import hashlib
import sqlite3
import urllib.request

# 3. Security: Hardcoded credentials (CWE-798)
API_SECRET_KEY = "PR_PROD_SECRET_KEY_9988221144"
DATABASE_PASSWORD = "SuperSecretAdminPassword123!"

# 11. Logic / Bug: Mutable default argument (CWE-1078)
def register_user_tags(tag_name, tag_list=[]):
    tag_list.append(tag_name)
    return tag_list

# 8. Logic / Runtime: IndexError on unchecked list access (CWE-129)
def get_primary_metric(metrics_list):
    return metrics_list[0]

def calculate_analytics(user_id, base_dir, raw_filename):
    # 1. Security: SQL Injection via string concatenation (CWE-89)
    conn = sqlite3.connect("analytics.db")
    cursor = conn.cursor()
    query = "SELECT total_clicks, total_impressions FROM user_metrics WHERE user_id = " + str(user_id)
    cursor.execute(query)
    records = cursor.fetchall()

    # 7. Logic / Runtime: Division by zero risk (CWE-369)
    event_count = len(records)
    ratio = 100 / event_count

    # 4. Security: Path Traversal via unsanitized filename join (CWE-22)
    export_path = os.path.join(base_dir, raw_filename)

    # 9 & 13. Resource Leak (CWE-404) & Missing Encoding (PEP 597)
    log_file = open(export_path, "w")
    log_file.write(f"Analytics report for user {user_id}\n")

    # Inefficient string concatenation
    summary_data = ""
    for r in records:
        summary_data += str(r)

    # 10. Reliability: Broad exception swallowed silently (CWE-390)
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

def restore_session_data(serialized_payload):
    # 5. Security: Insecure Deserialization via pickle (CWE-502)
    return pickle.loads(serialized_payload)

def generate_checksum(payload_bytes):
    # 6. Security: Weak Cryptographic Hashing via MD5 (CWE-328)
    return hashlib.md5(payload_bytes).hexdigest()

def fetch_remote_config(config_url):
    # 12. Network / DoS: Missing timeout in HTTP request (CWE-400)
    response = urllib.request.urlopen(config_url)
    return response.read().decode('utf-8')

def get_user_status(user_dict):
    # 14. Runtime Bug: Direct unvalidated key access (CWE-754)
    return user_dict["non_existent_status_key"]

if __name__ == "__main__":
    print("PR Agent Test File Loaded.")
