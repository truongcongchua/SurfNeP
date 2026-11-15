#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

// Gợi ý cấu trúc dữ liệu — có thể đổi tuỳ kỹ thuật bạn chọn (select / poll / pthread).
#define BUF_SIZE 4096
#define MAX_KEYS 1000
#define KLEN 65

typedef struct { int fd; char buf[BUF_SIZE]; size_t len; } Client;
typedef struct { char key[KLEN], val[KLEN]; } Entry;

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <N>\n", argv[0]);
        return 1;
    }
    int limit = atoi(argv[2]);
    (void)limit;
    // TODO: socket lắng nghe; WELCOME / FULL theo giới hạn N
    // TODO: ghép dòng cho từng client; xử lý SET / GET / DEL / COUNT / QUIT
    return 0;
}
