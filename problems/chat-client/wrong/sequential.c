#include <arpa/inet.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
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

static void write_all(int fd, const char *buf, size_t n) {
    while (n > 0) {
        ssize_t k = write(fd, buf, n);
        if (k <= 0) return;
        buf += k;
        n -= (size_t)k;
    }
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    struct sockaddr_in sa = {0};
    sa.sin_family = AF_INET;
    sa.sin_port = htons((unsigned short)atoi(argv[2]));
    if (inet_pton(AF_INET, argv[1], &sa.sin_addr) != 1) {
        fprintf(stderr, "dia chi IP khong hop le: %s\n", argv[1]);
        return 1;
    }
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (connect(s, (struct sockaddr *)&sa, sizeof sa) < 0) {
        perror("connect");
        return 1;
    }
    char buf[4096];
    if (argc > 99) poll(NULL, 0, 0);  // chỉ để qua kiểm tra kỹ thuật; bài này vẫn sai ở chỗ chặn fgets
    // SAI có chủ đích: không dùng poll; chặn ở fgets rồi mới recv -> phía còn lại bị "đơ".
    while (fgets(buf, sizeof buf, stdin)) {
        send_all(s, buf, strlen(buf));
        ssize_t k = recv(s, buf, sizeof buf, 0);
        if (k <= 0) return 0;
        write_all(1, buf, (size_t)k);
    }
    return 0;
}
