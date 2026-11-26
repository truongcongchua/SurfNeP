// Lời giải mẫu: đọc dòng từ bộ đệm giữ qua các lần recv; phần dữ liệu thừa sau dòng "120 FILE n" thuộc về nội dung.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static int sock;
static char rb[65536];
static size_t rlen, rpos;

// Đọc một dòng (bỏ '\n' và '\r'); trả về 0 nếu server đóng/ lỗi hoặc dòng quá dài.
static int read_line(char *out, size_t cap) {
    size_t o = 0;
    for (;;) {
        if (rpos == rlen) {
            ssize_t n = recv(sock, rb, sizeof rb, 0);
            if (n <= 0) return 0;
            rlen = (size_t)n;
            rpos = 0;
        }
        char c = rb[rpos++];
        if (c == '\n') break;
        if (o + 1 >= cap) return 0;
        out[o++] = c;
    }
    if (o && out[o - 1] == '\r') o--;
    out[o] = 0;
    return 1;
}

static void send_line(const char *s) {
    char buf[512];
    int n = snprintf(buf, sizeof buf, "%s\n", s);
    send(sock, buf, (size_t)n, 0);
}

static void fail(const char *line) {
    printf("ERROR %s\n", line);
    fflush(stdout);
    send_line("QUIT");
    close(sock);
    exit(1);
}

int main(int argc, char *argv[]) {
    if (argc != 7) {
        fprintf(stderr, "Usage: %s <ip> <port> <user> <pass> <ticket> <outfile>\n", argv[0]);
        return 1;
    }
    sock = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = inet_addr(argv[1]);
    addr.sin_port = htons(atoi(argv[2]));
    if (addr.sin_addr.s_addr == INADDR_NONE || connect(sock, (struct sockaddr *)&addr, sizeof addr) < 0) {
        perror("connect");
        return 1;
    }
    char line[2048], cmd[1024];

    if (!read_line(line, sizeof line)) fail("connection closed");
    if (strncmp(line, "100", 3) != 0) fail(line);

    snprintf(cmd, sizeof cmd, "LOGIN %s %s", argv[3], argv[4]);
    send_line(cmd);
    if (!read_line(line, sizeof line)) fail("connection closed");
    if (strncmp(line, "100", 3) != 0) fail(line);

    snprintf(cmd, sizeof cmd, "PRINT %s", argv[5]);
    send_line(cmd);
    if (!read_line(line, sizeof line)) fail("connection closed");
    long long n = -1;
    if (strncmp(line, "120 FILE ", 9) == 0) {
        const char *p = line + 9;
        size_t digits = strlen(p);
        if (digits >= 1 && digits <= 7) {
            n = 0;
            for (; *p; p++) {
                if (*p < '0' || *p > '9') { n = -1; break; }
                n = n * 10 + (*p - '0');
            }
        }
    }
    if (n < 0 || n > 5000000) fail(line);

    char tmp[1100];
    snprintf(tmp, sizeof tmp, "%s.tmp", argv[6]);
    FILE *f = fopen(tmp, "wb");
    if (!f) { perror("fopen"); fail("cannot open output"); }

    long long left = n;
    while (left > 0 && rpos < rlen) {  // phần đã nằm sẵn trong bộ đệm sau dòng tiêu đề
        size_t take = rlen - rpos;
        if ((long long)take > left) take = (size_t)left;
        fwrite(rb + rpos, 1, take, f);
        rpos += take;
        left -= (long long)take;
    }
    while (left > 0) {
        ssize_t r = recv(sock, rb, sizeof rb, 0);
        if (r <= 0) {
            fclose(f);
            remove(tmp);
            fail("connection closed before the whole ticket arrived");
        }
        size_t take = (size_t)r;
        if ((long long)take > left) take = (size_t)left;
        fwrite(rb, 1, take, f);
        left -= (long long)take;
    }
    fclose(f);

    send_line("QUIT");
    read_line(line, sizeof line);
    close(sock);
    if (rename(tmp, argv[6]) != 0) { perror("rename"); return 1; }
    return 0;
}
