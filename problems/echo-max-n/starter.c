#include <arpa/inet.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define BUF_SIZE 4096

// Gợi ý: mỗi client một bộ đệm dòng riêng. Có thể đổi sang select hoặc pthread tuỳ ý.
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; } Client;

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <N>\n", argv[0]);
        return 1;
    }
    int limit = atoi(argv[2]);
    (void)limit;
    // TODO: socket -> bind -> listen
    // TODO: accept: còn chỗ -> WELCOME, hết chỗ -> FULL rồi close
    // TODO: ghép dòng cho từng client; COUNT / QUIT / ECHO <dòng>
    return 0;
}
