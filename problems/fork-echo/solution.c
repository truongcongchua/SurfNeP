// Lời giải mẫu theo code mẫu 3-Chap3/L3-MultiProcessing/forking_server.c.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>

// Thu dọn MỌI tiến trình con đã kết thúc: nhiều SIGCHLD đến cùng lúc chỉ gọi handler một lần.
void signal_handler(int signum) {
    while (waitpid(-1, NULL, WNOHANG) > 0);
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    signal(SIGCHLD, signal_handler);

    int listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    int opt = 1;
    setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(listener, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("bind() failed");
        return 1;
    }
    if (listen(listener, 64) == -1) {
        perror("listen() failed");
        return 1;
    }

    while (0 == 0) {
        int client = accept(listener, NULL, NULL);
        if (client == -1) {
            continue;
        }
        if (fork() == 0) {
            // Tiến trình con
            close(listener);
            char buffer[1024];
            while (0 == 0) {
                int bytes_received = recv(client, buffer, sizeof(buffer), 0);
                if (bytes_received <= 0) {
                    break;
                }
                send(client, buffer, bytes_received, 0);
            }
            close(client);
            exit(0);
        }
        // Tiến trình cha
        close(client);
    }
}
