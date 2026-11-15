#include <arpa/inet.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

static int recv_exact(int fd, void *buf, size_t n) {
    char *p = buf;
    while (n > 0) {
        ssize_t k = recv(fd, p, n, 0);
        if (k <= 0) return -1;
        p += k;
        n -= (size_t)k;
    }
    return 0;
}

// Trả về 1 nếu đọc được bản ghi hợp lệ, 0 nếu không hợp lệ, -1 nếu client đóng/lỗi.
static int serve_one(int c, const char *ip, const char *logpath) {
    unsigned char head[5], tail[6];
    char name[101];
    if (recv_exact(c, head, 5) < 0) return -1;
    uint32_t mssv;
    memcpy(&mssv, head, 4);
    mssv = ntohl(mssv);
    unsigned nlen = head[4];
    if (nlen == 0 || nlen > 100) return 0;
    if (recv_exact(c, name, nlen) < 0 || recv_exact(c, tail, 6) < 0) return -1;
    name[nlen] = 0;
    uint16_t year, gpa;
    memcpy(&year, tail, 2);
    memcpy(&gpa, tail + 4, 2);
    year = ntohs(year);
    gpa = ntohs(gpa);
    unsigned month = tail[2], day = tail[3];
    if (month < 1 || month > 12 || day < 1 || day > 31 || gpa > 400) return 0;

    char now[32];
    time_t t = time(NULL);
    strftime(now, sizeof now, "%Y-%m-%d %H:%M:%S", localtime(&t));
    char line[512];
    snprintf(line, sizeof line, "%s %s %u %s %04u-%02u-%02u %u.%02u\n", ip, now, mssv, name,
             (unsigned)year, month, day, gpa / 100u, gpa % 100u);
    fputs(line, stdout);
    fflush(stdout);
    FILE *f = fopen(logpath, "a");
    if (f) {
        fputs(line, f);
        fclose(f);
    }
    send(c, "OK\n", 3, MSG_NOSIGNAL);
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <log_file>\n", argv[0]);
        return 1;
    }
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 5) < 0) {
        perror("bind/listen");
        return 1;
    }
    for (;;) {
        struct sockaddr_in ca;
        socklen_t cl = sizeof ca;
        int c = accept(ls, (struct sockaddr *)&ca, &cl);
        if (c < 0) continue;
        char ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &ca.sin_addr, ip, sizeof ip);
        int r;
        while ((r = serve_one(c, ip, argv[2])) == 1) {
        }
        if (r == 0) send(c, "ERROR\n", 6, MSG_NOSIGNAL);
        close(c);
    }
}
