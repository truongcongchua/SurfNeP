// Lời giải mẫu: inet_addr / inet_ntoa như code mẫu 2-Chap2 (tcp_client.c, udp_receiver.c).
#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>

const char *kind(unsigned int a) {
    if ((a & 0xFF000000u) == 0x7F000000u) return "LOOPBACK";
    if ((a & 0xFF000000u) == 0x0A000000u || (a & 0xFFF00000u) == 0xAC100000u ||
        (a & 0xFFFF0000u) == 0xC0A80000u)
        return "PRIVATE";
    if (a == 0 || a == 0xFFFFFFFFu) return "SPECIAL";
    return "PUBLIC";
}

int main(void) {
    char line[256];
    while (fgets(line, sizeof(line), stdin) != NULL) {
        line[strcspn(line, "\r\n")] = 0;
        struct in_addr in;
        in.s_addr = inet_addr(line);
        // inet_addr trả INADDR_NONE (0xFFFFFFFF) khi xâu sai, nhưng "255.255.255.255" hợp lệ cũng cho
        // đúng giá trị đó, nên phải so riêng.
        if (in.s_addr == INADDR_NONE && strcmp(line, "255.255.255.255") != 0) {
            printf("INVALID\n");
            continue;
        }
        unsigned int host = ntohl(in.s_addr);  // s_addr theo thứ tự mạng
        printf("VALID %s 0x%08X %s\n", inet_ntoa(in), host, kind(host));
    }
    return 0;
}
