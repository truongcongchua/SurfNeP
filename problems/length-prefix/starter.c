#include <arpa/inet.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_LEN 65536

// Nhận đủ n byte. Trả về 0 nếu đủ, -1 nếu lỗi hoặc đối phương đóng giữa chừng.
static int recv_exact(int fd, void *buf, size_t n) {
    // TODO
    (void)fd; (void)buf; (void)n;
    return -1;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen; vòng lặp accept
    // TODO: mỗi client: đọc 4 byte độ dài (ntohl), đọc L byte, đổi chữ hoa, gửi lại cùng định dạng
    (void)recv_exact;
    return 0;
}
