// Lời giải mẫu: select() một luồng; thời gian đổi ra "số phút kể từ một mốc" bằng công thức ngày dân sự (không phụ thuộc múi giờ).
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
#define MAX_FLIGHTS 200
#define MAX_ACCOUNTS 50
#define MAX_TICKETS 2000
#define MAXTOK 16
#define CHANGE_FEE 200000

typedef struct {
    char code[16], from[8], to[8], date[16], dep[8], arr[8];
    long long price[2];
    int seats[2];
} Flight;
typedef struct { char user[40], pass[40]; long long balance; } Account;
typedef struct { char no[20]; int acct, flight, cls, cancelled; char pax[48]; long long price; } Ticket;
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct; } Client;

static Flight fl[MAX_FLIGHTS];
static Account acc[MAX_ACCOUNTS];
static Ticket tk[MAX_TICKETS];
static int nfl, nacc, ntk;
static long long now_min;
static char now_date[16], now_time[8];
static Client clients[MAX_CLIENTS];

// Số phút kể từ 1970-01-01 00:00 cho "YYYY-MM-DD" và "HH:MM" (thuật toán days_from_civil).
static long long to_minutes(const char *date, const char *hhmm) {
    int y, m, d, hh, mm;
    sscanf(date, "%d-%d-%d", &y, &m, &d);
    sscanf(hhmm, "%d:%d", &hh, &mm);
    y -= m <= 2;
    long long era = (y >= 0 ? y : y - 399) / 400;
    long long yoe = y - era * 400;
    long long doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    long long doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    long long days = era * 146097 + doe - 719468;
    return days * 1440 + hh * 60 + mm;
}

static void load(void) {
    char line[512], u[64], p[64];
    FILE *f = fopen("flights.txt", "r");
    while (f && nfl < MAX_FLIGHTS && fgets(line, sizeof line, f)) {
        Flight *x = &fl[nfl];
        char air[8];
        if (sscanf(line, "%15s %7s %7s %7s %15s %7s %7s %lld %d %lld %d", x->code, air, x->from, x->to, x->date, x->dep, x->arr,
                   &x->price[0], &x->seats[0], &x->price[1], &x->seats[1]) == 11)
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
    f = fopen("tickets.txt", "r");
    char user[40], code[16], date[16], cls[8], status[16];
    while (f && ntk < MAX_TICKETS && fgets(line, sizeof line, f)) {
        Ticket *t = &tk[ntk];
        if (sscanf(line, "%19s %39s %15s %15s %7s %47s %lld %15s", t->no, user, code, date, cls, t->pax, &t->price, status) != 8) continue;
        for (t->acct = 0; t->acct < nacc && strcmp(acc[t->acct].user, user); t->acct++) {}
        for (t->flight = 0; t->flight < nfl && strcmp(fl[t->flight].code, code); t->flight++) {}
        t->cls = !strcmp(cls, "BUS");
        t->cancelled = !strcmp(status, "CANCELLED");
        ntk++;
    }
    if (f) fclose(f);
}

static void reply(int fd, const char *s) { send(fd, s, strlen(s), 0); }

static int find_flight(const char *code) {
    for (int i = 0; i < nfl; i++)
        if (!strcmp(fl[i].code, code)) return i;
    return -1;
}
static int find_ticket(const char *no) {
    for (int i = 0; i < ntk; i++)
        if (!strcmp(tk[i].no, no)) return i;
    return -1;
}
static long long minutes_left(const Flight *f) { return to_minutes(f->date, f->dep) - now_min; }

static void drop(Client *c) { close(c->fd); c->fd = -1; c->len = 0; c->acct = -1; }

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

// Trả về chỉ số vé nếu qua các kiểm tra chung (nt phải = need); ngược lại đã trả lời lỗi và trả -1.
static int pick_ticket(Client *c, char **tok, int nt, int need) {
    if (nt != need) { reply(c->fd, "201 INVALID\n"); return -1; }
    int i = find_ticket(tok[1]);
    if (i < 0) { reply(c->fd, "202 NOT FOUND\n"); return -1; }
    if (tk[i].acct != c->acct) { reply(c->fd, "203 DENIED\n"); return -1; }
    return i;
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
    char out[2048];

    if (!strcmp(cmd, "LOGIN")) {
        int a;
        if (nt != 3 || !valid_user(tok[1]) || !valid_pass(tok[2])) reply(c->fd, "201 INVALID\n");
        else if (c->acct >= 0) reply(c->fd, "207 ALREADY LOGGED IN\n");
        else {
            for (a = 0; a < nacc; a++)
                if (!strcmp(acc[a].user, tok[1]) && !strcmp(acc[a].pass, tok[2])) break;
            if (a == nacc) reply(c->fd, "203 DENIED\n");
            else { c->acct = a; snprintf(out, sizeof out, "100 OK %s\n", acc[a].user); reply(c->fd, out); }
        }
        return 1;
    }
    if (!strcmp(cmd, "QUIT") && nt == 1) { reply(c->fd, "100 OK\n"); return 0; }
    if (!strcmp(cmd, "SEATS")) {
        int f;
        if (nt != 2) reply(c->fd, "201 INVALID\n");
        else if ((f = find_flight(tok[1])) < 0) reply(c->fd, "202 NOT FOUND\n");
        else { snprintf(out, sizeof out, "100 OK %d %d\n", fl[f].seats[0], fl[f].seats[1]); reply(c->fd, out); }
        return 1;
    }
    int needs_login = !strcmp(cmd, "BALANCE") || !strcmp(cmd, "MYTICKETS") || !strcmp(cmd, "VIEW") || !strcmp(cmd, "CANCEL") ||
                      !strcmp(cmd, "CHANGE") || !strcmp(cmd, "PRINT");
    if (!needs_login) { reply(c->fd, "999 UNKNOWN ERROR\n"); return 1; }
    if (c->acct < 0) { reply(c->fd, "204 LOGIN FIRST\n"); return 1; }

    if (!strcmp(cmd, "BALANCE")) {
        if (nt != 1) reply(c->fd, "201 INVALID\n");
        else { snprintf(out, sizeof out, "100 OK %lld\n", acc[c->acct].balance); reply(c->fd, out); }
    } else if (!strcmp(cmd, "MYTICKETS")) {
        if (nt != 1) { reply(c->fd, "201 INVALID\n"); return 1; }
        int k = 0;
        size_t o = 0;
        char body[8000] = "";
        for (int i = 0; i < ntk; i++)
            if (tk[i].acct == c->acct && o < sizeof body - 200) {
                o += (size_t)snprintf(body + o, sizeof body - o, "%s %s %s %s %s %lld %s\n", tk[i].no, fl[tk[i].flight].code,
                                      fl[tk[i].flight].date, tk[i].cls ? "BUS" : "ECO", tk[i].pax, tk[i].price,
                                      tk[i].cancelled ? "CANCELLED" : "PAID");
                k++;
            }
        snprintf(out, sizeof out, "110 TICKETS %d\n", k);
        reply(c->fd, out);
        reply(c->fd, body);
    } else if (!strcmp(cmd, "VIEW")) {
        int i = pick_ticket(c, tok, nt, 2);
        if (i < 0) return 1;
        Flight *f = &fl[tk[i].flight];
        snprintf(out, sizeof out, "100 OK %s %s %s %s %s %lld %s %s %s\n", tk[i].no, f->code, f->date, tk[i].cls ? "BUS" : "ECO", tk[i].pax,
                 tk[i].price, tk[i].cancelled ? "CANCELLED" : "PAID", f->dep, f->arr);
        reply(c->fd, out);
    } else if (!strcmp(cmd, "CANCEL")) {
        int i = pick_ticket(c, tok, nt, 2);
        if (i < 0) return 1;
        Flight *f = &fl[tk[i].flight];
        long long left = minutes_left(f);
        if (tk[i].cancelled) { reply(c->fd, "209 ALREADY CANCELLED\n"); return 1; }
        if (left <= 0) { reply(c->fd, "210 TOO LATE\n"); return 1; }
        int pct = left >= 72 * 60 ? 90 : left >= 24 * 60 ? 70 : 30;
        long long refund = tk[i].price * pct / 100;
        acc[c->acct].balance += refund;
        f->seats[tk[i].cls]++;
        tk[i].cancelled = 1;
        snprintf(out, sizeof out, "100 OK REFUNDED %lld\n", refund);
        reply(c->fd, out);
    } else if (!strcmp(cmd, "CHANGE")) {
        int i = pick_ticket(c, tok, nt, 3);
        if (i < 0) return 1;
        Flight *old = &fl[tk[i].flight];
        if (tk[i].cancelled) { reply(c->fd, "209 ALREADY CANCELLED\n"); return 1; }
        if (!strcmp(tok[2], old->code)) { reply(c->fd, "201 INVALID\n"); return 1; }
        if (minutes_left(old) < 180) { reply(c->fd, "210 TOO LATE\n"); return 1; }
        int nf = find_flight(tok[2]);
        if (nf < 0) { reply(c->fd, "202 NOT FOUND\n"); return 1; }
        Flight *nw = &fl[nf];
        if (strcmp(nw->from, old->from) || strcmp(nw->to, old->to)) { reply(c->fd, "211 DIFFERENT ROUTE\n"); return 1; }
        if (minutes_left(nw) <= 0) { reply(c->fd, "210 TOO LATE\n"); return 1; }
        if (nw->seats[tk[i].cls] < 1) { reply(c->fd, "205 NO SEATS\n"); return 1; }
        long long delta = nw->price[tk[i].cls] - tk[i].price + CHANGE_FEE;
        if (delta > acc[c->acct].balance) { reply(c->fd, "206 PAYMENT FAILED\n"); return 1; }
        acc[c->acct].balance -= delta;
        old->seats[tk[i].cls]++;
        nw->seats[tk[i].cls]--;
        tk[i].flight = nf;
        tk[i].price = nw->price[tk[i].cls];
        snprintf(out, sizeof out, "100 OK CHANGED %s %lld\n", tk[i].no, delta);
        reply(c->fd, out);
    } else if (!strcmp(cmd, "PRINT")) {
        int i = pick_ticket(c, tok, nt, 2);
        if (i < 0) return 1;
        Flight *f = &fl[tk[i].flight];
        char body[1024];
        int bl = snprintf(body, sizeof body,
                          "===== VE DIEN TU =====\nSo ve: %s\nHanh khach: %s\nChuyen bay: %s %s -> %s\nNgay: %s %s - %s\nHang: %s\n"
                          "Gia ve: %lld\nTrang thai: %s\nIn luc: %s %s\n",
                          tk[i].no, tk[i].pax, f->code, f->from, f->to, f->date, f->dep, f->arr, tk[i].cls ? "BUS" : "ECO", tk[i].price,
                          tk[i].cancelled ? "CANCELLED" : "PAID", now_date, now_time);
        snprintf(out, sizeof out, "120 FILE %d\n", bl);
        reply(c->fd, out);
        send(c->fd, body, (size_t)bl, 0);
    }
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 4) { fprintf(stderr, "usage: %s <port> <YYYY-MM-DD> <HH:MM>\n", argv[0]); return 1; }
    signal(SIGPIPE, SIG_IGN);
    snprintf(now_date, sizeof now_date, "%s", argv[2]);
    snprintf(now_time, sizeof now_time, "%s", argv[3]);
    now_min = to_minutes(now_date, now_time);
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
                    if (clients[i].fd < 0) { clients[i].fd = fd; clients[i].len = 0; clients[i].acct = -1; placed = 1; }
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
