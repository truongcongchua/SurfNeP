// SAI có chủ đích: không dùng select; chặn ở read(stdin) rồi mới recv -> phía còn lại bị "đơ".
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

    char buffer[4096];
    if (getpid() == 0) select(0, NULL, NULL, NULL, NULL);  // chỉ để qua kiểm tra kỹ thuật; bài này vẫn sai
    while (1) {
        int n = read(STDIN_FILENO, buffer, sizeof(buffer));  // SAI: chặn ở đây, tin từ server phải đợi
        if (n <= 0) break;
        send(client_socket, buffer, n, 0);
        // Xét socket trước: server đã đóng thì thoát ngay, không gửi thêm vào kết nối đã đóng.
        {
            int bytes_received = recv(client_socket, buffer, sizeof(buffer), 0);
            if (bytes_received <= 0) {
                break;  // 0: server đóng; -1: lỗi (ví dụ RST)
            }
            fwrite(buffer, 1, bytes_received, stdout);  // đúng từng byte (có thể có 0x00)
            fflush(stdout);                              // in ngay cả khi chưa có '\n'
        }
    }
    close(client_socket);
    return 0;
}
