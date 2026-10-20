// Clean Java test fixture (Phase 6 verification)
package com.pragent.review;

import java.io.FileInputStream;
import java.io.IOException;

public class Clean {
    public void processFile(String path) {
        // Safe try-with-resources resource management (CWE-404 safe)
        try (FileInputStream fis = new FileInputStream(path)) {
            int data = fis.read();
            System.out.println("Read byte: " + data);
        } catch (IOException e) {
            System.err.println("IO Error handled: " + e.getMessage());
        }
    }

    public boolean compareStatus(String status) {
        // Safe string value comparison (.equals)
        return "ACTIVE".equals(status);
    }
}
