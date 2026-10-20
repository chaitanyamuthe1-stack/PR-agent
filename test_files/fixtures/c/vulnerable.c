/* Vulnerable C test fixture for static analysis verification (Cppcheck) */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Hardcoded credentials (CWE-798) */
const char* FIRMWARE_KEY = "HARDCODED_ROOT_KEY_998811";

void authenticate_device(const char* input) {
    char local_buffer[16];
    /* Unbounded strcpy buffer overflow (CWE-120) */
    strcpy(local_buffer, input);

    /* Unclosed resource leak (CWE-404) */
    FILE* fp = fopen("device.log", "w");
    if (fp) {
        fputs(local_buffer, fp);
    }
}
