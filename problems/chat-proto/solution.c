// Lời giải mẫu: select() một luồng, bộ đệm dòng và tên riêng của mỗi client.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_CLIENTS 64
#define BUF_SIZE 4096

typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int joined; char nick[40]; } Client;

static Client clients[MAX_CLIENTS];

static void reply(int fd, const char *s) { send(fd, s, strlen(s), 0); }

static Client *find_nick(const char *nick) {
    for (int i = 0; i < MAX_CLIENTS; i++)
        if (clients[i].fd >= 0 && clients[i].joined && strcmp(clients[i].nick, nick) == 0) return &clients[i];
    return NULL;
}

static int valid_nick(const char *s) {
    size_t n = strlen(s);
    if (n < 1 || n > 32) return 0;
    for (size_t i = 0; i < n; i++)
        if (!((s[i] >= 'a' && s[i] <= 'z') || (s[i] >= '0' && s[i] <= '9'))) return 0;
    return 1;
}

static void drop(Client *c) {
    close(c->fd);
    c->fd = -1;
    c->len = 0;
    c->joined = 0;
}

// Trả về 0 nếu phải đóng kết nối.
static int handle(Client *c, char *line) {
    size_t n = strlen(line);
    if (n && line[n - 1] == '\r') line[--n] = 0;
    char *arg = strchr(line, ' ');
    if (arg) *arg++ = 0;  // line = tên lệnh, arg = phần còn lại nguyên văn (NULL nếu không có dấu cách)
    char out[BUF_SIZE + 128];

    if (!strcmp(line, "QUIT") && !arg) {
        reply(c->fd, "100 OK\n");
        return 0;
    }
    if (!strcmp(line, "JOIN") && arg) {
        if (c->joined) reply(c->fd, "203 DENIED\n");
        else if (!valid_nick(arg)) reply(c->fd, "201 INVALID NICK NAME\n");
        else if (find_nick(arg)) reply(c->fd, "200 NICKNAME IN USE\n");
        else { strcpy(c->nick, arg); c->joined = 1; reply(c->fd, "100 OK\n"); }
        return 1;
    }
    if (!strcmp(line, "MSG") && arg && *arg) {
        if (!c->joined) { reply(c->fd, "203 DENIED\n"); return 1; }
        snprintf(out, sizeof out, "[%s]: %s\n", c->nick, arg);
        for (int i = 0; i < MAX_CLIENTS; i++)
            if (clients[i].fd >= 0 && clients[i].joined && &clients[i] != c) reply(clients[i].fd, out);
        reply(c->fd, "100 OK\n");
        return 1;
    }
    if (!strcmp(line, "PMSG") && arg) {
        char *text = strchr(arg, ' ');
        if (text) *text++ = 0;
        if (!text || !*text) { reply(c->fd, "999 UNKNOWN ERROR\n"); return 1; }
        if (!c->joined) { reply(c->fd, "203 DENIED\n"); return 1; }
        Client *to = find_nick(arg);
        if (!to || to == c) { reply(c->fd, "202 UNKNOWN NICKNAME\n"); return 1; }
        snprintf(out, sizeof out, "[%s] (private): %s\n", c->nick, text);
        reply(to->fd, out);
        reply(c->fd, "100 OK\n");
        return 1;
    }
    reply(c->fd, "999 UNKNOWN ERROR\n");
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 2) { fprintf(stderr, "usage: %s <port>\n", argv[0]); return 1; }
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
            int fd = accept(ls, NULL, NULL);
            if (fd >= 0) {
                int placed = 0;
                for (int i = 0; i < MAX_CLIENTS && !placed; i++)
                    if (clients[i].fd < 0) { clients[i].fd = fd; clients[i].len = 0; clients[i].joined = 0; placed = 1; }
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
            if (c->len == BUF_SIZE - 1) { reply(c->fd, "999 UNKNOWN ERROR\n"); c->len = 0; }
        }
    }
}
