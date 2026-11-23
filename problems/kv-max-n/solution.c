// Lời giải mẫu: select() + bộ đệm dòng riêng + giới hạn N client.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_FD_CLIENTS 64
#define BUF_SIZE 4096
#define MAX_KEYS 1000
#define KLEN 65

typedef struct { int fd; char buf[BUF_SIZE]; size_t len; } Client;
typedef struct { char key[KLEN], val[KLEN]; } Entry;

static Client clients[MAX_FD_CLIENTS];
static Entry table[MAX_KEYS];
static int nkeys = 0, nclients = 0;

static void reply(int fd, const char *s) { send(fd, s, strlen(s), 0); }

static int find(const char *k) {
    for (int i = 0; i < nkeys; i++)
        if (strcmp(table[i].key, k) == 0) return i;
    return -1;
}

static void drop(Client *c) {
    close(c->fd);
    c->fd = -1;
    c->len = 0;
    nclients--;
}

// Trả về 0 nếu client phải bị đóng (QUIT).
static int handle(Client *c, char *line) {
    size_t n = strlen(line);
    if (n && line[n - 1] == '\r') line[--n] = 0;
    char *tok[4], *save = NULL;
    int nt = 0;
    for (char *t = strtok_r(line, " ", &save); t && nt < 4; t = strtok_r(NULL, " ", &save))
        tok[nt++] = t;
    for (int i = 1; i < nt; i++)
        if (strlen(tok[i]) >= KLEN) { reply(c->fd, "ERROR\n"); return 1; }
    char out[160];
    if (nt == 3 && !strcmp(tok[0], "SET")) {
        int i = find(tok[1]);
        if (i < 0 && nkeys == MAX_KEYS) { reply(c->fd, "ERROR\n"); return 1; }
        if (i < 0) { i = nkeys++; strcpy(table[i].key, tok[1]); }
        strcpy(table[i].val, tok[2]);
        reply(c->fd, "OK\n");
    } else if (nt == 2 && !strcmp(tok[0], "GET")) {
        int i = find(tok[1]);
        if (i < 0) reply(c->fd, "NOT_FOUND\n");
        else { snprintf(out, sizeof out, "VALUE %s\n", table[i].val); reply(c->fd, out); }
    } else if (nt == 2 && !strcmp(tok[0], "DEL")) {
        int i = find(tok[1]);
        if (i < 0) reply(c->fd, "NOT_FOUND\n");
        else { table[i] = table[--nkeys]; reply(c->fd, "OK\n"); }
    } else if (nt == 1 && !strcmp(tok[0], "COUNT")) {
        snprintf(out, sizeof out, "COUNT %d\n", nkeys);
        reply(c->fd, out);
    } else if (nt == 1 && !strcmp(tok[0], "QUIT")) {
        reply(c->fd, "BYE\n");
        return 0;
    } else {
        reply(c->fd, "ERROR\n");
    }
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <N>\n", argv[0]);
        return 1;
    }
    int limit = atoi(argv[2]);
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 16) < 0) {
        perror("bind/listen");
        return 1;
    }
    for (int i = 0; i < MAX_FD_CLIENTS; i++) clients[i].fd = -1;

    for (;;) {
        fd_set rd;
        FD_ZERO(&rd);
        FD_SET(ls, &rd);
        int maxfd = ls;
        for (int i = 0; i < MAX_FD_CLIENTS; i++)
            if (clients[i].fd >= 0) {
                FD_SET(clients[i].fd, &rd);
                if (clients[i].fd > maxfd) maxfd = clients[i].fd;
            }
        if (select(maxfd + 1, &rd, NULL, NULL, NULL) < 0) { perror("select"); return 1; }

        if (FD_ISSET(ls, &rd)) {
            int fd = accept(ls, NULL, NULL);
            if (fd >= 0 && nclients >= limit) {
                reply(fd, "FULL\n");
                close(fd);
            } else if (fd >= 0) {
                for (int i = 0; i < MAX_FD_CLIENTS; i++)
                    if (clients[i].fd < 0) {
                        clients[i].fd = fd;
                        clients[i].len = 0;
                        nclients++;
                        reply(fd, "WELCOME\n");
                        break;
                    }
            }
        }
        for (int i = 0; i < MAX_FD_CLIENTS; i++) {
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
            if (c->len == BUF_SIZE - 1) { reply(c->fd, "ERROR\n"); c->len = 0; }
        }
    }
}
