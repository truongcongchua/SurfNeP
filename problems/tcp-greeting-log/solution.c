// Lời giải mẫu: server lặp như tcp_server.c; đọc câu chào bằng open/read, ghi log bằng open(O_APPEND)/write (lab08).
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    if (argc != 4) {
        printf("Usage: %s <port> <greeting_file> <log_file>\n", argv[0]);
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

    char buffer[4096];
    while (0 == 0) {
        int client = accept(listener, NULL, NULL);
        if (client == -1) continue;

        // 1. Gửi câu chào: mở lại tệp mỗi lần, gửi đúng số byte read trả về (có thể có 0x00).
        int gfd = open(argv[2], O_RDONLY);
        if (gfd != -1) {
            int bytes_read;
            while ((bytes_read = read(gfd, buffer, sizeof(buffer))) > 0) {
                send(client, buffer, bytes_read, 0);
            }
            close(gfd);
        }

        // 2. Ghi nối tiếp (O_APPEND) mọi dữ liệu client gửi vào tệp log; write đưa dữ liệu vào tệp ngay.
        int lfd = open(argv[3], O_WRONLY | O_CREAT | O_APPEND, 0644);
        while (0 == 0) {
            int bytes_received = recv(client, buffer, sizeof(buffer), 0);
            if (bytes_received <= 0) break;
            if (lfd != -1) write(lfd, buffer, bytes_received);
        }
        if (lfd != -1) close(lfd);
        close(client);
    }
}
