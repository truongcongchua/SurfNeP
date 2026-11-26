// Lời giải mẫu: select() một luồng; dữ liệu dùng chung nằm trong bộ nhớ.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_CLIENTS 64
#define BUF_SIZE 2048
#define MAX_FLIGHTS 200
#define MAX_ACCOUNTS 50
#define MAX_TICKETS 10000
#define MAXTOK 16

typedef struct { char code[16], from[8], to[8], date[16], dep[8], arr[8]; long long price; int seats; } Flight;
typedef struct { char user[40], pass[40]; long long balance; } Account;
typedef struct { int id, acct, flight, alive; } Ticket;
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct; } Client;

static Flight fl[MAX_FLIGHTS];
static Account acc[MAX_ACCOUNTS];
static Ticket tk[MAX_TICKETS];
static int nfl, nacc, ntk, nclients;
static Client clients[MAX_CLIENTS];

static void load_files(void) {
    char line[512], u[64], p[64];
    FILE *f = fopen("flights.txt", "r");
    while (f && nfl < MAX_FLIGHTS && fgets(line, sizeof line, f)) {
        Flight *x = &fl[nfl];
        char air[8];
        long long bp;
        int bs;
        if (sscanf(line, "%15s %7s %7s %7s %15s %7s %7s %lld %d %lld %d", x->code, air, x->from, x->to, x->date, x->dep,
                   x->arr, &x->price, &x->seats, &bp, &bs) == 11)
            nfl++;
    }
    if (f) fclose(f);
    f = fopen("accounts.txt", "r");
    while (f && nacc < MAX_ACCOUNTS && fscanf(f, "%39s %39s", acc[nacc].user, acc[nacc].pass) == 2) nacc++;
    if (f) fclose(f);
    f = fopen("wallets.txt", "r");
    long long bal;
    while (f && fscanf(f, "%39s %lld", u, &bal) == 2)
        for (int i = 0; i < nacc; i++)
            if (!strcmp(acc[i].user, u)) acc[i].balance = bal;
    if (f) fclose(f);
}

static void reply(int fd, const char *s) { send(fd, s, strlen(s), 0); }

static int find_flight(const char *code, const char *date) {
    for (int i = 0; i < nfl; i++)
        if (!strcmp(fl[i].code, code) && !strcmp(fl[i].date, date)) return i;
    return -1;
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
    char out[8192];
    const char *cmd = tok[0];

    if (!strcmp(cmd, "LOGIN") && nt == 3) {
        int a;
        for (a = 0; a < nacc; a++)
            if (!strcmp(acc[a].user, tok[1]) && !strcmp(acc[a].pass, tok[2])) break;
        if (a == nacc) reply(c->fd, "FAIL\n");
        else { c->acct = a; snprintf(out, sizeof out, "OK %s\n", acc[a].user); reply(c->fd, out); }
    } else if (!strcmp(cmd, "SEARCH") && nt == 4) {
        int k = 0;
        size_t o = 0;
        char body[8000] = "";
        for (int i = 0; i < nfl; i++)
            if (!strcmp(fl[i].from, tok[1]) && !strcmp(fl[i].to, tok[2]) && !strcmp(fl[i].date, tok[3]) && fl[i].seats >= 1) {
                o += (size_t)snprintf(body + o, sizeof body - o, "%s %s %s %lld\n", fl[i].code, fl[i].dep, fl[i].arr, fl[i].price);
                k++;
            }
        snprintf(out, sizeof out, "FLIGHTS %d\n%s", k, body);
        reply(c->fd, out);
    } else if (!strcmp(cmd, "QUIT") && nt == 1) {
        reply(c->fd, "BYE\n");
        return 0;
    } else if ((!strcmp(cmd, "BOOK") || !strcmp(cmd, "MYTICKETS") || !strcmp(cmd, "CANCEL") || !strcmp(cmd, "BALANCE")) &&
               c->acct < 0) {
        reply(c->fd, "LOGIN_FIRST\n");
    } else if (!strcmp(cmd, "BOOK") && nt == 3) {
        int f = find_flight(tok[1], tok[2]);
        if (f < 0) reply(c->fd, "NOT_FOUND\n");
        else if (fl[f].seats < 1) reply(c->fd, "NO_SEATS\n");
        else if (acc[c->acct].balance < fl[f].price) reply(c->fd, "NO_MONEY\n");
        else {
            fl[f].seats--;
            acc[c->acct].balance -= fl[f].price;
            Ticket *t = &tk[ntk++];
            t->id = ntk;
            t->acct = c->acct;
            t->flight = f;
            t->alive = 1;
            snprintf(out, sizeof out, "TICKET T%04d\n", t->id);
            reply(c->fd, out);
        }
    } else if (!strcmp(cmd, "MYTICKETS") && nt == 1) {
        int k = 0;
        size_t o = 0;
        char body[8000] = "";
        for (int i = 0; i < ntk; i++)
            if (tk[i].alive && tk[i].acct == c->acct && o < sizeof body - 100) {
                o += (size_t)snprintf(body + o, sizeof body - o, "T%04d %s %s\n", tk[i].id, fl[tk[i].flight].code, fl[tk[i].flight].date);
                k++;
            }
        snprintf(out, sizeof out, "TICKETS %d\n%s", k, body);
        reply(c->fd, out);
    } else if (!strcmp(cmd, "CANCEL") && nt == 2) {
        int id = -1;
        if (strlen(tok[1]) == 5 && tok[1][0] == 'T') {
            id = 0;
            for (int i = 1; i < 5; i++) {
                if (tok[1][i] < '0' || tok[1][i] > '9') { id = -1; break; }
                id = id * 10 + (tok[1][i] - '0');
            }
        }
        if (id < 1 || id > ntk || !tk[id - 1].alive) reply(c->fd, "NOT_FOUND\n");
        else if (tk[id - 1].acct != c->acct) reply(c->fd, "NOT_YOURS\n");
        else {
            Flight *f = &fl[tk[id - 1].flight];
            tk[id - 1].alive = 0;
            f->seats++;
            acc[c->acct].balance += f->price;
            snprintf(out, sizeof out, "REFUNDED %lld\n", f->price);
            reply(c->fd, out);
        }
    } else if (!strcmp(cmd, "BALANCE") && nt == 1) {
        snprintf(out, sizeof out, "BALANCE %lld\n", acc[c->acct].balance);
        reply(c->fd, out);
    } else {
        reply(c->fd, "ERROR\n");
    }
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 3) { fprintf(stderr, "usage: %s <port> <N>\n", argv[0]); return 1; }
    int limit = atoi(argv[2]);
    load_files();
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
                reply(fd, "FULL\n");
                close(fd);
            } else if (fd >= 0) {
                for (int i = 0; i < MAX_CLIENTS; i++)
                    if (clients[i].fd < 0) {
                        clients[i].fd = fd;
                        clients[i].len = 0;
                        clients[i].acct = -1;
                        nclients++;
                        reply(fd, "WELCOME\n");
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
            if (c->len == BUF_SIZE - 1) { reply(c->fd, "ERROR\n"); c->len = 0; }
        }
    }
}
