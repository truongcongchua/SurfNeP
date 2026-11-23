// SAI có chủ đích: dùng s_addr trực tiếp (thứ tự mạng) để in và so mặt nạ.
#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>

int main(void) {
    char line[256];
    while (fgets(line, sizeof(line), stdin) != NULL) {
        line[strcspn(line, "\r\n")] = 0;
        struct in_addr in;
        in.s_addr = inet_addr(line);
        if (in.s_addr == INADDR_NONE && strcmp(line, "255.255.255.255") != 0) { printf("INVALID\n"); continue; }
        unsigned int a = in.s_addr;
        const char *k = (a & 0xFF000000u) == 0x7F000000u ? "LOOPBACK"
                      : (a & 0xFF000000u) == 0x0A000000u ? "PRIVATE" : "PUBLIC";
        printf("VALID %s 0x%08X %s\n", inet_ntoa(in), a, k);
    }
    return 0;
}
