// Lời giải mẫu: khung accept của pthread_server.c, mỗi client một luồng, fd truyền qua ô nhớ malloc riêng.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <arpa/inet.h>
#include <sys/socket.h>

void *greet(void *arg);

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    int server_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    int opt = 1;
    setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(atoi(argv[1]));
    server_addr.sin_addr.s_addr = INADDR_ANY;
    if (bind(server_socket, (struct sockaddr *)&server_addr, sizeof(server_addr)) == -1) {
        perror("bind() failed");
        return 1;
    }
    if (listen(server_socket, 64) == -1) {
        perror("listen() failed");
        return 1;
    }

    while (1) {
        int client_socket = accept(server_socket, NULL, NULL);
        if (client_socket == -1) {
            continue;
        }
        int *arg = malloc(sizeof(int));
        *arg = client_socket;
        pthread_t thread;
        if (pthread_create(&thread, NULL, greet, arg) != 0) {
            close(client_socket);
            free(arg);
            continue;
        }
        pthread_detach(thread);
    }
    return 0;
}

void *greet(void *arg) {
    int client_socket = *(int *)arg;
    free(arg);
    sleep(1);
    send(client_socket, "Hello!\n", 7, 0);
    close(client_socket);
    return NULL;
}
