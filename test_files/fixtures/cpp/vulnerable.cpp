// Vulnerable C++ test fixture for static analysis verification (Cppcheck)
#include <iostream>
#include <cstring>
#include <cstdlib>

void vulnerable_packet_processor(const char* packet_data, int count) {
    // 1. Buffer overflow via unsafe strcpy (CWE-120)
    char buffer[32];
    strcpy(buffer, packet_data);

    // 2. Memory leak: malloc without free (CWE-401)
    int* session_id = (int*)malloc(sizeof(int));
    *session_id = 999;

    // 3. Division by zero without guard check (CWE-369)
    int ratio = 100 / count;

    // 4. NULL pointer dereference risk from getenv (CWE-476)
    char* token = getenv("AUTH_TOKEN");
    if (strlen(token) > 0) {
        std::cout << "Active: " << token << ratio << std::endl;
    }
}
