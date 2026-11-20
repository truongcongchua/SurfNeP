#include <arpa/inet.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void dump(const unsigned char *b, size_t n) {
    for (size_t i = 0; i < n; i++)
        printf(i ? " %02X" : "%02X", b[i]);
}

int main(void) {
    char line[256];
    while (fgets(line, sizeof line, stdin)) {
        char type[8], num[64], extra[8];
        int k = sscanf(line, "%7s %63s %7s", type, num, extra);
        if (k == 0 || k == EOF) continue;  // bỏ qua dòng trống
        char *end;
        errno = 0;
        unsigned long long v = strtoull(num, &end, 10);
        int numok = k == 2 && num[0] >= '0' && num[0] <= '9' && *end == 0 && errno == 0;
        if (numok && !strcmp(type, "u16") && v <= 0xFFFF) {
            uint16_t net = htons((uint16_t)v);
            unsigned char b[2];
            memcpy(b, &net, 2);
            dump(b, 2);
            printf(" | %u\n", (unsigned)net);
        } else if (numok && !strcmp(type, "u32") && v <= 0xFFFFFFFFULL) {
            uint32_t net = htonl((uint32_t)v);
            unsigned char b[4];
            memcpy(b, &net, 4);
            dump(b, 4);
            printf(" | %u\n", net);
        } else {
            puts("ERROR");
        }
    }
    return 0;
}
