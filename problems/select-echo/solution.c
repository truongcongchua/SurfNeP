#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_CLIENTS 512

static int send_all(int fd, const char *buf, size_t n) {
    while (n > 0) {
        ssize_t k = send(fd, buf, n, MSG_NOSIGNAL);
        if (k <= 0) return -1;
        buf += k;
        n -= (size_t)k;
    }
    return 0;
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
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 64) < 0) {
        perror("bind/listen");
        return 1;
    }
    int clients[MAX_CLIENTS], n = 0;
    for (;;) {
        fd_set rd;
        FD_ZERO(&rd);
        FD_SET(ls, &rd);
        int maxfd = ls;
        for (int i = 0; i < n; i++) {
            FD_SET(clients[i], &rd);
            if (clients[i] > maxfd) maxfd = clients[i];
        }
        if (select(maxfd + 1, &rd, NULL, NULL, NULL) < 0) continue;
        if (FD_ISSET(ls, &rd)) {
            int c = accept(ls, NULL, NULL);
            if (c >= 0 && n < MAX_CLIENTS && c < FD_SETSIZE) clients[n++] = c;
            else if (c >= 0) close(c);
        }
        for (int i = 0; i < n; i++) {
            if (!FD_ISSET(clients[i], &rd)) continue;
            char buf[8192];
            ssize_t k = recv(clients[i], buf, sizeof buf, 0);
            if (k <= 0 || send_all(clients[i], buf, (size_t)k) < 0) {
                close(clients[i]);
                clients[i--] = clients[--n];  // xoá bằng cách đưa phần tử cuối lên
            }
        }
    }
}
