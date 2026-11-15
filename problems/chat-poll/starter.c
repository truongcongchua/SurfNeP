#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_CLIENTS 64
#define BUF_SIZE 4096

typedef struct {
    int fd;              // -1 nếu ô trống
    char id[64];         // rỗng nếu chưa đăng ký
    char buf[BUF_SIZE];  // phần dòng chưa hoàn chỉnh của client này
    size_t len;
} Client;

static Client clients[MAX_CLIENTS];

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: tạo socket lắng nghe
    // TODO: mảng struct pollfd (phần tử 0 là socket lắng nghe), vòng lặp poll()
    // TODO: kiểm tra revents (POLLIN | POLLHUP | POLLERR), ghép dòng cho từng client
    return 0;
}
