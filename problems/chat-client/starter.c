#include <arpa/inet.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket + connect (lỗi -> stderr + return 1)
    // TODO: struct pollfd fds[2] = { {0 (stdin), POLLIN}, {sock, POLLIN} };
    // TODO: vòng lặp poll():
    //   - stdin sẵn sàng: read -> send cho server; read trả 0 (EOF) -> shutdown(SHUT_WR), ngừng theo dõi stdin
    //   - socket sẵn sàng: recv -> write(1, ...) ngay; recv trả 0 -> return 0
    return 0;
}
