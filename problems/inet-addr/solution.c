#include <arpa/inet.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static const char *kind(uint32_t a) {
    if ((a & 0xFF000000u) == 0x7F000000u) return "LOOPBACK";
    if ((a & 0xFF000000u) == 0x0A000000u || (a & 0xFFF00000u) == 0xAC100000u ||
        (a & 0xFFFF0000u) == 0xC0A80000u)
        return "PRIVATE";
    if (a == 0 || a == 0xFFFFFFFFu) return "SPECIAL";
    return "PUBLIC";
}

int main(void) {
    char line[256];
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\r\n")] = 0;
        struct in_addr in;
        if (inet_pton(AF_INET, line, &in) != 1) {
            puts("INVALID");
            continue;
        }
        char text[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &in, text, sizeof text);
        uint32_t host = ntohl(in.s_addr);
        printf("VALID %s 0x%08X %s\n", text, host, kind(host));
    }
    return 0;
}
