// Lời giải mẫu theo code mẫu 3-Chap3/L1-NonBlocking/non_blocking_server.c
// (sửa: client đã đóng phải được xoá khỏi mảng).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/ioctl.h>

#define MAX_CLIENTS 512

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
    if (listen(listener, 64) == -1) {
        perror("listen() failed");
        return 1;
    }

    int io_mode = 1;
    ioctl(listener, FIONBIO, &io_mode);  // accept không chặn nữa

    char buffer[1024];
    int client_sockets[MAX_CLIENTS];
    int num_clients = 0;
    while (0 == 0) {
        int client = accept(listener, NULL, NULL);
        if (client != -1) {
            if (num_clients < MAX_CLIENTS) {
                ioctl(client, FIONBIO, &io_mode);  // recv không chặn nữa
                client_sockets[num_clients++] = client;
            } else {
                close(client);
            }
        }
        for (int i = 0; i < num_clients; i++) {
            int byte_received = recv(client_sockets[i], buffer, sizeof(buffer), 0);
            if (byte_received > 0) {
                send(client_sockets[i], buffer, byte_received, 0);
            } else if (byte_received == 0) {
                // Client đóng: close và xoá khỏi mảng (đưa phần tử cuối lên chỗ i)
                close(client_sockets[i]);
                client_sockets[i] = client_sockets[num_clients - 1];
                num_clients--;
                i--;
            }
            // byte_received == -1: chưa có dữ liệu, thử client tiếp theo
        }
    }
}
