#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

// Gửi đủ n byte (send() có thể gửi thiếu). Trả về 0 nếu thành công, -1 nếu lỗi.
static int send_all(int fd, const char *buf, size_t n) {
    // TODO
    (void)fd; (void)buf; (void)n;
    return -1;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: vòng lặp accept; với mỗi client: recv -> send_all cho đến khi recv trả về 0
    (void)send_all;
    return 0;
}
