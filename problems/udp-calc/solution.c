#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_PEERS 1024

typedef struct { struct sockaddr_in addr; long count; } Peer;
static Peer peers[MAX_PEERS];
static int npeers = 0;

static Peer *lookup(const struct sockaddr_in *a) {
    for (int i = 0; i < npeers; i++)
        if (peers[i].addr.sin_addr.s_addr == a->sin_addr.s_addr && peers[i].addr.sin_port == a->sin_port)
            return &peers[i];
    if (npeers == MAX_PEERS) return NULL;
    peers[npeers].addr = *a;
    peers[npeers].count = 0;
    return &peers[npeers++];
}

// Đọc số nguyên chiếm trọn xâu s. Trả về 1 nếu hợp lệ.
static int parse_ll(const char *s, long long *out) {
    if (!*s) return 0;
    char *end;
    errno = 0;
    *out = strtoll(s, &end, 10);
    return *end == 0 && errno == 0 && s[0] != ' ' && s[0] != '+';
}

static void handle(const char *req, Peer *p, char *out, size_t cap) {
    if (!strcmp(req, "COUNT")) {
        snprintf(out, cap, "%ld", p ? p->count : 0L);
        return;
    }
    char a[64], op[4], b[64];
    const char *s1 = strchr(req, ' ');
    const char *s2 = s1 ? strchr(s1 + 1, ' ') : NULL;
    if (!s1 || !s2 || strchr(s2 + 1, ' ') || s1 - req >= (long)sizeof a || s2 - s1 - 1 != 1 ||
        strlen(s2 + 1) >= sizeof b) {
        snprintf(out, cap, "ERROR syntax");
        return;
    }
    memcpy(a, req, (size_t)(s1 - req));
    a[s1 - req] = 0;
    op[0] = s1[1];
    op[1] = 0;
    strcpy(b, s2 + 1);
    long long x, y;
    if (!parse_ll(a, &x) || !parse_ll(b, &y) || !strchr("+-*/%", op[0])) {
        snprintf(out, cap, "ERROR syntax");
        return;
    }
    if ((op[0] == '/' || op[0] == '%') && y == 0) {
        snprintf(out, cap, "ERROR div0");
        return;
    }
    long long r = op[0] == '+' ? x + y : op[0] == '-' ? x - y : op[0] == '*' ? x * y
                : op[0] == '/' ? x / y : x % y;
    if (p) p->count++;
    snprintf(out, cap, "%lld", r);
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(s, (struct sockaddr *)&addr, sizeof addr) < 0) {
        perror("bind");
        return 1;
    }
    char buf[1024], out[64];
    for (;;) {
        struct sockaddr_in from;
        socklen_t fl = sizeof from;
        ssize_t n = recvfrom(s, buf, sizeof buf - 1, 0, (struct sockaddr *)&from, &fl);
        if (n < 0) continue;
        buf[n] = 0;
        handle(buf, lookup(&from), out, sizeof out);
        sendto(s, out, strlen(out), 0, (struct sockaddr *)&from, fl);
    }
}
