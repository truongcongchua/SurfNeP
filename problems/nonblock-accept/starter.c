#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>
#include <sys/ioctl.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: đặt non-blocking (ioctl FIONBIO); vòng lặp thử accept + thử recv từng client; usleep khi rảnh
    return 0;
}
