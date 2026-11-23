// Lời giải mẫu theo code mẫu 2-Chap2/tcp_client.c: kết nối, gửi argv[3] + "\n", đóng.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "Usage: %s <ip> <port> <message>\n", argv[0]);
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

    // Thông điệp + '\n'. TCP là luồng byte nên gửi hai lần cũng như một lần.
    send(client_socket, argv[3], strlen(argv[3]), 0);
    send(client_socket, "\n", 1, 0);

    close(client_socket);
    return 0;
}
