// SAI có chủ đích: dùng s_addr trực tiếp (thứ tự mạng) để in và so mặt nạ.
#include <arpa/inet.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    char line[256];
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\r\n")] = 0;
        struct in_addr in;
        if (inet_pton(AF_INET, line, &in) != 1) { puts("INVALID"); continue; }
        uint32_t a = in.s_addr;
        const char *k = (a & 0xFF000000u) == 0x7F000000u ? "LOOPBACK"
                      : (a & 0xFF000000u) == 0x0A000000u ? "PRIVATE" : "PUBLIC";
        printf("VALID %s 0x%08X %s\n", line, a, k);
    }
    return 0;
}
