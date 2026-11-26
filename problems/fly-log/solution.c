// Lời giải mẫu: select() + bộ đệm dòng riêng; mọi sự kiện ghi vào một FILE* mở sẵn, flush ngay.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define MAX_CLIENTS 64
#define BUF_SIZE 2048

typedef struct { int fd; char buf[BUF_SIZE]; size_t len; char addr[32]; } Client;

static Client clients[MAX_CLIENTS];
static FILE *logf;

static void log_event(const char *addr, const char *kind, const char *text) {
    time_t now = time(NULL);
    char ts[32];
    strftime(ts, sizeof ts, "%Y-%m-%d %H:%M:%S", localtime(&now));
    if (text) fprintf(logf, "[%s] %s %s \"%s\"\n", ts, kind, addr, text);
    else fprintf(logf, "[%s] %s %s\n", ts, kind, addr);
    fflush(logf);
}

// Ghi log SEND trước, rồi mới gửi.
static void reply(Client *c, const char *line) {
    log_event(c->addr, "SEND", line);
    char out[128];
    int n = snprintf(out, sizeof out, "%s\n", line);
    send(c->fd, out, (size_t)n, 0);
}

static void drop(Client *c) {
    log_event(c->addr, "DISCONNECT", NULL);
    close(c->fd);
    c->fd = -1;
    c->len = 0;
}

// Trả về 0 nếu phải đóng kết nối.
static int handle(Client *c, char *line) {
    size_t n = strlen(line);
    if (n && line[n - 1] == '\r') line[--n] = 0;
    log_event(c->addr, "RECV", line);
    if (strcmp(line, "PING") == 0) {
        reply(c, "100 OK PONG");
    } else if (strcmp(line, "QUIT") == 0) {
        reply(c, "100 OK");
        return 0;
    } else {
        reply(c, "999 UNKNOWN ERROR");
    }
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 3) { fprintf(stderr, "usage: %s <port> <logfile>\n", argv[0]); return 1; }
    logf = fopen(argv[2], "a");
    if (!logf) { perror("log"); return 1; }
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 16) < 0) { perror("bind/listen"); return 1; }
    for (int i = 0; i < MAX_CLIENTS; i++) clients[i].fd = -1;

    for (;;) {
        fd_set rd;
        FD_ZERO(&rd);
        FD_SET(ls, &rd);
        int maxfd = ls;
        for (int i = 0; i < MAX_CLIENTS; i++)
            if (clients[i].fd >= 0) {
                FD_SET(clients[i].fd, &rd);
                if (clients[i].fd > maxfd) maxfd = clients[i].fd;
            }
        if (select(maxfd + 1, &rd, NULL, NULL, NULL) < 0) { perror("select"); return 1; }

        if (FD_ISSET(ls, &rd)) {
            struct sockaddr_in ca;
            socklen_t cl = sizeof ca;
            int fd = accept(ls, (struct sockaddr *)&ca, &cl);
            if (fd >= 0) {
                int placed = 0;
                for (int i = 0; i < MAX_CLIENTS && !placed; i++)
                    if (clients[i].fd < 0) {
                        clients[i].fd = fd;
                        clients[i].len = 0;
                        snprintf(clients[i].addr, sizeof clients[i].addr, "%s:%d", inet_ntoa(ca.sin_addr), ntohs(ca.sin_port));
                        log_event(clients[i].addr, "CONNECT", NULL);
                        placed = 1;
                    }
                if (!placed) close(fd);
            }
        }
        for (int i = 0; i < MAX_CLIENTS; i++) {
            Client *c = &clients[i];
            if (c->fd < 0 || !FD_ISSET(c->fd, &rd)) continue;
            ssize_t n = recv(c->fd, c->buf + c->len, BUF_SIZE - 1 - c->len, 0);
            if (n <= 0) { drop(c); continue; }
            c->len += (size_t)n;
            c->buf[c->len] = 0;
            char *start = c->buf, *nl;
            int alive = 1;
            while (alive && (nl = strchr(start, '\n'))) {
                *nl = 0;
                alive = handle(c, start);
                start = nl + 1;
            }
            if (!alive) { drop(c); continue; }
            c->len -= (size_t)(start - c->buf);
            memmove(c->buf, start, c->len);
            if (c->len == BUF_SIZE - 1) { c->len = 0; }
        }
    }
}
