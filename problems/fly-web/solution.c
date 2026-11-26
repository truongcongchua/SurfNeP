// Lời giải mẫu: mỗi kết nối một luồng (như http_server.c); đọc đến \r\n\r\n, POST đọc đủ Content-Length, dựng HTML bằng bộ đệm lớn.
#include <arpa/inet.h>
#include <strings.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_FLIGHTS 1000
#define HEAD_MAX 8192

typedef struct {
    char code[16], airline[8], from[8], to[8], date[16], dep[8], arr[8];
    long long price[2];
    int seats[2];
} Flight;

static Flight fl[MAX_FLIGHTS];
static int nfl;

static void load(void) {
    FILE *f = fopen("flights.txt", "r");
    char line[512];
    while (f && nfl < MAX_FLIGHTS && fgets(line, sizeof line, f)) {
        Flight *x = &fl[nfl];
        if (sscanf(line, "%15s %7s %7s %7s %15s %7s %7s %lld %d %lld %d", x->code, x->airline, x->from, x->to, x->date, x->dep, x->arr,
                   &x->price[0], &x->seats[0], &x->price[1], &x->seats[1]) == 11)
            nfl++;
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
static int airport(const char *s) { return strlen(s) == 3 && s[0] >= 'A' && s[0] <= 'Z' && s[1] >= 'A' && s[1] <= 'Z' && s[2] >= 'A' && s[2] <= 'Z'; }

static int hexv(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

// Giải mã %XX và '+' tại chỗ; trả về 0 nếu % hỏng.
static int url_decode(char *s) {
    char *w = s;
    for (char *r = s; *r; r++) {
        if (*r == '+') *w++ = ' ';
        else if (*r == '%') {
            if (hexv(r[1]) < 0 || hexv(r[2]) < 0) return 0;
            *w++ = (char)(hexv(r[1]) * 16 + hexv(r[2]));
            r += 2;
        } else *w++ = *r;
    }
    *w = 0;
    return 1;
}

static void send_all_text(int fd, const char *s, size_t n) { send(fd, s, n, 0); }

static void respond(int fd, int code, const char *reason, const char *type, const char *body, size_t len) {
    char head[256];
    int n = snprintf(head, sizeof head, "HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %zu\r\nConnection: close\r\n\r\n", code, reason, type, len);
    send_all_text(fd, head, (size_t)n);
    send_all_text(fd, body, len);
}

static void error(int fd, int code, const char *reason) {
    char body[64];
    int n = snprintf(body, sizeof body, "%s\n", reason);
    respond(fd, code, reason, "text/plain; charset=utf-8", body, (size_t)n);
}

static void html(int fd, const char *body, size_t len) { respond(fd, 200, "OK", "text/html; charset=utf-8", body, len); }

static void index_page(int fd) {
    static const char page[] =
        "<html><body><h1>Tim chuyen bay</h1>\n<form action=\"/search\" method=\"get\">\n"
        "Di: <input name=\"from\"> Den: <input name=\"to\"> Ngay: <input name=\"date\"> So khach: <input name=\"pax\"> Hang: <input name=\"class\">\n"
        "<input type=\"submit\" value=\"Tim\">\n</form></body></html>\n";
    html(fd, page, sizeof page - 1);
}

static void search_page(int fd, char *query) {
    char *val[5] = {0};
    static const char *keys[5] = {"from", "to", "date", "pax", "class"};
    for (char *p = query; p && *p;) {
        char *amp = strchr(p, '&');
        if (amp) *amp = 0;
        char *eq = strchr(p, '=');
        if (eq) {
            *eq = 0;
            char *k = p, *v = eq + 1;
            if (!url_decode(k) || !url_decode(v)) { error(fd, 400, "Bad Request"); return; }
            for (int i = 0; i < 5; i++)
                if (!strcmp(k, keys[i]) && !val[i]) val[i] = v;
        }
        p = amp ? amp + 1 : NULL;
    }
    if (!val[0] || !val[1] || !val[2] || !val[3] || !val[4] || !airport(val[0]) || !airport(val[1]) || !strcmp(val[0], val[1]) ||
        !valid_date(val[2]) || strlen(val[3]) != 1 || val[3][0] < '1' || val[3][0] > '9' || (strcmp(val[4], "ECO") && strcmp(val[4], "BUS"))) {
        error(fd, 400, "Bad Request");
        return;
    }
    int pax = val[3][0] - '0', bus = !strcmp(val[4], "BUS");
    size_t cap = 4096 + (size_t)nfl * 160;
    char *out = malloc(cap);
    size_t o = 0;
    int idx[MAX_FLIGHTS], k = 0;
    for (int i = 0; i < nfl; i++)
        if (!strcmp(fl[i].from, val[0]) && !strcmp(fl[i].to, val[1]) && !strcmp(fl[i].date, val[2]) && fl[i].seats[bus] >= pax) idx[k++] = i;
    o += (size_t)snprintf(out + o, cap - o, "<html><body><h1>Co %d chuyen</h1>\n<h2>%s -&gt; %s %s</h2>\n<table>\n", k, val[0], val[1], val[2]);
    o += (size_t)snprintf(out + o, cap - o, "<tr><th>Ma</th><th>Hang</th><th>Gio di</th><th>Gio den</th><th>Tong tien</th></tr>\n");
    for (int j = 0; j < k; j++) {
        Flight *x = &fl[idx[j]];
        o += (size_t)snprintf(out + o, cap - o, "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%lld</td></tr>\n", x->code, x->airline, x->dep, x->arr,
                              x->price[bus] * pax);
    }
    o += (size_t)snprintf(out + o, cap - o, "</table>\n<a href=\"/\">Tim lai</a></body></html>\n");
    html(fd, out, o);
    free(out);
}

static void flight_page(int fd, const char *code) {
    for (int i = 0; i < nfl; i++)
        if (!strcmp(fl[i].code, code)) {
            Flight *x = &fl[i];
            char body[1024];
            int n = snprintf(body, sizeof body,
                             "<html><body><h1>%s</h1>\n<p>%s -&gt; %s %s %s-%s</p>\n<p>ECO %lld (%d ghe)</p>\n<p>BUS %lld (%d ghe)</p>\n</body></html>\n",
                             x->code, x->from, x->to, x->date, x->dep, x->arr, x->price[0], x->seats[0], x->price[1], x->seats[1]);
            html(fd, body, (size_t)n);
            return;
        }
    error(fd, 404, "Not Found");
}

static void *serve(void *arg) {
    int fd = *(int *)arg;
    free(arg);
    char buf[HEAD_MAX + 4097];
    size_t len = 0;
    char *end = NULL;
    while (!end) {
        if (len >= HEAD_MAX) { error(fd, 400, "Bad Request"); goto done; }
        ssize_t n = recv(fd, buf + len, HEAD_MAX - len, 0);
        if (n <= 0) goto done;
        len += (size_t)n;
        buf[len] = 0;
        end = strstr(buf, "\r\n\r\n");
    }
    size_t head_len = (size_t)(end - buf) + 4;
    char method[32], target[HEAD_MAX], version[32], extra[8];
    char *eol = strstr(buf, "\r\n");
    *eol = 0;
    if (sscanf(buf, "%31s %8191s %31s %7s", method, target, version, extra) != 3 || strchr(buf, '\t')) { error(fd, 400, "Bad Request"); goto done; }
    *eol = '\r';
    {
        // đúng một dấu cách giữa ba thành phần
        size_t a = strlen(method), b = strlen(target);
        if (buf[a] != ' ' || buf[a + 1 + b] != ' ' || buf[a + 1] == ' ') { error(fd, 400, "Bad Request"); goto done; }
    }
    if (strcmp(version, "HTTP/1.1") && strcmp(version, "HTTP/1.0")) { error(fd, 400, "Bad Request"); goto done; }
    if (strcmp(method, "GET") && strcmp(method, "POST")) { error(fd, 405, "Method Not Allowed"); goto done; }
    char *q = strchr(target, '?');
    char *query = q ? q + 1 : NULL;
    if (q) *q = 0;
    if (!strcmp(method, "GET")) {
        if (!strcmp(target, "/")) index_page(fd);
        else if (!strcmp(target, "/search")) { char empty[1] = ""; char *qq = query ? query : empty; search_page(fd, qq); }
        else if (!strncmp(target, "/flight/", 8)) flight_page(fd, target + 8);
        else error(fd, 404, "Not Found");
    } else {
        if (strcmp(target, "/search")) { error(fd, 404, "Not Found"); goto done; }
        // tìm Content-Length (không phân biệt hoa thường)
        long clen = -1;
        for (char *p = strstr(buf, "\r\n"); p && p < end; p = strstr(p + 2, "\r\n")) {
            char *line = p + 2;
            if (!strncasecmp(line, "Content-Length:", 15)) {
                char *v = line + 15;
                while (*v == ' ') v++;
                char *e;
                clen = strtol(v, &e, 10);
                if (e == v) clen = -1;
                break;
            }
        }
        if (clen < 0 || clen > 4096) { error(fd, 400, "Bad Request"); goto done; }
        size_t have = len - head_len;
        char body[4100];
        if ((long)have > clen) have = (size_t)clen;
        memcpy(body, buf + head_len, have);
        while ((long)have < clen) {
            ssize_t n = recv(fd, body + have, (size_t)clen - have, 0);
            if (n <= 0) goto done;
            have += (size_t)n;
        }
        body[have] = 0;
        search_page(fd, body);
    }
done:
    close(fd);
    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 2) { fprintf(stderr, "usage: %s <port>\n", argv[0]); return 1; }
    signal(SIGPIPE, SIG_IGN);
    load();
    int ls = socket(AF_INET, SOCK_STREAM, 0), yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 64) < 0) { perror("bind/listen"); return 1; }
    for (;;) {
        int fd = accept(ls, NULL, NULL);
        if (fd < 0) continue;
        int *arg = malloc(sizeof *arg);
        *arg = fd;
        pthread_t t;
        if (pthread_create(&t, NULL, serve, arg) != 0) { close(fd); free(arg); continue; }
        pthread_detach(t);
    }
}
