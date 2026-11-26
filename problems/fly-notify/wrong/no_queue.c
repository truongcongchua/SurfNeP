// Sai có chủ đích: thông báo chỉ gửi cho khách đang online; khách offline bị mất thông báo (không có hàng đợi).
// Lời giải mẫu: select() một luồng; hàng đợi thông báo theo tài khoản (mảng cấp phát động).
#include <arpa/inet.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_CLIENTS 64
#define BUF_SIZE 2048
#define MAX_FLIGHTS 100
#define MAX_ACCOUNTS 50
#define MAX_TICKETS 1000
#define MAXTOK 16

enum { ON_TIME, DELAYED, RESCHEDULED, CANCELLED };

typedef struct { char code[16]; int status, delay; char date[16], dep[8], arr[8]; } Flight;
typedef struct { char user[40], pass[40]; char (*q)[128]; int nq, cap; } Account;
typedef struct { int acct, flight; } Ticket;
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct, admin; } Client;

static Flight fl[MAX_FLIGHTS];
static Account acc[MAX_ACCOUNTS];
static Ticket tk[MAX_TICKETS];
static int nfl, nacc, ntk;
static Client clients[MAX_CLIENTS];
static const char *admin_key;

static void load(void) {
    char line[512];
    FILE *f = fopen("flights.txt", "r");
    while (f && nfl < MAX_FLIGHTS && fgets(line, sizeof line, f)) {
        char air[8], from[8], to[8];
        long long a;
        int b;
        Flight *x = &fl[nfl];
        if (sscanf(line, "%15s %7s %7s %7s %15s %7s %7s %lld %d", x->code, air, from, to, x->date, x->dep, x->arr, &a, &b) == 9) nfl++;
    }
    if (f) fclose(f);
    f = fopen("accounts.txt", "r");
    while (f && nacc < MAX_ACCOUNTS && fscanf(f, "%39s %39s", acc[nacc].user, acc[nacc].pass) == 2) nacc++;
    if (f) fclose(f);
    f = fopen("tickets.txt", "r");
    char no[24], user[40], code[16], date[16], cls[8], pax[48], status[16];
    long long price;
    while (f && ntk < MAX_TICKETS && fgets(line, sizeof line, f)) {
        if (sscanf(line, "%23s %39s %15s %15s %7s %47s %lld %15s", no, user, code, date, cls, pax, &price, status) != 8) continue;
        if (strcmp(status, "PAID")) continue;
        int a, b;
        for (a = 0; a < nacc && strcmp(acc[a].user, user); a++) {}
        for (b = 0; b < nfl && strcmp(fl[b].code, code); b++) {}
        if (a < nacc && b < nfl) { tk[ntk].acct = a; tk[ntk].flight = b; ntk++; }
    }
    if (f) fclose(f);
}

static int is_digit(char c) { return c >= '0' && c <= '9'; }
static int leap(int y) { return (y % 4 == 0 && y % 100 != 0) || y % 400 == 0; }
static int valid_date(const char *s) {
    if (strlen(s) != 10 || s[4] != '-' || s[7] != '-') return 0;
    for (int i = 0; i < 10; i++)
        if (i != 4 && i != 7 && !is_digit(s[i])) return 0;
    int y = (s[0] - '0') * 1000 + (s[1] - '0') * 100 + (s[2] - '0') * 10 + (s[3] - '0');
    int m = (s[5] - '0') * 10 + (s[6] - '0'), d = (s[8] - '0') * 10 + (s[9] - '0');
    static const int dim[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if (y < 1900 || y > 2100 || m < 1 || m > 12 || d < 1) return 0;
    return d <= dim[m - 1] + (m == 2 && leap(y));
}
static int valid_time(const char *s) {
    if (strlen(s) != 5 || !is_digit(s[0]) || !is_digit(s[1]) || s[2] != ':' || !is_digit(s[3]) || !is_digit(s[4])) return 0;
    int h = (s[0] - '0') * 10 + (s[1] - '0'), m = (s[3] - '0') * 10 + (s[4] - '0');
    return h <= 23 && m <= 59;
}
static int valid_user(const char *s) {
    size_t n = strlen(s);
    if (n < 1 || n > 32) return 0;
    for (size_t i = 0; i < n; i++)
        if (!((s[i] >= 'a' && s[i] <= 'z') || is_digit(s[i]))) return 0;
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
static int find_flight(const char *code) {
    for (int i = 0; i < nfl; i++)
        if (!strcmp(fl[i].code, code)) return i;
    return -1;
}
static void drop(Client *c) { close(c->fd); c->fd = -1; c->len = 0; c->acct = -1; c->admin = 0; }

// Gửi thông báo cho mọi khách có vé PAID trên chuyến f; trả về số khách khác nhau.
static int notify(int f, const char *msg) {
    int count = 0;
    for (int a = 0; a < nacc; a++) {
        int holds = 0;
        for (int t = 0; t < ntk && !holds; t++)
            if (tk[t].acct == a && tk[t].flight == f) holds = 1;
        if (!holds) continue;
        count++;
        int online = 0;
        for (int i = 0; i < MAX_CLIENTS; i++)
            if (clients[i].fd >= 0 && clients[i].acct == a) { reply(clients[i].fd, msg); online = 1; }
        if (!online) {
            Account *x = &acc[a];
            if (x->nq == x->cap) {
                x->cap = x->cap ? x->cap * 2 : 16;
                x->q = realloc(x->q, (size_t)x->cap * sizeof x->q[0]);
            }
            (void)x;
        }
    }
    return count;
}

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
    const char *cmd = tok[0];
    char out[256];

    if (!strcmp(cmd, "LOGIN")) {
        int a;
        if (nt != 3 || !valid_user(tok[1]) || !valid_pass(tok[2])) reply(c->fd, "201 INVALID\n");
        else if (c->acct >= 0) reply(c->fd, "207 ALREADY LOGGED IN\n");
        else {
            for (a = 0; a < nacc; a++)
                if (!strcmp(acc[a].user, tok[1]) && !strcmp(acc[a].pass, tok[2])) break;
            if (a == nacc) { reply(c->fd, "203 DENIED\n"); return 1; }
            int online = 0;
            for (int i = 0; i < MAX_CLIENTS; i++)
                if (clients[i].fd >= 0 && clients[i].acct == a) online = 1;
            c->acct = a;
            snprintf(out, sizeof out, "100 OK %s\n", acc[a].user);
            reply(c->fd, out);
            if (!online) {
                for (int k = 0; k < acc[a].nq; k++) reply(c->fd, acc[a].q[k]);
                acc[a].nq = 0;
            }
        }
    } else if (!strcmp(cmd, "ADMIN")) {
        if (nt != 2) reply(c->fd, "201 INVALID\n");
        else if (strcmp(tok[1], admin_key)) reply(c->fd, "203 DENIED\n");
        else { c->admin = 1; reply(c->fd, "100 OK\n"); }
    } else if (!strcmp(cmd, "STATUS")) {
        int f;
        if (nt != 2) reply(c->fd, "201 INVALID\n");
        else if ((f = find_flight(tok[1])) < 0) reply(c->fd, "202 NOT FOUND\n");
        else {
            Flight *x = &fl[f];
            if (x->status == ON_TIME) snprintf(out, sizeof out, "100 OK ON_TIME\n");
            else if (x->status == DELAYED) snprintf(out, sizeof out, "100 OK DELAYED %d\n", x->delay);
            else if (x->status == RESCHEDULED) snprintf(out, sizeof out, "100 OK RESCHEDULED %s %s %s\n", x->date, x->dep, x->arr);
            else snprintf(out, sizeof out, "100 OK CANCELLED\n");
            reply(c->fd, out);
        }
    } else if (!strcmp(cmd, "DELAY") || !strcmp(cmd, "RESCHEDULE") || !strcmp(cmd, "CANCELFLIGHT")) {
        if (!c->admin) { reply(c->fd, "203 DENIED\n"); return 1; }
        int kind = !strcmp(cmd, "DELAY") ? 0 : !strcmp(cmd, "RESCHEDULE") ? 1 : 2;
        int need = kind == 0 ? 3 : kind == 1 ? 5 : 2;
        int minutes = 0;
        if (nt != need) { reply(c->fd, "201 INVALID\n"); return 1; }
        if (kind == 0) {
            size_t l = strlen(tok[2]);
            int ok = l >= 1 && l <= 4 && tok[2][0] != '0';
            for (size_t i = 0; ok && i < l; i++)
                if (!is_digit(tok[2][i])) ok = 0;
            if (ok) minutes = atoi(tok[2]);
            if (!ok || minutes < 1 || minutes > 1440) { reply(c->fd, "201 INVALID\n"); return 1; }
        }
        if (kind == 1 && (!valid_date(tok[2]) || !valid_time(tok[3]) || !valid_time(tok[4]))) { reply(c->fd, "201 INVALID\n"); return 1; }
        int f = find_flight(tok[1]);
        if (f < 0) { reply(c->fd, "202 NOT FOUND\n"); return 1; }
        Flight *x = &fl[f];
        if (x->status == CANCELLED) { reply(c->fd, "209 ALREADY CANCELLED\n"); return 1; }
        char msg[160];
        if (kind == 0) {
            x->status = DELAYED;
            x->delay = minutes;
            snprintf(msg, sizeof msg, "301 NOTIFY DELAY %s %d\n", x->code, minutes);
        } else if (kind == 1) {
            x->status = RESCHEDULED;
            snprintf(x->date, sizeof x->date, "%s", tok[2]);
            snprintf(x->dep, sizeof x->dep, "%s", tok[3]);
            snprintf(x->arr, sizeof x->arr, "%s", tok[4]);
            snprintf(msg, sizeof msg, "301 NOTIFY RESCHEDULE %s %s %s %s\n", x->code, tok[2], tok[3], tok[4]);
        } else {
            x->status = CANCELLED;
            snprintf(msg, sizeof msg, "301 NOTIFY CANCEL %s\n", x->code);
        }
        int k = notify(f, msg);
        snprintf(out, sizeof out, "100 OK %d\n", k);
        reply(c->fd, out);
    } else if (!strcmp(cmd, "QUIT") && nt == 1) {
        reply(c->fd, "100 OK\n");
        return 0;
    } else {
        reply(c->fd, "999 UNKNOWN ERROR\n");
    }
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 3) { fprintf(stderr, "usage: %s <port> <admin-key>\n", argv[0]); return 1; }
    signal(SIGPIPE, SIG_IGN);
    admin_key = argv[2];
    load();
    int ls = socket(AF_INET, SOCK_STREAM, 0), yes = 1;
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
            if (fd >= 0) {
                int placed = 0;
                for (int i = 0; i < MAX_CLIENTS && !placed; i++)
                    if (clients[i].fd < 0) { clients[i].fd = fd; clients[i].len = 0; clients[i].acct = -1; clients[i].admin = 0; placed = 1; }
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
