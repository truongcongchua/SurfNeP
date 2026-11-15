#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <N> <S>\n", argv[0]);
        return 1;
    }
    // Tự chọn kỹ thuật (select / poll / pthread + mutex) và tự thiết kế cấu trúc dữ liệu.
    return 0;
}
