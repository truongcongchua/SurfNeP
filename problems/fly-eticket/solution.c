// Lời giải mẫu: select() cho client; khi ISSUE, server làm client SMTP (blocking connect, select có timeout 2s cho mỗi phản hồi).
#include <arpa/inet.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define MAX_CLIENTS 64
#define BUF_SIZE 2048
#define MAX_ACCOUNTS 100
#define MAXTOK 16

typedef struct { char user[40], pass[40], email[80]; } Account;
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct; } Client;

static Account acc[MAX_ACCOUNTS];
static int nacc;
static Client clients[MAX_CLIENTS];
static long next_serial;
static char smtp_ip[64];
static int smtp_port;

static void load(void) {
    FILE *f = fopen("accounts.txt", "r");
    while (f && nacc < MAX_ACCOUNTS && fscanf(f, "%39s %39s %79s", acc[nacc].user, acc[nacc].pass, acc[nacc].email) == 3) nacc++;
    if (f) fclose(f);
    long lines = 0;
    char line[512];
    f = fopen("tickets.txt", "r");
    while (f && fgets(line, sizeof line, f)) lines++;
    if (f) fclose(f);
    next_serial = lines + 1;
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
static int valid_flight(const char *s) {
    size_t n = strlen(s);
    if (n < 3 || n > 6 || s[0] < 'A' || s[0] > 'Z' || s[1] < 'A' || s[1] > 'Z') return 0;
    for (size_t i = 2; i < n; i++)
        if (!is_digit(s[i])) return 0;
    return 1;
}
static int valid_name(const char *s) {
    size_t n = strlen(s);
    if (n < 1 || n > 40) return 0;
    for (size_t i = 0; i < n; i++)
        if (!((s[i] >= 'A' && s[i] <= 'Z') || (s[i] >= 'a' && s[i] <= 'z') || s[i] == '_')) return 0;
    return 1;
}

static void reply(int fd, const char *s) { send(fd, s, strlen(s), 0); }

// ---- SMTP ----
static char sb[4096];
static size_t slen, spos;

// Đọc một dòng SMTP với timeout 2s; trả về 0 nếu lỗi/hết giờ.
static int smtp_line(int s, char *out, size_t cap) {
    size_t o = 0;
    for (;;) {
        if (spos == slen) {
            fd_set rd;
            FD_ZERO(&rd);
            FD_SET(s, &rd);
            struct timeval tv = {2, 0};
            if (select(s + 1, &rd, NULL, NULL, &tv) <= 0) return 0;
            ssize_t n = recv(s, sb, sizeof sb, 0);
            if (n <= 0) return 0;
            slen = (size_t)n;
            spos = 0;
        }
        char c = sb[spos++];
        if (c == '\n') break;
        if (o + 1 < cap) out[o++] = c;
    }
    if (o && out[o - 1] == '\r') o--;
    out[o] = 0;
    return 1;
}

// Đọc phản hồi (có thể nhiều dòng), kiểm tra mã đầu tiên.
static int smtp_expect(int s, const char *code) {
    char line[512];
    for (;;) {
        if (!smtp_line(s, line, sizeof line)) return 0;
        if (strlen(line) < 4 || strncmp(line, code, 3) != 0) return 0;
        if (line[3] == ' ') return 1;
        if (line[3] != '-') return 0;
    }
}

static int smtp_cmd(int s, const char *cmd, const char *code) {
    char buf[1024];
    int n = snprintf(buf, sizeof buf, "%s\r\n", cmd);
    send(s, buf, (size_t)n, 0);
    return smtp_expect(s, code);
}

static int smtp_send(const char *email, const char *msg, size_t msglen) {
    slen = spos = 0;
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = inet_addr(smtp_ip);
    a.sin_port = htons(smtp_port);
    if (connect(s, (struct sockaddr *)&a, sizeof a) < 0) { close(s); return 0; }
    char cmd[256];
    int ok = smtp_expect(s, "220") && smtp_cmd(s, "HELO fly.local", "250") && smtp_cmd(s, "MAIL FROM:<noreply@fly.local>", "250");
    if (ok) {
        snprintf(cmd, sizeof cmd, "RCPT TO:<%s>", email);
        ok = smtp_cmd(s, cmd, "250") && smtp_cmd(s, "DATA", "354");
    }
    if (ok) {
        send(s, msg, msglen, 0);
        ok = smtp_cmd(s, ".", "250");
    }
    send(s, "QUIT\r\n", 6, 0);
    close(s);
    return ok;
}

static void drop(Client *c) { close(c->fd); c->fd = -1; c->len = 0; c->acct = -1; }

static void issue(Client *c, char **tok) {
    const char *flight = tok[1], *date = tok[2], *cls = tok[3], *pax = tok[4];
    const char *code = !strncmp(flight, "VN", 2) ? "738" : !strncmp(flight, "VJ", 2) ? "978" : !strncmp(flight, "QH", 2) ? "126"
                       : !strncmp(flight, "BL", 2) ? "550" : "000";
    char ticket[32];
    snprintf(ticket, sizeof ticket, "%s%010ld", code, next_serial++);
    FILE *f = fopen("tickets.txt", "a");
    if (f) {
        fprintf(f, "%s %s %s %s %s %s\n", ticket, acc[c->acct].user, flight, date, cls, pax);
        fclose(f);
    }
    char msg[1024];
    int ml = snprintf(msg, sizeof msg,
                      "From: noreply@fly.local\r\nTo: %s\r\nSubject: Ve dien tu %s\r\n\r\nTicket: %s\r\nFlight: %s %s %s\r\nPassenger: %s\r\n",
                      acc[c->acct].email, ticket, ticket, flight, date, cls, pax);
    int mailed = smtp_send(acc[c->acct].email, msg, (size_t)ml);

    char path[256];
    mkdir("outbox", 0777);
    snprintf(path, sizeof path, "outbox/%s", acc[c->acct].user);
    mkdir(path, 0777);
    snprintf(path, sizeof path, "outbox/%s/%s.eml", acc[c->acct].user, ticket);
    f = fopen(path, "wb");
    if (f) { fwrite(msg, 1, (size_t)ml, f); fclose(f); }

    char out[128];
    snprintf(out, sizeof out, "300 TICKET %s\n", ticket);
    for (int i = 0; i < MAX_CLIENTS; i++)
        if (clients[i].fd >= 0 && &clients[i] != c && clients[i].acct == c->acct) reply(clients[i].fd, out);
    snprintf(out, sizeof out, mailed ? "100 OK %s\n" : "100 OK %s MAIL_FAILED\n", ticket);
    reply(c->fd, out);
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
    char out[128];
    if (!strcmp(tok[0], "LOGIN")) {
        int a;
        if (nt != 3 || !valid_user(tok[1]) || !valid_pass(tok[2])) reply(c->fd, "201 INVALID\n");
        else if (c->acct >= 0) reply(c->fd, "207 ALREADY LOGGED IN\n");
        else {
            for (a = 0; a < nacc; a++)
                if (!strcmp(acc[a].user, tok[1]) && !strcmp(acc[a].pass, tok[2])) break;
            if (a == nacc) reply(c->fd, "203 DENIED\n");
            else { c->acct = a; snprintf(out, sizeof out, "100 OK %s\n", acc[a].user); reply(c->fd, out); }
        }
    } else if (!strcmp(tok[0], "ISSUE")) {
        if (c->acct < 0) reply(c->fd, "204 LOGIN FIRST\n");
        else if (nt != 5 || !valid_flight(tok[1]) || !valid_date(tok[2]) || (strcmp(tok[3], "ECO") && strcmp(tok[3], "BUS")) ||
                 !valid_name(tok[4])) reply(c->fd, "201 INVALID\n");
        else issue(c, tok);
    } else if (!strcmp(tok[0], "QUIT") && nt == 1) {
        reply(c->fd, "100 OK\n");
        return 0;
    } else {
        reply(c->fd, "999 UNKNOWN ERROR\n");
    }
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 4) { fprintf(stderr, "usage: %s <port> <smtp-ip> <smtp-port>\n", argv[0]); return 1; }
    signal(SIGPIPE, SIG_IGN);
    snprintf(smtp_ip, sizeof smtp_ip, "%s", argv[2]);
    smtp_port = atoi(argv[3]);
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
