#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

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
    if (argc != 3) {
        fprintf(stderr, "usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(argv[2]));
    if (inet_pton(AF_INET, argv[1], &addr.sin_addr) != 1) {
        fprintf(stderr, "dia chi IP khong hop le: %s\n", argv[1]);
        return 1;
    }
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (connect(s, (struct sockaddr *)&addr, sizeof addr) < 0) {
        perror("connect");
        return 1;
    }
    // read() trả về ngay khi có dữ liệu (mỗi dòng gõ vào), không đợi EOF.
    char buf[4096];
    ssize_t n;
    while ((n = read(STDIN_FILENO, buf, sizeof buf)) > 0)
        if (send_all(s, buf, (size_t)n) < 0) {
            perror("send");
            return 1;
        }
    close(s);
    return 0;
}
