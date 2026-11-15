#include <arpa/inet.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <log_file>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen; accept lấy cả địa chỉ client (inet_ntop)
    // TODO: đọc từng bản ghi theo đúng định dạng (recv_exact + ntohl/ntohs), kiểm tra hợp lệ
    // TODO: hợp lệ -> in + ghi log (strftime cho thời gian) + "OK\n"; không hợp lệ -> "ERROR\n" + đóng
    return 0;
}
