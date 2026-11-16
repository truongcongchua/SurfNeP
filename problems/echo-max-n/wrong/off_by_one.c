// SAI có chủ đích: so sánh > thay vì >= nên cho vào N+1 client (lệch một).
#include <arpa/inet.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define BUF_SIZE 4096
#define MAX_CLIENTS 64

typedef struct { int fd; char buf[BUF_SIZE]; size_t len; } Client;
static Client cl[MAX_CLIENTS];
static int active;

static void send_str(int fd, const char *s) { send(fd, s, strlen(s), MSG_NOSIGNAL); }

// Xử lý một dòng. Trả về 0 nếu phải đóng client.
static int handle_line(Client *x, char *line) {
    size_t n = strlen(line);
    if (n && line[n - 1] == '\r') line[--n] = 0;
    char out[BUF_SIZE + 16];
    if (!strcmp(line, "QUIT")) {
        send_str(x->fd, "BYE\n");
        return 0;
    }
    if (!strcmp(line, "COUNT")) snprintf(out, sizeof out, "COUNT %d\n", active);
    else snprintf(out, sizeof out, "ECHO %s\n", line);
    send_str(x->fd, out);
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <N>\n", argv[0]);
        return 1;
    }
    int limit = atoi(argv[2]);
    for (int i = 0; i < MAX_CLIENTS; i++) cl[i].fd = -1;
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 64) < 0) {
        perror("bind/listen");
        return 1;
    }
    for (;;) {
        struct pollfd pfd[MAX_CLIENTS + 1];
        int idx[MAX_CLIENTS + 1];
        int n = 0;
        pfd[n].fd = ls;
        pfd[n].events = POLLIN;
        idx[n++] = -1;
        for (int i = 0; i < MAX_CLIENTS; i++)
            if (cl[i].fd >= 0) {
                pfd[n].fd = cl[i].fd;
                pfd[n].events = POLLIN;
                idx[n++] = i;
            }
        if (poll(pfd, (nfds_t)n, -1) < 0) continue;
        if (pfd[0].revents & POLLIN) {
            int c = accept(ls, NULL, NULL);
            int slot = -1;
            for (int i = 0; i < MAX_CLIENTS && slot < 0; i++)
                if (cl[i].fd < 0) slot = i;
            if (c >= 0) {
                if (active > limit || slot < 0) {
                    send_str(c, "FULL\n");
                    close(c);
                } else {
                    cl[slot].fd = c;
                    cl[slot].len = 0;
                    active++;
                    send_str(c, "WELCOME\n");
                }
            }
        }
        for (int j = 1; j < n; j++) {
            Client *x = &cl[idx[j]];
            if (!(pfd[j].revents & (POLLIN | POLLHUP | POLLERR))) continue;
            ssize_t k = recv(x->fd, x->buf + x->len, BUF_SIZE - 1 - x->len, 0);
            int alive = k > 0;
            if (alive) {
                x->len += (size_t)k;
                x->buf[x->len] = 0;
                char *start = x->buf, *nl;
                while (alive && (nl = strchr(start, '\n'))) {
                    *nl = 0;
                    alive = handle_line(x, start);
                    start = nl + 1;
                }
                x->len -= (size_t)(start - x->buf);
                memmove(x->buf, start, x->len);
                if (x->len == BUF_SIZE - 1) x->len = 0;
            }
            if (!alive) {
                close(x->fd);
                x->fd = -1;
                active--;
            }
        }
    }
}
