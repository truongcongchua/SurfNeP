// Sai có chủ đích: server lặp — đọc yêu cầu của một kết nối (chặn) rồi mới accept tiếp; luôn trả trang trống 200.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 2) return 1;
    int ls = socket(AF_INET, SOCK_STREAM, 0), yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_ANY);
    a.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&a, sizeof a) < 0 || listen(ls, 16) < 0) return 1;
    for (;;) {
        int fd = accept(ls, NULL, NULL);
        char buf[8192];
        size_t len = 0;
        while (len < sizeof buf - 1) {
            ssize_t n = recv(fd, buf + len, sizeof buf - 1 - len, 0);
            if (n <= 0) break;
            len += (size_t)n;
            buf[len] = 0;
            if (strstr(buf, "\r\n\r\n")) break;
        }
        const char *r = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: 7\r\nConnection: close\r\n\r\n<html/>";
        send(fd, r, strlen(r), 0);
        close(fd);
    }
}
