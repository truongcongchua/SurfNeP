// Lời giải mẫu theo code mẫu 3-Chap3/L5-IOMultiPlexing/select_server.c.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/select.h>

#define MAX_CLIENTS 512

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    int listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    int opt = 1;
    setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(atoi(argv[1]));
    server_addr.sin_addr.s_addr = INADDR_ANY;
    if (bind(listener, (struct sockaddr *)&server_addr, sizeof(server_addr)) == -1) {
        perror("bind() failed");
        return 1;
    }
    if (listen(listener, 64) == -1) {
        perror("listen() failed");
        return 1;
    }

    fd_set read_fds;
    int client_list[MAX_CLIENTS];
    int number_of_clients = 0;
    char buffer[1024];
    while (1) {
        // select() ghi đè read_fds nên phải dựng lại mỗi vòng
        FD_ZERO(&read_fds);
        FD_SET(listener, &read_fds);
        int max_fd = listener;
        for (int i = 0; i < number_of_clients; i++) {
            FD_SET(client_list[i], &read_fds);
            if (client_list[i] > max_fd) max_fd = client_list[i];
        }
        int activity = select(max_fd + 1, &read_fds, NULL, NULL, NULL);
        if (activity < 0) {
            continue;
        }
        if (FD_ISSET(listener, &read_fds)) {
            int client_socket = accept(listener, NULL, NULL);
            if (client_socket >= 0 && number_of_clients < MAX_CLIENTS && client_socket < FD_SETSIZE) {
                client_list[number_of_clients] = client_socket;
                number_of_clients++;
            } else if (client_socket >= 0) {
                close(client_socket);
            }
        }
        for (int i = 0; i < number_of_clients; i++) {
            int client_socket = client_list[i];
            if (!FD_ISSET(client_socket, &read_fds)) continue;
            int bytes_received = recv(client_socket, buffer, sizeof(buffer), 0);
            if (bytes_received > 0) {
                send(client_socket, buffer, bytes_received, 0);
            } else {
                // 0: client đóng; -1: lỗi. Đóng socket và xoá khỏi danh sách
                // (đưa phần tử cuối vào chỗ trống, rồi xét lại vị trí i).
                close(client_socket);
                client_list[i] = client_list[number_of_clients - 1];
                number_of_clients--;
                i--;
            }
        }
    }
    return 0;
}
