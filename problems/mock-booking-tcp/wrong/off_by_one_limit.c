// SAI có chủ đích: cho phép N+1 client.
// Lời giải mẫu: select() + bộ đệm dòng + bảng ghế gắn với tên.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_FD_CLIENTS 64
#define BUF_SIZE 4096
#define NAME_MAX_LEN 32

typedef struct { int fd; char name[NAME_MAX_LEN + 1]; char buf[BUF_SIZE]; size_t len; } Client;

static Client cl[MAX_FD_CLIENTS];
static char owner[101][NAME_MAX_LEN + 1];  // owner[g][0] == 0: ghế trống
static int nseats, nclients, limit;

static void reply(int fd, const char *s) {
    send(fd, s, strlen(s), 0);
    send(fd, "\n", 1, 0);
}

static int parse_seat(const char *s) {
    if (!*s) return 0;
    for (const char *p = s; *p; p++)
        if (*p < '0' || *p > '9') return 0;
    if (strlen(s) > 4) return 0;
    int g = atoi(s);
    return g >= 1 && g <= nseats ? g : 0;
}

// Ghép danh sách ghế thoả điều kiện vào out: "<k> g1 g2 ..."
static void seat_list(char *out, size_t cap, const char *prefix, const char *who) {
    char tail[1024] = "";
    int k = 0;
    for (int g = 1; g <= nseats; g++) {
        int match = who ? !strcmp(owner[g], who) : !owner[g][0];
        if (match) {
            k++;
            size_t l = strlen(tail);
            snprintf(tail + l, sizeof tail - l, " %d", g);
        }
    }
    snprintf(out, cap, "%s %d%s", prefix, k, tail);
}

// Trả về 0 nếu phải đóng client (QUIT).
static int handle(Client *c, char *line) {
    size_t n = strlen(line);
    if (n && line[n - 1] == '\r') line[--n] = 0;
    char *tok[3], *save = NULL;
    int nt = 0;
    for (char *t = strtok_r(line, " ", &save); t && nt < 3; t = strtok_r(NULL, " ", &save)) tok[nt++] = t;
    char out[1200];
    const char *cmd = nt ? tok[0] : "";
    if (nt == 2 && !strcmp(cmd, "LOGIN") && strlen(tok[1]) <= NAME_MAX_LEN) {
        strcpy(c->name, tok[1]);
        snprintf(out, sizeof out, "OK %s", c->name);
    } else if (nt == 1 && !strcmp(cmd, "LIST")) {
        seat_list(out, sizeof out, "FREE", NULL);
    } else if (nt == 1 && !strcmp(cmd, "QUIT")) {
        reply(c->fd, "BYE");
        return 0;
    } else if ((nt == 2 && (!strcmp(cmd, "BOOK") || !strcmp(cmd, "CANCEL"))) || (nt == 1 && !strcmp(cmd, "MINE"))) {
        int g = nt == 2 ? parse_seat(tok[1]) : 0;
        if (!c->name[0]) snprintf(out, sizeof out, "LOGIN_FIRST");
        else if (!strcmp(cmd, "MINE")) seat_list(out, sizeof out, "MINE", c->name);
        else if (!g) snprintf(out, sizeof out, "INVALID");
        else if (!strcmp(cmd, "BOOK")) {
            if (owner[g][0]) snprintf(out, sizeof out, "TAKEN %d", g);
            else {
                strcpy(owner[g], c->name);
                snprintf(out, sizeof out, "BOOKED %d", g);
            }
        } else if (!strcmp(owner[g], c->name)) {
            owner[g][0] = 0;
            snprintf(out, sizeof out, "CANCELLED %d", g);
        } else {
            snprintf(out, sizeof out, "NOT_YOURS %d", g);
        }
    } else {
        snprintf(out, sizeof out, "ERROR");
    }
    reply(c->fd, out);
    return 1;
}

static void drop(Client *c) {
    close(c->fd);
    c->fd = -1;
    nclients--;
}

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <N> <S>\n", argv[0]);
        return 1;
    }
    limit = atoi(argv[2]);
    nseats = atoi(argv[3]);
    for (int i = 0; i < MAX_FD_CLIENTS; i++) cl[i].fd = -1;
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
        fd_set rd;
        FD_ZERO(&rd);
        FD_SET(ls, &rd);
        int maxfd = ls;
        for (int i = 0; i < MAX_FD_CLIENTS; i++)
            if (cl[i].fd >= 0) {
                FD_SET(cl[i].fd, &rd);
                if (cl[i].fd > maxfd) maxfd = cl[i].fd;
            }
        if (select(maxfd + 1, &rd, NULL, NULL, NULL) < 0) continue;
        if (FD_ISSET(ls, &rd)) {
            int fd = accept(ls, NULL, NULL);
            if (fd >= 0 && nclients > limit) {
                reply(fd, "FULL");
                close(fd);
            } else if (fd >= 0) {
                for (int i = 0; i < MAX_FD_CLIENTS; i++)
                    if (cl[i].fd < 0) {
                        cl[i].fd = fd;
                        cl[i].len = 0;
                        cl[i].name[0] = 0;
                        nclients++;
                        reply(fd, "WELCOME");
                        break;
                    }
            }
        }
        for (int i = 0; i < MAX_FD_CLIENTS; i++) {
            Client *c = &cl[i];
            if (c->fd < 0 || !FD_ISSET(c->fd, &rd)) continue;
            ssize_t k = recv(c->fd, c->buf + c->len, BUF_SIZE - 1 - c->len, 0);
            if (k <= 0) {
                drop(c);
                continue;
            }
            c->len += (size_t)k;
            c->buf[c->len] = 0;
            char *start = c->buf, *nl;
            int alive = 1;
            while (alive && (nl = strchr(start, '\n'))) {
                *nl = 0;
                alive = handle(c, start);
                start = nl + 1;
            }
            if (!alive) {
                drop(c);
                continue;
            }
            c->len -= (size_t)(start - c->buf);
            memmove(c->buf, start, c->len);
            if (c->len == BUF_SIZE - 1) c->len = 0;
        }
    }
}
