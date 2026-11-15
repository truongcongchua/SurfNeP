#include <arpa/inet.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <greeting_file> <log_file>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: với mỗi client: gửi toàn bộ argv[2]; nhận dữ liệu và ghi NỐI TIẾP vào argv[3]
    return 0;
}
