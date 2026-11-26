// Lời giải mẫu: select() + bộ đệm dòng riêng mỗi client; dữ liệu chuyến bay nạp một lần lúc khởi động.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_FLIGHTS 1000
#define MAX_CLIENTS 64
#define BUF_SIZE 2048
#define MAXTOK 32

typedef struct {
    char code[16], airline[8], from[8], to[8], date[16], dep[8], arr[8];
    long long eco_price, bus_price;
    int eco_seats, bus_seats;
} Flight;

typedef struct { int fd; char buf[BUF_SIZE]; size_t len; } Client;

static Flight fl[MAX_FLIGHTS];
static int nfl = 0;
static Client clients[MAX_CLIENTS];

static void load_flights(void) {
    FILE *f = fopen("flights.txt", "r");
    if (!f) { perror("flights.txt"); exit(1); }
    char line[512];
    while (nfl < MAX_FLIGHTS && fgets(line, sizeof line, f)) {
        Flight *x = &fl[nfl];
        if (sscanf(line, "%15s %7s %7s %7s %15s %7s %7s %lld %d %lld %d", x->code, x->airline, x->from, x->to,
                   x->date, x->dep, x->arr, &x->eco_price, &x->eco_seats, &x->bus_price, &x->bus_seats) == 11)
            nfl++;
    }
    fclose(f);
}

static int is_upper(char c) { return c >= 'A' && c <= 'Z'; }
static int is_digit(char c) { return c >= '0' && c <= '9'; }
static int airport(const char *s) {
    return strlen(s) == 3 && is_upper(s[0]) && is_upper(s[1]) && is_upper(s[2]);
}
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
static int valid_search(char **t, int nt) {
    if (nt != 6 && nt != 7) return 0;
    if (!airport(t[1]) || !airport(t[2]) || strcmp(t[1], t[2]) == 0) return 0;
    if (!valid_date(t[3])) return 0;
    if (strlen(t[4]) != 1 || t[4][0] < '1' || t[4][0] > '9') return 0;
    if (strcmp(t[5], "ECO") != 0 && strcmp(t[5], "BUS") != 0) return 0;
    if (nt == 7 && (!valid_date(t[6]) || strcmp(t[6], t[3]) < 0)) return 0;
    return 1;
}

// Ghi vào out danh sách chuyến của một chiều; trả về độ dài đã ghi.
static size_t list_flights(char *out, size_t cap, const char *tag, const char *from, const char *to, const char *date,
                           int pax, int bus) {
    int idx[MAX_FLIGHTS], k = 0;
    for (int i = 0; i < nfl; i++) {
        int seats = bus ? fl[i].bus_seats : fl[i].eco_seats;
        if (!strcmp(fl[i].from, from) && !strcmp(fl[i].to, to) && !strcmp(fl[i].date, date) && seats >= pax)
            idx[k++] = i;
    }
    size_t o = (size_t)snprintf(out, cap, "%s %d\n", tag, k);
    for (int j = 0; j < k; j++) {
        Flight *x = &fl[idx[j]];
        long long price = bus ? x->bus_price : x->eco_price;
        o += (size_t)snprintf(out + o, cap - o, "%s %s %s %s %lld\n", x->code, x->airline, x->dep, x->arr, price * pax);
    }
    return o;
}

static void reply(int fd, const char *s, size_t n) { send(fd, s, n, 0); }
static void reply_str(int fd, const char *s) { reply(fd, s, strlen(s)); }

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

    if (n > 0 && strcmp(tok[0], "QUIT") == 0) {
        if (nt != 1) { reply_str(c->fd, "201 INVALID\n"); return 1; }
        reply_str(c->fd, "100 OK\n");
        return 0;
    }
    if (n > 0 && strcmp(tok[0], "SEARCH") == 0) {
        if (nt > MAXTOK || !valid_search(tok, nt)) { reply_str(c->fd, "201 INVALID\n"); return 1; }
        int pax = tok[4][0] - '0', bus = strcmp(tok[5], "BUS") == 0;
        static char out[MAX_FLIGHTS * 64 * 2 + 256];
        size_t o = list_flights(out, sizeof out, "110 FLIGHTS", tok[1], tok[2], tok[3], pax, bus);
        if (nt == 7) o += list_flights(out + o, sizeof out - o, "111 RETURN", tok[2], tok[1], tok[6], pax, bus);
        reply(c->fd, out, o);
        return 1;
    }
    reply_str(c->fd, "999 UNKNOWN ERROR\n");
    return 1;
}

static void drop(Client *c) { close(c->fd); c->fd = -1; c->len = 0; }

int main(int argc, char *argv[]) {
    if (argc != 2) { fprintf(stderr, "usage: %s <port>\n", argv[0]); return 1; }
    load_flights();
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
                    if (clients[i].fd < 0) { clients[i].fd = fd; clients[i].len = 0; placed = 1; }
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
            if (c->len == BUF_SIZE - 1) { reply_str(c->fd, "999 UNKNOWN ERROR\n"); c->len = 0; }
        }
    }
}
