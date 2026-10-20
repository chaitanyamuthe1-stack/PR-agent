/**
 * Comprehensive C++ Test File with 10 Intentional Bugs
 * Designed for PR Agent Benchmarking
 *
 * Bugs included:
 * 1. Security: Buffer Overflow via unsafe strcpy into fixed buffer (CWE-120)
 * 2. Security: Hardcoded production secret token (CWE-798)
 * 3. Resource Leak: Heap memory leak via raw malloc without free (CWE-401)
 * 4. Logic / Memory: Potential NULL pointer dereference on getenv return (CWE-476)
 * 5. Logic: Off-by-one array index boundary error in loop condition (CWE-193)
 * 6. Runtime Bug: Uninitialized pointer variable dereferenced (CWE-457)
 * 7. Resource Leak: File opened with fopen() without matching fclose() (CWE-404)
 * 8. Security: Insecure random number generator rand() used for auth token (CWE-338)
 * 9. Performance: Passing large std::vector by value instead of const reference (CWE-1078)
 * 10. Security / Memory: Use-after-free pattern accessing deallocated memory (CWE-416)
 */

#include <iostream>
#include <vector>
#include <cstring>
#include <cstdlib>
#include <cstdio>

// 2. Security: Hardcoded credential (CWE-798)
const char* API_KEY = "HARDCODED_PROD_JWT_SECRET_2026";

// 9. Performance: Passing large vector by value instead of const reference (CWE-1078)
void process_telemetry(std::vector<int> data_points) {
    int sum = 0;
    for (int v : data_points) {
        sum += v;
    }
    std::cout << "Sum: " << sum << std::endl;
}

void process_network_packet(const char* packet_data, int size) {
    // 1. Security: Buffer Overflow with unsafe strcpy (CWE-120)
    char buffer[64];
    strcpy(buffer, packet_data);

    // 3. Resource Leak: Memory leak - heap allocated without free (CWE-401)
    int* session_id = (int*)malloc(sizeof(int));
    *session_id = 42;

    // 4. Logic / Memory: NULL pointer dereference on getenv return (CWE-476)
    char* token = getenv("AUTH_TOKEN");
    if (strlen(token) > 0) {
        std::cout << "Authenticated" << std::endl;
    }

    // 5. Logic: Off-by-one error in loop condition (CWE-193)
    int values[10];
    for (int i = 0; i <= 10; ++i) {
        values[i] = i * 2;
    }

    // 6. Runtime: Uninitialized pointer dereferenced (CWE-457)
    int* status_code;
    if (*status_code == 1) {
        std::cout << "Active status" << std::endl;
    }

    // 7. Resource Leak: Unclosed file opened with fopen (CWE-404)
    FILE* log_fp = fopen("packet_log.txt", "w");
    if (log_fp) {
        fputs("Packet processed\n", log_fp);
    }

    // 8. Security: Insecure random number generator for session token (CWE-338)
    int session_token = rand();
    std::cout << "Token: " << session_token << std::endl;

    // 10. Security / Memory: Use-after-free pattern (CWE-416)
    char* temp_buf = (char*)malloc(32);
    free(temp_buf);
    *temp_buf = 'A';
}
