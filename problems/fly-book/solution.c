// Lời giải mẫu: select() một luồng (không cần mutex), hết hạn giữ chỗ được xét "lười" ở đầu mỗi lệnh.
#include <arpa/inet.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define MAX_CLIENTS 64
#define BUF_SIZE 2048
#define MAX_FLIGHTS 100
#define MAX_ACCOUNTS 100
#define MAX_BOOKINGS 20000
#define MAXTOK 16

enum { HOLD, PAID, EXPIRED, GONE };

typedef struct {
    char code[16], date[16];
    long long price[2];  // [0] = ECO, [1] = BUS
    int seats[2];
} Flight;
typedef struct { char user[40], pass[40]; long long balance; } Account;
typedef struct {
    char pnr[8];
    int acct, flight, cls, pax, state, sid;
    long long amount;
    time_t expire;
} Booking;
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct; int sid; } Client;

static Flight fl[MAX_FLIGHTS];
static Account acc[MAX_ACCOUNTS];
static Booking bk[MAX_BOOKINGS];
static int nfl, nacc, nbk, nclients, next_sid = 1, hold_secs;
static Client clients[MAX_CLIENTS];

static void load_files(void) {
    char line[512], code[16], air[8], from[8], to[8], date[16], u[64], p[64];
    long long ep, bp;
    int es, bs;
    FILE *f = fopen("flights.txt", "r");
    while (f && nfl < MAX_FLIGHTS && fgets(line, sizeof line, f))
        if (sscanf(line, "%15s %7s %7s %7s %15s %*s %*s %lld %d %lld %d", code, air, from, to, date, &ep, &es, &bp, &bs) == 9) {
            strcpy(fl[nfl].code, code);
            strcpy(fl[nfl].date, date);
            fl[nfl].price[0] = ep; fl[nfl].seats[0] = es;
            fl[nfl].price[1] = bp; fl[nfl].seats[1] = bs;
            nfl++;
        }
    if (f) fclose(f);
    f = fopen("accounts.txt", "r");
    while (f && nacc < MAX_ACCOUNTS && fscanf(f, "%39s %39s", u, p) == 2) {
        strcpy(acc[nacc].user, u);
        strcpy(acc[nacc].pass, p);
        nacc++;
    }
    if (f) fclose(f);
    f = fopen("wallets.txt", "r");
    long long bal;
    while (f && fscanf(f, "%39s %lld", u, &bal) == 2)
        for (int i = 0; i < nacc; i++)
            if (!strcmp(acc[i].user, u)) acc[i].balance = bal;
    if (f) fclose(f);
}

static int is_digit(char c) { return c >= '0' && c <= '9'; }
static int leap(int y) { return (y % 4 == 0 && y % 100 != 0) || y % 400 == 0; }
static int valid_date(const char *s) {
    if (strlen(s) != 10 || s[4] != '-' || s[7] != '-') return 0;
    for (int i = 0; i < 10; i++)
        if (i != 4 && i != 7 && !is_digit(s[i])) return 0;
    int y = (s[0] - '0') * 1000 + (s[1] - '0') * 100 + (s[2] - '0') * 10 + (s[3] - '0');
    int m = (s[5] - '0') * 10 + (s[6] - '0');
    int d = (s[8] - '0') * 10 + (s[9] - '0');
    static const int dim[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if (y < 1900 || y > 2100 || m < 1 || m > 12 || d < 1) return 0;
    return d <= dim[m - 1] + (m == 2 && leap(y));
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

static int luhn_ok(const char *s) {
    if (strlen(s) != 16) return 0;
    int sum = 0;
    for (int i = 0; i < 16; i++) {
        if (!is_digit(s[15 - i])) return 0;
        int d = s[15 - i] - '0';
        if (i % 2) { d *= 2; if (d > 9) d -= 9; }
        sum += d;
    }
    return sum % 10 == 0;
}

static int card_ok(const char *num, const char *exp, const char *cvv) {
    if (!luhn_ok(num)) return 0;
    if (strlen(cvv) != 3 || !is_digit(cvv[0]) || !is_digit(cvv[1]) || !is_digit(cvv[2])) return 0;
    if (strlen(exp) != 5 || exp[2] != '/' || !is_digit(exp[0]) || !is_digit(exp[1]) || !is_digit(exp[3]) || !is_digit(exp[4]))
        return 0;
    int mm = (exp[0] - '0') * 10 + (exp[1] - '0'), yy = (exp[3] - '0') * 10 + (exp[4] - '0');
    if (mm < 1 || mm > 12) return 0;
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    int cy = t->tm_year + 1900, cm = t->tm_mon + 1;
    return 2000 + yy > cy || (2000 + yy == cy && mm >= cm);
}

static void reply(int fd, const char *s) { send(fd, s, strlen(s), 0); }

static void expire_holds(void) {
    time_t now = time(NULL);
    for (int i = 0; i < nbk; i++)
        if (bk[i].state == HOLD && bk[i].expire <= now) {
            fl[bk[i].flight].seats[bk[i].cls] += bk[i].pax;
            bk[i].state = EXPIRED;
        }
}

static int find_booking(const char *pnr) {
    for (int i = 0; i < nbk; i++)
        if (bk[i].state != GONE && strcmp(bk[i].pnr, pnr) == 0) return i;
    return -1;
}

static int pnr_used(const char *pnr) {
    for (int i = 0; i < nbk; i++)
        if (strcmp(bk[i].pnr, pnr) == 0) return 1;
    return 0;
}

static int find_flight(const char *code, const char *date) {
    for (int i = 0; i < nfl; i++)
        if (!strcmp(fl[i].code, code) && !strcmp(fl[i].date, date)) return i;
    return -1;
}

static void release_session(int sid) {
    for (int i = 0; i < nbk; i++)
        if (bk[i].state == HOLD && bk[i].sid == sid) {
            fl[bk[i].flight].seats[bk[i].cls] += bk[i].pax;
            bk[i].state = GONE;
        }
}

static void drop(Client *c) {
    expire_holds();
    release_session(c->sid);
    close(c->fd);
    c->fd = -1;
    c->len = 0;
    c->acct = -1;
    nclients--;
}

// Trả về 0 nếu phải đóng kết nối.
static int handle(Client *c, char *line) {
    expire_holds();
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
    char out[160];
    const char *cmd = tok[0];

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
    } else if (!strcmp(cmd, "SEATS")) {
        int f;
        if (nt != 3) reply(c->fd, "201 INVALID\n");
        else if ((f = find_flight(tok[1], tok[2])) < 0) reply(c->fd, "202 NOT FOUND\n");
        else { snprintf(out, sizeof out, "100 OK %d %d\n", fl[f].seats[0], fl[f].seats[1]); reply(c->fd, out); }
    } else if (!strcmp(cmd, "QUIT")) {
        if (nt != 1) { reply(c->fd, "201 INVALID\n"); return 1; }
        reply(c->fd, "100 OK\n");
        return 0;
    } else if (!strcmp(cmd, "BALANCE") || !strcmp(cmd, "BOOK") || !strcmp(cmd, "PAY") || !strcmp(cmd, "RELEASE")) {
        if (c->acct < 0) { reply(c->fd, "204 LOGIN FIRST\n"); return 1; }
        if (!strcmp(cmd, "BALANCE")) {
            if (nt != 1) reply(c->fd, "201 INVALID\n");
            else { snprintf(out, sizeof out, "100 OK %lld\n", acc[c->acct].balance); reply(c->fd, out); }
        } else if (!strcmp(cmd, "BOOK")) {
            if (nt != 5 || !valid_date(tok[2]) || (strcmp(tok[3], "ECO") && strcmp(tok[3], "BUS")) || strlen(tok[4]) != 1 ||
                tok[4][0] < '1' || tok[4][0] > '9') { reply(c->fd, "201 INVALID\n"); return 1; }
            int cls = !strcmp(tok[3], "BUS");
            int f = find_flight(tok[1], tok[2]), pax = tok[4][0] - '0';
            if (f < 0) reply(c->fd, "202 NOT FOUND\n");
            else if (fl[f].seats[cls] < pax || nbk >= MAX_BOOKINGS) reply(c->fd, "205 NO SEATS\n");
            else {
                char pnr[8];
                do {
                    for (int i = 0; i < 6; i++) {
                        int r = rand() % 36;
                        pnr[i] = r < 26 ? 'A' + r : '0' + (r - 26);
                    }
                    pnr[6] = 0;
                } while (pnr_used(pnr));
                Booking *b = &bk[nbk++];
                strcpy(b->pnr, pnr);
                b->acct = c->acct; b->flight = f; b->cls = cls; b->pax = pax; b->state = HOLD; b->sid = c->sid;
                b->amount = fl[f].price[cls] * pax;
                b->expire = time(NULL) + hold_secs;
                fl[f].seats[cls] -= pax;
                struct tm *t = localtime(&b->expire);
                snprintf(out, sizeof out, "100 OK HOLD %s %lld %02d:%02d:%02d\n", b->pnr, b->amount, t->tm_hour, t->tm_min, t->tm_sec);
                reply(c->fd, out);
            }
        } else {  // PAY / RELEASE
            int pay = !strcmp(cmd, "PAY");
            int wallet = pay && nt == 3 && !strcmp(tok[2], "WALLET");
            int card = pay && nt == 6 && !strcmp(tok[2], "CARD");
            if ((pay && !wallet && !card) || (!pay && nt != 2)) { reply(c->fd, "201 INVALID\n"); return 1; }
            int i = find_booking(tok[1]);
            if (i < 0) reply(c->fd, "202 NOT FOUND\n");
            else if (bk[i].acct != c->acct) reply(c->fd, "203 DENIED\n");
            else if (bk[i].state == PAID) reply(c->fd, "209 ALREADY PAID\n");
            else if (bk[i].state == EXPIRED) reply(c->fd, "208 EXPIRED\n");
            else if (!pay) {
                fl[bk[i].flight].seats[bk[i].cls] += bk[i].pax;
                bk[i].state = GONE;
                reply(c->fd, "100 OK\n");
            } else if (wallet ? acc[c->acct].balance < bk[i].amount : !card_ok(tok[3], tok[4], tok[5])) {
                reply(c->fd, "206 PAYMENT FAILED\n");
            } else {
                if (wallet) acc[c->acct].balance -= bk[i].amount;
                bk[i].state = PAID;
                snprintf(out, sizeof out, "100 OK PAID %s\n", bk[i].pnr);
                reply(c->fd, out);
            }
        }
    } else {
        reply(c->fd, "999 UNKNOWN ERROR\n");
    }
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 4) { fprintf(stderr, "usage: %s <port> <N> <T>\n", argv[0]); return 1; }
    int limit = atoi(argv[2]);
    hold_secs = atoi(argv[3]);
    signal(SIGPIPE, SIG_IGN);
    srand((unsigned)time(NULL) ^ (unsigned)getpid());
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
        struct timeval tv = {1, 0};  // thức dậy mỗi giây để trả ghế hết hạn dù không ai gửi lệnh
        int r = select(maxfd + 1, &rd, NULL, NULL, &tv);
        if (r < 0) { perror("select"); return 1; }
        expire_holds();
        if (r == 0) continue;

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
                        clients[i].sid = next_sid++;
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
