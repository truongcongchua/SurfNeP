#include <arpa/inet.h>
#include <math.h>
#include <stdint.h>
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
    // TODO: lặp: đọc 4 dòng (MSSV, họ tên, ngày sinh, điểm); bỏ '\n' cuối mỗi dòng; EOF -> thoát
    // TODO: ghép bản ghi vào mảng unsigned char (htonl/htons), send một lần
    // TODO: đọc một dòng phản hồi, in ra stdout rồi fflush; "ERROR" -> dừng
    return 0;
}
