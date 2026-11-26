// Lời giải mẫu: server lặp như tcp_server.c; mở log chế độ "ab" mỗi client.
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <port> <log_file>\n", argv[0]);
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
        FILE *log = fopen(argv[2], "ab");
        while (0 == 0) {
            int bytes_received = recv(client, buffer, sizeof(buffer), 0);
            if (bytes_received <= 0) break;
            if (log != NULL) fwrite(buffer, 1, bytes_received, log);
        }
        if (log != NULL) fclose(log);  // fclose đẩy dữ liệu xuống tệp ngay
        close(client);
    }
}
