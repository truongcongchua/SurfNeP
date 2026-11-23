// SAI có chủ đích: in bằng stdio mà không fflush -> phần tin chưa có '\n' nằm lại trong bộ đệm, hiện quá muộn.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/select.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    int client_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(atoi(argv[2]));
    server_addr.sin_addr.s_addr = inet_addr(argv[1]);
    if (connect(client_socket, (struct sockaddr *)&server_addr, sizeof(server_addr)) == -1) {
        perror("connect");
        close(client_socket);
        exit(EXIT_FAILURE);
    }

    fd_set read_fds;
    char buffer[4096];
    while (1) {
        FD_ZERO(&read_fds);
        FD_SET(client_socket, &read_fds);
        FD_SET(STDIN_FILENO, &read_fds);
        int max_fd = (client_socket > STDIN_FILENO) ? client_socket : STDIN_FILENO;
        // timeout NULL: ngủ tới khi có dữ liệu (không lặp bận)
        int activity = select(max_fd + 1, &read_fds, NULL, NULL, NULL);
        if (activity < 0) {
            break;
        }
        // Xét socket trước: server đã đóng thì thoát ngay, không gửi thêm vào kết nối đã đóng.
        if (FD_ISSET(client_socket, &read_fds)) {
            int bytes_received = recv(client_socket, buffer, sizeof(buffer), 0);
            if (bytes_received <= 0) {
                break;  // 0: server đóng; -1: lỗi (ví dụ RST)
            }
            fwrite(buffer, 1, bytes_received, stdout);  // SAI: không fflush
        }
        if (FD_ISSET(STDIN_FILENO, &read_fds)) {
            int n = read(STDIN_FILENO, buffer, sizeof(buffer));
            if (n <= 0) {
                break;  // EOF (Ctrl+D): đóng kết nối và thoát
            }
            send(client_socket, buffer, n, 0);
        }
    }
    close(client_socket);
    return 0;
}
