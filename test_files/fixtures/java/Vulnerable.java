// Vulnerable Java test fixture for static analysis verification (Checkstyle)
package com.pragent.review;

import java.io.FileInputStream;

public class Vulnerable {
    // Hardcoded secret (CWE-798)
    private static final String API_SECRET = "sk_live_99881122334455667788";

    public void processData(String filePath, String status) {
        // String comparison using == instead of .equals() (CWE-595)
        if (status == "VIP") {
            System.out.println("VIP user access");
        }

        // Unclosed resource descriptor leak without try-with-resources (CWE-404)
        try {
            FileInputStream fis = new FileInputStream(filePath);
            fis.read();
        } catch (Exception e) {
            // Empty catch block swallowing exception silently (CWE-390)
        }
    }
}
