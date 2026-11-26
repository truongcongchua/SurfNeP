// Lời giải mẫu: select() + bộ đệm dòng riêng + bảng tài khoản nạp từ accounts.txt, ghi nối khi REGISTER.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_CLIENTS 64
#define BUF_SIZE 2048
#define MAX_ACCOUNTS 1000
#define MAXTOK 32

typedef struct { char user[40], pass[40]; } Account;
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct; } Client;  // acct = -1: chưa đăng nhập

static Account acc[MAX_ACCOUNTS];
static int nacc = 0, nclients = 0;
static Client clients[MAX_CLIENTS];

static void load_accounts(void) {
    FILE *f = fopen("accounts.txt", "r");
    if (!f) return;
    char u[64], p[64];
    while (nacc < MAX_ACCOUNTS && fscanf(f, "%39s %39s", u, p) == 2) {
        strcpy(acc[nacc].user, u);
        strcpy(acc[nacc].pass, p);
        nacc++;
    }
    fclose(f);
}

static int find_user(const char *u) {
    for (int i = 0; i < nacc; i++)
        if (strcmp(acc[i].user, u) == 0) return i;
    return -1;
}

static int valid_user(const char *s) {
    size_t n = strlen(s);
    if (n < 1 || n > 32) return 0;
    for (size_t i = 0; i < n; i++)
        if (!((s[i] >= 'a' && s[i] <= 'z') || (s[i] >= '0' && s[i] <= '9'))) return 0;
    return 1;
}

static int valid_pass(const char *s) {
    size_t n = strlen(s);
    if (n < 4 || n > 32) return 0;
    for (size_t i = 0; i < n; i++)
        if ((unsigned char)s[i] < 0x21 || (unsigned char)s[i] > 0x7E) return 0;
    return 1;
}

static void reply(int fd, const char *s) { send(fd, s, strlen(s), 0); }

static int in_use(int a) {
    for (int i = 0; i < MAX_CLIENTS; i++)
        if (clients[i].fd >= 0 && clients[i].acct == a) return 1;
    return 0;
}

static void drop(Client *c) {
    close(c->fd);
    c->fd = -1;
    c->len = 0;
    c->acct = -1;
    nclients--;
}

// Trả về 0 nếu phải đóng kết nối.
static int handle(Client *c, char *line) {
    size_t n = strlen(line);
    if (n && line[n - 1] == '\r') line[--n] = 0;
    char *tok[MAXTOK + 1];
    int nt = 0;
    for (char *p = line;;) {
        if (nt < MAXTOK) tok[nt] = p;
        nt++;
        char *sp = strchr(p, ' ');
        if (!sp) break;
        *sp = 0;
        p = sp + 1;
    }
    if (nt > MAXTOK) nt = MAXTOK + 1;
    char out[128];

    if (strcmp(tok[0], "REGISTER") == 0) {
        if (nt != 3 || !valid_user(tok[1]) || !valid_pass(tok[2])) reply(c->fd, "201 INVALID\n");
        else if (find_user(tok[1]) >= 0 || nacc >= MAX_ACCOUNTS) reply(c->fd, "200 USERNAME IN USE\n");
        else {
            FILE *f = fopen("accounts.txt", "a");
            if (f) { fprintf(f, "%s %s\n", tok[1], tok[2]); fclose(f); }
            strcpy(acc[nacc].user, tok[1]);
            strcpy(acc[nacc].pass, tok[2]);
            nacc++;
            reply(c->fd, "100 OK\n");
        }
    } else if (strcmp(tok[0], "LOGIN") == 0) {
        int a;
        if (nt != 3 || !valid_user(tok[1]) || !valid_pass(tok[2])) reply(c->fd, "201 INVALID\n");
        else if (c->acct >= 0) reply(c->fd, "207 ALREADY LOGGED IN\n");
        else if ((a = find_user(tok[1])) < 0 || strcmp(acc[a].pass, tok[2]) != 0) reply(c->fd, "203 DENIED\n");
        else if (in_use(a)) reply(c->fd, "207 ALREADY LOGGED IN\n");
        else {
            c->acct = a;
            snprintf(out, sizeof out, "100 OK %s\n", acc[a].user);
            reply(c->fd, out);
        }
    } else if (strcmp(tok[0], "LOGOUT") == 0) {
        if (nt != 1) reply(c->fd, "201 INVALID\n");
        else if (c->acct < 0) reply(c->fd, "204 LOGIN FIRST\n");
        else { c->acct = -1; reply(c->fd, "100 OK\n"); }
    } else if (strcmp(tok[0], "WHOAMI") == 0) {
        if (nt != 1) reply(c->fd, "201 INVALID\n");
        else if (c->acct < 0) reply(c->fd, "204 LOGIN FIRST\n");
        else {
            snprintf(out, sizeof out, "100 OK %s\n", acc[c->acct].user);
            reply(c->fd, out);
        }
    } else if (strcmp(tok[0], "QUIT") == 0) {
        if (nt != 1) { reply(c->fd, "201 INVALID\n"); return 1; }
        reply(c->fd, "100 OK\n");
        return 0;
    } else {
        reply(c->fd, "999 UNKNOWN ERROR\n");
    }
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 3) { fprintf(stderr, "usage: %s <port> <N>\n", argv[0]); return 1; }
    int limit = atoi(argv[2]);
    load_accounts();
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 16) < 0) { perror("bind/listen"); return 1; }
    for (int i = 0; i < MAX_CLIENTS; i++) { clients[i].fd = -1; clients[i].acct = -1; }

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
            if (fd >= 0 && nclients >= limit) {
                reply(fd, "500 FULL\n");
                close(fd);
            } else if (fd >= 0) {
                for (int i = 0; i < MAX_CLIENTS; i++)
                    if (clients[i].fd < 0) {
                        clients[i].fd = fd;
                        clients[i].len = 0;
                        clients[i].acct = -1;
                        nclients++;
                        reply(fd, "100 OK WELCOME\n");
                        break;
                    }
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
