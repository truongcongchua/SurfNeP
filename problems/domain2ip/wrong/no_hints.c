// SAI có chủ đích: không đặt hints -> mỗi IP lặp 3 lần (STREAM/DGRAM/RAW), lẫn cả IPv6.
#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    char name[512];
    while (fgets(name, sizeof name, stdin)) {
        name[strcspn(name, "\r\n")] = 0;
        if (!name[0]) continue;
        struct addrinfo *res;
        printf("%s:", name);
        if (getaddrinfo(name, NULL, NULL, &res) != 0) { puts(" NOT_FOUND"); continue; }
        for (struct addrinfo *p = res; p; p = p->ai_next) {
            char ip[64];
            if (p->ai_family == AF_INET)
                inet_ntop(AF_INET, &((struct sockaddr_in *)p->ai_addr)->sin_addr, ip, sizeof ip);
            else
                inet_ntop(AF_INET6, &((struct sockaddr_in6 *)p->ai_addr)->sin6_addr, ip, sizeof ip);
            printf(" %s", ip);
        }
        putchar('\n');
        freeaddrinfo(res);
    }
    return 0;
}
