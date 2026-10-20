/* Clean C test fixture (Phase 6 verification) */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void safe_copy_and_compute(const char* src, int count) {
    char dest[64];
    /* Safe bounded copy with null termination (CWE-120 safe) */
    strncpy(dest, src, sizeof(dest) - 1);
    dest[sizeof(dest) - 1] = '\0';

    /* Guarded division (CWE-369 safe) */
    int ratio = (count > 0) ? (100 / count) : 0;
    printf("Processed %s with ratio %d\n", dest, ratio);
}
