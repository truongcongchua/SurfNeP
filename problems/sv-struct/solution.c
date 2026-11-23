// Lời giải mẫu: server lặp như tcp_server.c; đọc bản ghi từng phần, giải mã thủ công + ntohl/ntohs.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <arpa/inet.h>
#include <sys/socket.h>

// Nhận đủ n byte vào buf (recv có thể trả về ít hơn số byte xin). Trả về 0 nếu đủ, -1 nếu client đóng/lỗi.
int recv_n(int client, unsigned char *buf, int n) {
    int got = 0;
    while (got < n) {
        int k = recv(client, buf + got, n - got, 0);
        if (k <= 0) return -1;
        got += k;
    }
    return 0;
}

// Trả về 1 nếu đọc được bản ghi hợp lệ, 0 nếu không hợp lệ, -1 nếu client đóng/lỗi.
int serve_one(int client, const char *ip, const char *logpath) {
    unsigned char head[5], tail[6];
    char name[101];
    if (recv_n(client, head, 5) < 0) return -1;
    unsigned int mssv;
    memcpy(&mssv, head, 4);
    mssv = ntohl(mssv);
    int nlen = head[4];
    if (nlen == 0 || nlen > 100) return 0;
    if (recv_n(client, (unsigned char *)name, nlen) < 0 || recv_n(client, tail, 6) < 0) return -1;
    name[nlen] = 0;
    unsigned short year, gpa;
    memcpy(&year, tail, 2);
    memcpy(&gpa, tail + 4, 2);
    year = ntohs(year);
    gpa = ntohs(gpa);
    int month = tail[2], day = tail[3];
    if (month < 1 || month > 12 || day < 1 || day > 31 || gpa > 400) return 0;

    // Thời gian hiện tại (đoạn code cho sẵn trong đề)
    char now[32];
    time_t t = time(NULL);
    strftime(now, sizeof(now), "%Y-%m-%d %H:%M:%S", localtime(&t));

    char line[512];
    sprintf(line, "%s %s %u %s %04u-%02u-%02u %u.%02u\n", ip, now, mssv, name,
            (unsigned)year, (unsigned)month, (unsigned)day, gpa / 100u, gpa % 100u);
    printf("%s", line);
    fflush(stdout);
    FILE *f = fopen(logpath, "a");
    if (f != NULL) {
        fprintf(f, "%s", line);
        fclose(f);
    }
    send(client, "OK\n", 3, 0);
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <port> <log_file>\n", argv[0]);
        return 1;
    }
    int listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    int opt = 1;
    setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(argv[1]));
    addr.sin_addr.s_addr = INADDR_ANY;
    if (bind(listener, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("bind() failed");
        return 1;
    }
    if (listen(listener, 5) == -1) {
        perror("listen() failed");
        return 1;
    }
    while (0 == 0) {
        struct sockaddr_in client_addr;
        socklen_t client_addr_len = sizeof(client_addr);
        int client = accept(listener, (struct sockaddr *)&client_addr, &client_addr_len);
        if (client == -1) continue;
        char ip[32];
        strcpy(ip, inet_ntoa(client_addr.sin_addr));  // như udp_receiver.c
        int r;
        while ((r = serve_one(client, ip, argv[2])) == 1) {
        }
        if (r == 0) send(client, "ERROR\n", 6, 0);
        close(client);
    }
}
