#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <stdint.h>
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
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: tạo socket lắng nghe
    // TODO: vòng lặp accept -> tìm ô trống (giữ mutex) -> pthread_create một luồng cho client
    // TODO: luồng: recv + ghép dòng; broadcast phải giữ mutex khi duyệt danh sách client
    return 0;
}
