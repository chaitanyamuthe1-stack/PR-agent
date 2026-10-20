package com.pragent.test;

/**
 * Comprehensive Java Test File with 10 Intentional Bugs
 * Designed for PR Agent Benchmarking
 *
 * Bugs included:
 * 1. Security: SQL Injection via string concatenation in SQL statement (CWE-89)
 * 2. Security: Hardcoded production credentials (CWE-798)
 * 3. Resource Leak: Unclosed FileInputStream without try-with-resources (CWE-404)
 * 4. Code Quality / Bug: Empty catch block silently swallowing exceptions (CWE-390)
 * 5. Runtime Bug: Null pointer dereference risk on unvalidated parameter (CWE-476)
 * 6. Concurrency: Shared static mutable state accessed without synchronization (CWE-362)
 * 7. Performance: String concatenation in loop creating quadratic heap allocations (CWE-1078)
 * 8. Logic Bug: Strings compared with reference equality '==' instead of .equals() (CWE-595)
 * 9. Security: Path traversal risk constructing File from untrusted parameter (CWE-22)
 * 10. Logic: Division by zero risk without denominator validation (CWE-369)
 */

import java.io.*;
import java.sql.*;

public class Test {

    // 2. Security: Hardcoded database credentials (CWE-798)
    private static final String DB_SECRET = "sk_live_994821aBcDeFgHiJkLmNoP";

    // 6. Concurrency: Unsynchronized static mutable state (CWE-362)
    private static int requestCount = 0;

    public void processAccount(String accountId, String amount, String statusType, String reportPath) {
        requestCount++;

        // 5. Runtime Bug: Null pointer risk on unvalidated parameter (CWE-476)
        int idLength = accountId.length();

        // 8. Logic Bug: String comparison with '==' instead of .equals() (CWE-595)
        if (statusType == "ACTIVE") {
            System.out.println("Processing active account: " + idLength);
        }

        // 9. Security: Path traversal via unvalidated File path (CWE-22)
        File reportFile = new File("/var/reports", reportPath);

        // 10. Logic: Division by zero risk (CWE-369)
        int items = 0;
        int rate = 100 / items;

        Connection conn = null;
        try {
            conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/billing", "root", DB_SECRET);

            // 1. Security: SQL Injection via string concatenation (CWE-89)
            Statement stmt = conn.createStatement();
            String sql = "UPDATE accounts SET balance = balance + " + amount + " WHERE id = '" + accountId + "'";
            stmt.executeUpdate(sql);

            // 3. Resource Leak: Unclosed FileInputStream (CWE-404)
            FileInputStream fis = new FileInputStream(reportFile);
            fis.read();

            // 7. Performance: String concatenation in loop (CWE-1078)
            String logBuffer = "";
            for (int i = 0; i < 100; i++) {
                logBuffer += "record_" + i + ";";
            }

        } catch (Exception e) {
            // 4. Code Quality / Bug: Empty catch block swallowing critical exception (CWE-390)
        }
    }
}
