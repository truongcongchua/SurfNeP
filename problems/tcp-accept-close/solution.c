// Lời giải mẫu: phần đầu của 2-Chap2/tcp_server.c (socket -> bind -> listen -> accept).
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    int listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listener == -1) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(argv[1]));
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(listener, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("bind");
        close(listener);
        exit(EXIT_FAILURE);
    }
    if (listen(listener, 5) == -1) {
        perror("listen");
        close(listener);
        exit(EXIT_FAILURE);
    }

    int client = accept(listener, NULL, NULL);
    if (client == -1) {
        perror("accept");
        close(listener);
        exit(EXIT_FAILURE);
    }

    close(client);
    close(listener);
    return 0;
}
