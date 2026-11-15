#include <arpa/inet.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_LEN 65536

static int recv_exact(int fd, void *buf, size_t n) {
    char *p = buf;
    while (n > 0) {
        ssize_t k = recv(fd, p, n, 0);
        if (k <= 0) return -1;
        p += k;
        n -= (size_t)k;
    }
    return 0;
}

static int send_all(int fd, const void *buf, size_t n) {
    const char *p = buf;
    while (n > 0) {
        ssize_t k = send(fd, p, n, MSG_NOSIGNAL);
        if (k <= 0) return -1;
        p += k;
        n -= (size_t)k;
    }
    return 0;
}

static void serve(int c) {
    static unsigned char data[MAX_LEN];
    for (;;) {
        uint32_t netlen;
        if (recv_exact(c, &netlen, 4) < 0) return;
        uint32_t len = ntohl(netlen);
        if (len > MAX_LEN) return;
        if (recv_exact(c, data, len) < 0) return;
        for (uint32_t i = 0; i < len; i++)
            if (data[i] >= 'a' && data[i] <= 'z') data[i] -= 32;
        if (send_all(c, &netlen, 4) < 0 || send_all(c, data, len) < 0) return;
    }
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 5) < 0) {
        perror("bind/listen");
        return 1;
    }
    for (;;) {
        int c = accept(ls, NULL, NULL);
        if (c < 0) continue;
        serve(c);
        close(c);
    }
}
