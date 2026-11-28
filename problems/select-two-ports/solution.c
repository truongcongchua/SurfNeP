// Lời giải mẫu: khung select của select_server.c, nhưng theo dõi hai socket nghe thay cho danh sách client.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/select.h>

int make_listener(int port) {
    int s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    int opt = 1;
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = INADDR_ANY;
    if (bind(s, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("bind() failed");
        exit(1);
    }
    if (listen(s, 64) == -1) {
        perror("listen() failed");
        exit(1);
    }
    return s;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    int port = atoi(argv[1]);
    int listener1 = make_listener(port);
    int listener2 = make_listener(port + 1);

    fd_set read_fds;
    while (1) {
        // select() ghi đè read_fds nên phải dựng lại mỗi vòng
        FD_ZERO(&read_fds);
        FD_SET(listener1, &read_fds);
        FD_SET(listener2, &read_fds);
        int max_fd = listener1 > listener2 ? listener1 : listener2;
        if (select(max_fd + 1, &read_fds, NULL, NULL, NULL) < 0) {
            continue;
        }
        if (FD_ISSET(listener1, &read_fds)) {
            int client = accept(listener1, NULL, NULL);
            if (client >= 0) {
                send(client, "ONE\n", 4, 0);
                close(client);
            }
        }
        if (FD_ISSET(listener2, &read_fds)) {
            int client = accept(listener2, NULL, NULL);
            if (client >= 0) {
                send(client, "TWO\n", 4, 0);
                close(client);
            }
        }
    }
    return 0;
}
