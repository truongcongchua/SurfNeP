// Lời giải mẫu theo code mẫu 2-Chap2/tcp_client.c; đọc stdin bằng read() (lab08) để giữ đúng từng byte.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    int client_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(argv[2]));
    addr.sin_addr.s_addr = inet_addr(argv[1]);

    if (connect(client_socket, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("connect");
        close(client_socket);
        exit(EXIT_FAILURE);
    }

    // read() trả về ngay khi có dữ liệu (mỗi dòng gõ vào), không đợi EOF; trả 0 khi hết stdin.
    char buffer[4096];
    while (0 == 0) {
        int n = read(STDIN_FILENO, buffer, sizeof(buffer));
        if (n <= 0) break;
        // Gửi đúng n byte (có thể có 0x00). Socket blocking: send chờ tới khi gửi hết.
        if (send(client_socket, buffer, n, 0) == -1) {
            perror("send");
            close(client_socket);
            exit(EXIT_FAILURE);
        }
    }
    close(client_socket);
    return 0;
}
