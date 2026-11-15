#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    char name[512];
    while (fgets(name, sizeof name, stdin)) {
        name[strcspn(name, "\r\n")] = 0;
        if (!name[0]) continue;
        struct addrinfo hints = {0}, *res;
        hints.ai_family = AF_INET;
        hints.ai_socktype = SOCK_STREAM;
        printf("%s:", name);
        if (getaddrinfo(name, NULL, &hints, &res) != 0) {
            puts(" NOT_FOUND");
            continue;
        }
        for (struct addrinfo *p = res; p; p = p->ai_next) {
            char ip[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &((struct sockaddr_in *)p->ai_addr)->sin_addr, ip, sizeof ip);
            printf(" %s", ip);
        }
        putchar('\n');
        freeaddrinfo(res);
    }
    return 0;
}
