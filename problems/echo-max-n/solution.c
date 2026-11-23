// Lời giải mẫu: select() (như select_server.c) + bộ đệm dòng riêng mỗi client + giới hạn N client.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/select.h>

#define BUF_SIZE 4096
#define MAX_CLIENTS 64

int client_fd[MAX_CLIENTS];         // -1 = ô trống
char client_buf[MAX_CLIENTS][BUF_SIZE];
int client_len[MAX_CLIENTS];        // số byte đang chờ trong bộ đệm (dòng chưa trọn)
int active = 0;                     // số client đang kết nối

// Xử lý một dòng của client i. Trả về 0 nếu phải đóng client.
int handle_line(int i, char *line) {
    int n = strlen(line);
    if (n > 0 && line[n - 1] == '\r') line[n - 1] = 0;
    char out[BUF_SIZE + 16];
    if (strcmp(line, "QUIT") == 0) {
        send(client_fd[i], "BYE\n", 4, 0);
        return 0;
    }
    if (strcmp(line, "COUNT") == 0) sprintf(out, "COUNT %d\n", active);
    else sprintf(out, "ECHO %s\n", line);
    send(client_fd[i], out, strlen(out), 0);
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <port> <N>\n", argv[0]);
        return 1;
    }
    int limit = atoi(argv[2]);
    for (int i = 0; i < MAX_CLIENTS; i++) client_fd[i] = -1;

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

    fd_set read_fds;
    while (1) {
        FD_ZERO(&read_fds);
        FD_SET(listener, &read_fds);
        int max_fd = listener;
        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (client_fd[i] < 0) continue;
            FD_SET(client_fd[i], &read_fds);
            if (client_fd[i] > max_fd) max_fd = client_fd[i];
        }
        if (select(max_fd + 1, &read_fds, NULL, NULL, NULL) < 0) continue;

        if (FD_ISSET(listener, &read_fds)) {
            int c = accept(listener, NULL, NULL);
            int slot = -1;
            for (int i = 0; i < MAX_CLIENTS && slot < 0; i++)
                if (client_fd[i] < 0) slot = i;
            if (c >= 0) {
                if (active >= limit || slot < 0) {
                    send(c, "FULL\n", 5, 0);
                    close(c);
                } else {
                    client_fd[slot] = c;
                    client_len[slot] = 0;
                    active++;
                    send(c, "WELCOME\n", 8, 0);
                }
            }
        }

        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (client_fd[i] < 0 || !FD_ISSET(client_fd[i], &read_fds)) continue;
            char *buf = client_buf[i];
            int k = recv(client_fd[i], buf + client_len[i], BUF_SIZE - 1 - client_len[i], 0);
            int alive = k > 0;
            if (alive) {
                client_len[i] += k;
                buf[client_len[i]] = 0;
                // Cắt từng dòng trọn vẹn; phần dở dang giữ lại cho lần recv sau.
                char *start = buf, *nl;
                while (alive && (nl = strchr(start, '\n')) != NULL) {
                    *nl = 0;
                    alive = handle_line(i, start);
                    start = nl + 1;
                }
                client_len[i] -= start - buf;
                memmove(buf, start, client_len[i]);
                if (client_len[i] == BUF_SIZE - 1) client_len[i] = 0;
            }
            if (!alive) {  // QUIT, client đóng (recv == 0) hoặc lỗi (recv == -1)
                close(client_fd[i]);
                client_fd[i] = -1;
                active--;
            }
        }
    }
}
