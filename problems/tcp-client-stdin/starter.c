#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    // TODO: inet_pton địa chỉ, socket, connect (lỗi -> stderr + return 1)
    // TODO: đọc stdin, gửi ngay từng phần đọc được; EOF -> close + return 0
    return 0;
}
