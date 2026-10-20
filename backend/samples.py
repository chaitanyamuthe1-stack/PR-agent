"""
Preset Buggy Source Code Samples for PR Agent.
Supports all 6 core languages with real vulnerabilities, logic bugs, boundary errors, 
resource leaks, and performance defects.

WARNING: All samples in this file are INTENTIONALLY VULNERABLE and designed
strictly for automated benchmarking, static analysis verification, and multi-agent
remediation testing.
"""

SAMPLES = {
    "python": {
        "filename": "vulnerable_app.py",
        "language": "python",
        "tools": ["pylint", "bandit"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "boundary", "runtime", "resource", "performance", "syntax"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-89", "rule_id": "B608", "line_hint": 21, "title": "SQL Injection via string concatenation"},
            {"category": "security", "cwe": "CWE-78", "rule_id": "B605", "line_hint": 46, "title": "Command Injection via os.system"},
            {"category": "security", "cwe": "CWE-798", "rule_id": "B105", "line_hint": 30, "title": "Hardcoded sensitive admin token"},
            {"category": "security", "cwe": "CWE-22", "rule_id": "CWE-22", "line_hint": 51, "title": "Path Traversal via unsanitized file path"},
            {"category": "runtime", "cwe": "CWE-369", "rule_id": "zero-division", "line_hint": 27, "title": "Division by zero when user list is empty"},
            {"category": "resource", "cwe": "CWE-404", "rule_id": "unclosed-resource", "line_hint": 34, "title": "Unclosed file resource leak"},
            {"category": "boundary", "cwe": "CWE-193", "rule_id": "off-by-one", "line_hint": 56, "title": "Off-by-one boundary access on list length"},
            {"category": "performance", "cwe": "CWE-400", "rule_id": "inefficient-concat", "line_hint": 60, "title": "Inefficient string concatenation in quadratic loop"},
            {"category": "syntax", "cwe": "CWE-390", "rule_id": "bare-except", "line_hint": 52, "title": "Bare except clause suppressing critical interrupts"}
        ],
        "code": '''# WARNING: INTENTIONALLY VULNERABLE BENCHMARK SAMPLE - FOR TESTING & AUDIT ONLY
# PR Agent Multi-Language Benchmark Suite

import os
import sqlite3

def get_user_profile(user_id):
    # Security: SQL Injection (Bandit B608, CWE-89, OWASP A03:2021)
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = "SELECT username, role, email FROM users WHERE id = " + str(user_id)
    cursor.execute(query)
    user = cursor.fetchone()
    
    # Runtime Bug: Division by zero risk if user count is zero (CWE-369)
    user_count = len(user) if user else 0
    average_score = 100 / user_count
    
    # Security: Hardcoded sensitive admin token (Bandit B105, CWE-798)
    admin_token = "AG_SECRET_ROOT_API_KEY_9921_X"
    
    # Resource Leak: Unclosed resource (CWE-404, Pylint unclosed-resource)
    temp_cache = open("/tmp/cache.txt", "w")
    try:
        # Syntax / Lint Hazard: Bare except clause suppressing system interrupts (CWE-390, Pylint W0702)
        temp_cache.write(admin_token)
    except:
        pass
    
    return {"user": user, "avg": average_score}

def run_backup(folder_name):
    # Security: Command Injection (Bandit B605, CWE-78)
    os.system("tar -czf backup.tar.gz " + folder_name)

def export_audit_log(tags, user_file):
    # Security: Path Traversal (CWE-22)
    with open(os.path.join("/var/log/audit", user_file), "r") as f:
        data = f.read()
    
    # Boundary Bug: Off-by-one / IndexError accessing array length (CWE-193)
    last_tag = tags[len(tags)]
    
    # Performance Defect: Inefficient string concatenation in loop (CWE-400)
    audit_summary = ""
    for i in range(len(tags)):
        audit_summary += tags[i] + ":" + str(len(data)) + ";"
        
    return {"summary": audit_summary, "last": last_tag}
'''
    },
    "cpp": {
        "filename": "network_handler.cpp",
        "language": "cpp",
        "tools": ["cppcheck"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "boundary", "runtime", "resource", "performance", "syntax"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-120", "rule_id": "buffer-overflow", "line_hint": 14, "title": "Buffer Overflow with unsafe strcpy"},
            {"category": "security", "cwe": "CWE-798", "rule_id": "hardcoded-credentials", "line_hint": 17, "title": "Hardcoded master auth key"},
            {"category": "resource", "cwe": "CWE-401", "rule_id": "memleak", "line_hint": 20, "title": "Memory leak: heap allocated session_id without free"},
            {"category": "runtime", "cwe": "CWE-476", "rule_id": "nullPointer", "line_hint": 24, "title": "Potential NULL pointer dereference from getenv"},
            {"category": "boundary", "cwe": "CWE-193", "rule_id": "arrayIndexOutOfBounds", "line_hint": 31, "title": "Off-by-one boundary error in loop condition"},
            {"category": "resource", "cwe": "CWE-404", "rule_id": "resourceLeak", "line_hint": 38, "title": "Unclosed FILE pointer leak"},
            {"category": "performance", "cwe": "CWE-400", "rule_id": "performance", "line_hint": 43, "title": "Inefficient string concatenation copies in loop"},
            {"category": "syntax", "cwe": "CWE-670", "rule_id": "empty-statement", "line_hint": 105, "title": "Misplaced semicolon after conditional empty statement"}
        ],
        "code": '''/* WARNING: INTENTIONALLY VULNERABLE BENCHMARK SAMPLE - FOR TESTING & AUDIT ONLY */
/* PR Agent Multi-Language Benchmark Suite */

#include <iostream>
#include <cstring>
#include <cstdlib>
#include <vector>

void process_packet(const char* packet_data, int size) {
    // Syntax / Logic Hazard: Misplaced semicolon after conditional (CWE-670 / empty-statement)
    if (size < 0);

    // Security: Buffer Overflow with unsafe strcpy (CWE-120, CWE-787)
    char buffer[64];
    strcpy(buffer, packet_data);
    
    // Security: Hardcoded sensitive master key (CWE-798)
    const char* MASTER_KEY = "PROD_SECRET_KEY_Cpp_8832";
    
    // Resource: Memory leak - heap allocated without free/delete (CWE-401)
    int* session_id = (int*)malloc(sizeof(int));
    *session_id = rand();
    
    // Runtime Bug: Potential NULL pointer dereference (CWE-476)
    char* token = getenv("AUTH_TOKEN");
    if (strlen(token) > 0) {
        std::cout << "Token active: " << token << std::endl;
    }
    
    // Boundary Bug: Off-by-one error in loop condition (CWE-193)
    int values[10];
    for (int i = 0; i <= 10; ++i) {
        values[i] = i * 2;
    }
    
    // Resource: Unclosed file pointer leak (CWE-404)
    FILE* fp = fopen("/tmp/packet.log", "w");
    if (fp) {
        fputs(buffer, fp);
        // Missing fclose(fp)
    }
    
    // Performance: Inefficient repeated string allocation in loop (CWE-400)
    std::string report = "";
    for (int j = 0; j < 500; ++j) {
        report = report + std::string(packet_data);
    }
}
'''
    },
    "c": {
        "filename": "firmware_auth.c",
        "language": "c",
        "tools": ["cppcheck"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "boundary", "runtime", "resource", "performance", "syntax"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-120", "rule_id": "buffer-overflow", "line_hint": 14, "title": "Buffer overflow with unsafe sprintf"},
            {"category": "security", "cwe": "CWE-798", "rule_id": "hardcoded-credentials", "line_hint": 17, "title": "Hardcoded firmware device key"},
            {"category": "runtime", "cwe": "CWE-457", "rule_id": "uninitvar", "line_hint": 20, "title": "Uninitialized pointer dereference"},
            {"category": "runtime", "cwe": "CWE-369", "rule_id": "zerodiv", "line_hint": 26, "title": "Division by zero with unguarded sample_rate"},
            {"category": "boundary", "cwe": "CWE-119", "rule_id": "arrayIndexOutOfBounds", "line_hint": 30, "title": "Array index out of bounds write on boundary"},
            {"category": "resource", "cwe": "CWE-401", "rule_id": "memleak", "line_hint": 34, "title": "Memory leak: allocated token never freed"},
            {"category": "performance", "cwe": "CWE-400", "rule_id": "performance", "line_hint": 39, "title": "Repeated strlen in loop condition"},
            {"category": "syntax", "cwe": "CWE-783", "rule_id": "macro-parentheses", "line_hint": 160, "title": "Unparenthesized macro expansion operator precedence hazard"}
        ],
        "code": '''/* WARNING: INTENTIONALLY VULNERABLE BENCHMARK SAMPLE - FOR TESTING & AUDIT ONLY */
/* PR Agent Multi-Language Benchmark Suite */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

// Syntax / Preprocessor Hazard: Unparenthesized macro parameter hazard (CWE-783)
#define CALC_BUFFER(x) x * 16

int authenticate_user(char* input_pin, int sample_rate) {
    // Security: Buffer overflow with unsafe sprintf (CWE-120, CWE-242)
    char stored_hash[16];
    char pin_buffer[16];
    sprintf(pin_buffer, input_pin);
    
    // Security: Hardcoded credential (CWE-798)
    char* master_key = "HARDCODED_DEVICE_KEY_2026";
    
    // Runtime Bug: Uninitialized pointer dereference (CWE-457)
    int* status_code;
    if (*status_code == 1) {
        return 1;
    }
    
    // Runtime Bug: Division by zero risk (CWE-369)
    int rate_factor = 1000 / sample_rate;
    
    // Boundary Bug: Array index out of bounds write (CWE-119, CWE-787)
    int calibration_matrix[8];
    calibration_matrix[8] = 0xFF;
    
    // Resource: Memory leak without free (CWE-401)
    char* session_token = (char*)malloc(128);
    strcpy(session_token, master_key);
    
    // Performance: Repeated strlen evaluation in loop condition (CWE-400)
    int check_sum = 0;
    for (int i = 0; i < strlen(pin_buffer); i++) {
        check_sum += pin_buffer[i];
    }
    
    return check_sum + rate_factor;
}
'''
    },
    "java": {
        "filename": "UserPaymentService.java",
        "language": "java",
        "tools": ["checkstyle"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "boundary", "runtime", "resource", "performance", "syntax"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-798", "rule_id": "hardcoded-credentials", "line_hint": 14, "title": "Hardcoded database credential"},
            {"category": "security", "cwe": "CWE-89", "rule_id": "sql-injection", "line_hint": 22, "title": "SQL Injection via string concatenation"},
            {"category": "security", "cwe": "CWE-22", "rule_id": "path-traversal", "line_hint": 26, "title": "Path Traversal in receipt file access"},
            {"category": "resource", "cwe": "CWE-404", "rule_id": "resource-leak", "line_hint": 29, "title": "Unclosed FileInputStream without try-with-resources"},
            {"category": "runtime", "cwe": "CWE-369", "rule_id": "division-by-zero", "line_hint": 33, "title": "Division by zero risk on splitCount"},
            {"category": "boundary", "cwe": "CWE-129", "rule_id": "array-bounds", "line_hint": 37, "title": "Array index out of bounds access without length check"},
            {"category": "performance", "cwe": "CWE-400", "rule_id": "string-concat", "line_hint": 41, "title": "Inefficient String concatenation in loop"},
            {"category": "syntax", "cwe": "CWE-390", "rule_id": "EmptyBlock", "line_hint": 45, "title": "Empty catch block suppressing critical exception"}
        ],
        "code": '''/* WARNING: INTENTIONALLY VULNERABLE BENCHMARK SAMPLE - FOR TESTING & AUDIT ONLY */
/* PR Agent Multi-Language Benchmark Suite */

package com.pragent.billing;

import java.io.*;
import java.sql.*;

public class UserPaymentService {
    // Security: Hardcoded secret (CWE-798)
    private static final String DB_SECRET = "sk_live_994821aBcDeFgHiJkLmNoP";

    public void processPayment(String accountId, String amount, int splitCount) {
        Connection conn = null;
        try {
            conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/billing", "root", DB_SECRET);
            // Security: SQL Injection via string concat (CWE-89, OWASP A03:2021)
            Statement stmt = conn.createStatement();
            String sql = "UPDATE accounts SET balance = balance + " + amount + " WHERE id = '" + accountId + "'";
            stmt.executeUpdate(sql);
            
            // Security: Path Traversal (CWE-22)
            File receiptFile = new File("receipts/" + accountId + ".pdf");
            
            // Resource: Resource Leak (FileInputStream not closed in try-with-resources, CWE-404)
            FileInputStream fis = new FileInputStream(receiptFile);
            fis.read();
            
            // Runtime: Division by zero risk (CWE-369)
            int splitShare = 100 / splitCount;
            
            // Boundary: Array index boundary without length check (CWE-129)
            String[] parts = accountId.split("-");
            String region = parts[5];
            
            // Performance: Inefficient String concatenation in loop (CWE-400)
            String logSummary = "";
            for (int i = 0; i < 500; i++) {
                logSummary += "EVENT:" + i + ";";
            }
        } catch (Exception e) {
            // Bug: Empty catch block hiding critical failure (Checkstyle EmptyBlock, CWE-390)
        }
    }
}
'''
    },
    "javascript": {
        "filename": "server_route.js",
        "language": "javascript",
        "tools": ["eslint"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "boundary", "runtime", "resource", "performance", "syntax"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-798", "rule_id": "no-secrets", "line_hint": 11, "title": "Hardcoded JWT secret"},
            {"category": "security", "cwe": "CWE-95", "rule_id": "no-eval", "line_hint": 16, "title": "Direct dynamic code execution with eval"},
            {"category": "security", "cwe": "CWE-79", "rule_id": "xss", "line_hint": 19, "title": "Reflected Cross-Site Scripting (XSS)"},
            {"category": "security", "cwe": "CWE-1321", "rule_id": "prototype-pollution", "line_hint": 25, "title": "Prototype pollution vulnerability"},
            {"category": "style", "cwe": "CWE-697", "rule_id": "eqeqeq", "line_hint": 31, "title": "Loose equality comparison (eqeqeq)"},
            {"category": "resource", "cwe": "CWE-404", "rule_id": "resource-leak", "line_hint": 35, "title": "Unclosed file descriptor leak"},
            {"category": "boundary", "cwe": "CWE-193", "rule_id": "array-bounds", "line_hint": 40, "title": "Array boundary off-by-one accessing items[length]"},
            {"category": "runtime", "cwe": "CWE-369", "rule_id": "division-by-zero", "line_hint": 41, "title": "Division by zero when array is empty"},
            {"category": "performance", "cwe": "CWE-400", "rule_id": "blocking-io", "line_hint": 44, "title": "Synchronous blocking readFileSync in high-frequency route"}
        ],
        "code": '''/* WARNING: INTENTIONALLY VULNERABLE BENCHMARK SAMPLE - FOR TESTING & AUDIT ONLY */
/* PR Agent Multi-Language Benchmark Suite */

const express = require('express');
const fs = require('fs');
const app = express();

// Security: Hardcoded JWT secret (CWE-798)
const JWT_SECRET = "super_secret_jwt_key_12345";

app.post('/eval-rule', (req, res) => {
    const userCode = req.body.formula;
    // Security: Direct code execution with eval (ESLint: no-eval, CWE-95)
    const result = eval(userCode);
    
    // Security: Reflected Cross-Site Scripting (XSS, CWE-79, OWASP A03:2021)
    res.send("<div>Calculation Result: " + req.query.comment + "</div>");
});

app.post('/update-settings', (req, res) => {
    // Security: Prototype Pollution vulnerability (CWE-1321)
    const target = {};
    const payload = JSON.parse(req.body.data);
    for (let key in payload) {
        target[key] = payload[key];
    }
    
    // Style & Bug: Loose equality comparison (ESLint: eqeqeq)
    if (payload.priority == "1") {
        console.log("High priority update");
    }
    
    // Resource: Unclosed file descriptor resource leak (CWE-404)
    const fd = fs.openSync('/tmp/settings.json', 'w');
    fs.writeSync(fd, JSON.stringify(target));
    // Missing fs.closeSync(fd)
    
    // Boundary & Runtime: Accessing out-of-bounds array element & division by zero
    const items = payload.items || [];
    const lastItem = items[items.length]; // Boundary: items.length is out of bounds
    const avgRatio = 100 / items.length; // Runtime: division by zero if items is empty
    
    // Performance: Synchronous blocking file read in high-frequency route (CWE-400)
    const rawCache = fs.readFileSync('/tmp/config.json', 'utf8');
    
    res.json({ status: "ok", lastItem, avgRatio });
});
'''
    },
    "ruby": {
        "filename": "report_generator.rb",
        "language": "ruby",
        "tools": ["rubocop"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "boundary", "runtime", "resource", "performance", "syntax"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-798", "rule_id": "Security/HardcodedSecret", "line_hint": 10, "title": "Hardcoded production API key"},
            {"category": "security", "cwe": "CWE-89", "rule_id": "Security/SqlInjection", "line_hint": 17, "title": "SQL Injection via string interpolation"},
            {"category": "security", "cwe": "CWE-78", "rule_id": "Security/CommandInjection", "line_hint": 22, "title": "Command injection via backticks"},
            {"category": "security", "cwe": "CWE-502", "rule_id": "Security/MarshalLoad", "line_hint": 26, "title": "Insecure deserialization with Marshal.load"},
            {"category": "resource", "cwe": "CWE-404", "rule_id": "resource-leak", "line_hint": 30, "title": "Unclosed file handle leak"},
            {"category": "runtime", "cwe": "CWE-369", "rule_id": "division-by-zero", "line_hint": 35, "title": "ZeroDivisionError on empty total_records"},
            {"category": "boundary", "cwe": "CWE-193", "rule_id": "array-bounds", "line_hint": 38, "title": "Array boundary off-by-one accessing results[length]"},
            {"category": "performance", "cwe": "CWE-400", "rule_id": "performance", "line_hint": 41, "title": "Inefficient string concatenation in loop"},
            {"category": "syntax", "cwe": "CWE-390", "rule_id": "Lint/SuppressedException", "line_hint": 367, "title": "Suppressed exception in empty rescue block"}
        ],
        "code": '''# WARNING: INTENTIONALLY VULNERABLE BENCHMARK SAMPLE - FOR TESTING & AUDIT ONLY
# PR Agent Multi-Language Benchmark Suite

require 'sqlite3'

class ReportGenerator
  # Security: Hardcoded credential (CWE-798)
  API_KEY = "RB_SEC_PROD_993848123"

  def generate_monthly_report(table_name, user_input, total_records)
    db = SQLite3::Database.new "production.db"
    
    # Syntax / Lint Hazard: Suppressed exception in empty rescue block (CWE-390)
    begin; db.execute("PRAGMA quick_check"); rescue; end

    # Security: SQL Injection via string interpolation (CWE-89)
    query = "SELECT * FROM #{table_name} WHERE status = '#{user_input}'"
    results = db.execute(query)
    
    # Security: Command injection via backticks (RuboCop: Security/CommandInjection, CWE-78)
    filename = "report_#{user_input}.pdf"
    `wkhtmltopdf index.html #{filename}`
    
    # Security: Insecure deserialization with Marshal.load (RuboCop: Security/MarshalLoad, CWE-502)
    cached_data = File.read("cache.bin")
    deserialized = Marshal.load(cached_data)
    
    # Resource: Unclosed file handle leak (CWE-404)
    log_file = File.open("report.log", "a")
    log_file.puts("Report generated for: #{user_input}")
    # Missing log_file.close
    
    # Runtime: Division by zero risk (CWE-369)
    avg_per_record = 100 / total_records
    
    # Boundary: Array index boundary access without checking length (CWE-193)
    first_item = results[results.length]
    
    # Performance: Inefficient string concatenation in loop (CWE-400)
    summary = ""
    results.each do |row|
      summary += row.to_s + "\\n"
    end
    
    return results
  end
end
'''
    },
    "typescript": {
        "filename": "order_processor.ts",
        "language": "typescript",
        "tools": ["eslint"],
        "is_intentionally_vulnerable": True,
        "defect_categories": ["security", "boundary", "runtime", "resource", "performance", "syntax"],
        "expected_defects": [
            {"category": "security", "cwe": "CWE-798", "rule_id": "no-secrets", "line_hint": 14, "title": "Hardcoded Stripe private API secret key"},
            {"category": "security", "cwe": "CWE-95", "rule_id": "no-eval", "line_hint": 22, "title": "Direct eval execution of untrusted discount rule formula"},
            {"category": "runtime", "cwe": "CWE-369", "rule_id": "division-by-zero", "line_hint": 27, "title": "Division by zero when order item count is zero"},
            {"category": "boundary", "cwe": "CWE-193", "rule_id": "array-bounds", "line_hint": 31, "title": "Array boundary off-by-one accessing items[length]"},
            {"category": "resource", "cwe": "CWE-404", "rule_id": "resource-leak", "line_hint": 36, "title": "Unclosed file descriptor leak"},
            {"category": "performance", "cwe": "CWE-400", "rule_id": "blocking-io", "line_hint": 41, "title": "Synchronous blocking readFileSync inside transaction loop"},
            {"category": "syntax", "cwe": "CWE-390", "rule_id": "no-empty", "line_hint": 46, "title": "Empty catch block suppressing critical runtime exception"}
        ],
        "code": '''/* WARNING: INTENTIONALLY VULNERABLE BENCHMARK SAMPLE - FOR TESTING & AUDIT ONLY */
/* PR Agent Multi-Language Benchmark Suite */

import * as fs from 'fs';

interface OrderItem {
    id: string;
    price: number;
    qty: number;
}

export class OrderProcessor {
    // Security: Hardcoded Stripe private secret key (CWE-798)
    private readonly stripeKey: string = "sk_live_9941920_SECRET_KEY_PROD";

    public calculateDiscount(formula: string, items: OrderItem[]): number {
        // Security: Direct dynamic code evaluation with eval (ESLint: no-eval, CWE-95)
        const discountRate: any = eval(formula);

        // Runtime: Division by zero risk if order items array is empty (CWE-369)
        const avgPrice = 100 / items.length;

        // Boundary: Array boundary off-by-one accessing items[length] (CWE-193)
        const boundaryItem = items[items.length];

        // Resource: Unclosed file descriptor resource leak (CWE-404)
        const fd = fs.openSync('/tmp/order.log', 'a');
        fs.writeSync(fd, `Processed ${items.length} items\\n`);
        // Missing fs.closeSync(fd)

        // Performance: Synchronous blocking file read in high-frequency path (CWE-400)
        const syncConfig = fs.readFileSync('/tmp/config.json', 'utf8');

        try {
            // Syntax / Lint Hazard: Empty catch block hiding failures (CWE-390, no-empty)
            JSON.parse(syncConfig);
        } catch (e) {
            // Suppressed error
        }

        return Number(discountRate) + avgPrice;
    }
}
'''
    }
}
