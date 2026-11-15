// SAI có chủ đích: in byte theo thứ tự của máy (quên htons/htonl).
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    char line[256], type[8];
    unsigned long v;
    while (fgets(line, sizeof line, stdin)) {
        if (sscanf(line, "%7s %lu", type, &v) != 2) { puts("ERROR"); continue; }
        if (!strcmp(type, "u16") && v <= 0xFFFF) {
            uint16_t x = (uint16_t)v; unsigned char *b = (unsigned char *)&x;
            printf("%02X %02X | %u\n", b[0], b[1], (unsigned)x);
        } else if (!strcmp(type, "u32")) {
            uint32_t x = (uint32_t)v; unsigned char *b = (unsigned char *)&x;
            printf("%02X %02X %02X %02X | %u\n", b[0], b[1], b[2], b[3], x);
        } else puts("ERROR");
    }
    return 0;
}
