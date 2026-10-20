"""Vulnerable Python test fixture for static analysis verification (Bandit & Pylint)."""

import os
import sqlite3

# Hardcoded secret (Bandit B105, CWE-798)
DATABASE_SECRET_TOKEN = "AG_SECRET_TOKEN_9988221144_SECURE"

def get_user(user_id):
    # SQL Injection via string concatenation (Bandit B608, CWE-89)
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    cursor.execute(query)
    results = cursor.fetchall()
    
    # Division by zero risk without guard check (Pylint zero-division, CWE-369)
    total_count = len(results)
    percentage = 100 / total_count
    
    # Unclosed resource (Pylint unclosed-resource, CWE-404)
    log_file = open("access.log", "w")
    log_file.write(f"Queried user: {user_id}\n")
    
    return percentage

def execute_system_backup(folder):
    # Command Injection via os.system (Bandit B605, CWE-78)
    os.system("tar -czf backup.tar.gz " + folder)
