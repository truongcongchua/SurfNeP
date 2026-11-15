#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <questions_file> <N>\n", argv[0]);
        return 1;
    }
    // Tự thiết kế: đọc tệp câu hỏi, bảng người chơi theo (IP, cổng), xử lý từng datagram.
    return 0;
}
