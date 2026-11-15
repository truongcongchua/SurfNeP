#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(s, (struct sockaddr *)&addr, sizeof addr) < 0) {
        perror("bind");
        return 1;
    }
    char buf[65536];
    for (;;) {
        struct sockaddr_in from;
        socklen_t fl = sizeof from;
        ssize_t n = recvfrom(s, buf, sizeof buf, 0, (struct sockaddr *)&from, &fl);
        if (n < 0) continue;
        sendto(s, buf, (size_t)n, 0, (struct sockaddr *)&from, fl);
    }
}
