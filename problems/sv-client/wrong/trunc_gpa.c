// SAI có chủ đích: ép kiểu thẳng (int)(x*100) nên 2.85 thành 284.
#include <arpa/inet.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static int send_all(int fd, const unsigned char *buf, size_t n) {
    while (n > 0) {
        ssize_t k = send(fd, buf, n, MSG_NOSIGNAL);
        if (k <= 0) return -1;
        buf += k;
        n -= (size_t)k;
    }
    return 0;
}

// Đọc một dòng từ stdin, bỏ "\n" / "\r\n" cuối. Trả về 0 nếu EOF.
static int read_line(char *buf, size_t size) {
    if (!fgets(buf, (int)size, stdin)) return 0;
    buf[strcspn(buf, "\r\n")] = 0;
    return 1;
}

// Đọc một dòng phản hồi từ server (không kèm '\n'). Trả về -1 nếu server đóng.
static int recv_line(int fd, char *out, size_t size) {
    size_t n = 0;
    while (n + 1 < size) {
        char c;
        if (recv(fd, &c, 1, 0) <= 0) return -1;
        if (c == '\n') break;
        out[n++] = c;
    }
    out[n] = 0;
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    struct sockaddr_in sa = {0};
    sa.sin_family = AF_INET;
    sa.sin_port = htons((unsigned short)atoi(argv[2]));
    if (inet_pton(AF_INET, argv[1], &sa.sin_addr) != 1) {
        fprintf(stderr, "dia chi IP khong hop le\n");
        return 1;
    }
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (connect(s, (struct sockaddr *)&sa, sizeof sa) < 0) {
        perror("connect");
        return 1;
    }
    char mssv_s[64], name[512], dob[64], gpa_s[64];
    while (read_line(mssv_s, sizeof mssv_s) && read_line(name, sizeof name) &&
           read_line(dob, sizeof dob) && read_line(gpa_s, sizeof gpa_s)) {
        unsigned year = 0, month = 0, day = 0;
        sscanf(dob, "%u-%u-%u", &year, &month, &day);
        uint32_t mssv = htonl((uint32_t)strtoul(mssv_s, NULL, 10));
        uint16_t y = htons((uint16_t)year);
        uint16_t gpa = htons((uint16_t)(int)(strtod(gpa_s, NULL) * 100.0));
        size_t nlen = strlen(name);  // số BYTE, đúng với UTF-8

        unsigned char rec[4 + 1 + 255 + 6];
        size_t p = 0;
        memcpy(rec + p, &mssv, 4), p += 4;
        rec[p++] = (unsigned char)nlen;
        memcpy(rec + p, name, nlen), p += nlen;
        memcpy(rec + p, &y, 2), p += 2;
        rec[p++] = (unsigned char)month;
        rec[p++] = (unsigned char)day;
        memcpy(rec + p, &gpa, 2), p += 2;
        if (send_all(s, rec, p) < 0) break;

        char reply[128];
        if (recv_line(s, reply, sizeof reply) < 0) break;
        printf("%s\n", reply);
        fflush(stdout);
        if (strcmp(reply, "OK") != 0) break;
    }
    close(s);
    return 0;
}
