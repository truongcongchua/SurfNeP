// Lời giải mẫu theo code mẫu 2-Chap2/tcp_server.c: thêm vòng lặp accept và vòng lặp recv/send.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    int listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    int opt = 1;
    setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(argv[1]));
    addr.sin_addr.s_addr = INADDR_ANY;
    if (bind(listener, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("bind() failed");
        return 1;
    }
    if (listen(listener, 5) == -1) {
        perror("listen() failed");
        return 1;
    }

    char buffer[1024];
    while (0 == 0) {
        int client = accept(listener, NULL, NULL);
        if (client == -1) {
            continue;
        }
        while (0 == 0) {
            int bytes_received = recv(client, buffer, sizeof(buffer), 0);
            if (bytes_received <= 0) {
                break;  // 0: client đã đóng; -1: lỗi
            }
            send(client, buffer, bytes_received, 0);  // gửi đúng số byte nhận được
        }
        close(client);
    }
}
