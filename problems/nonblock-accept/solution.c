#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_CLIENTS 512

static void set_nonblock(int fd) {
    int on = 1;
    ioctl(fd, FIONBIO, &on);
}

// Gửi đủ n byte trên socket non-blocking (đợi một chút nếu bộ đệm gửi đầy).
static int send_all(int fd, const char *buf, size_t n) {
    while (n > 0) {
        ssize_t k = send(fd, buf, n, MSG_NOSIGNAL);
        if (k < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            usleep(500);
            continue;
        }
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
    set_nonblock(ls);
    int clients[MAX_CLIENTS], n = 0;
    for (;;) {
        int busy = 0;
        int c = accept(ls, NULL, NULL);
        if (c >= 0) {
            busy = 1;
            if (n < MAX_CLIENTS) {
                set_nonblock(c);
                clients[n++] = c;
            } else {
                close(c);
            }
        }
        for (int i = 0; i < n; i++) {
            char buf[8192];
            ssize_t k = recv(clients[i], buf, sizeof buf, 0);
            if (k > 0) {
                busy = 1;
                if (send_all(clients[i], buf, (size_t)k) == 0) continue;
            } else if (k < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
                continue;  // chưa có dữ liệu
            }
            close(clients[i]);  // k == 0 (client đóng) hoặc lỗi thật
            clients[i--] = clients[--n];
        }
        if (!busy) usleep(1000);
    }
}
