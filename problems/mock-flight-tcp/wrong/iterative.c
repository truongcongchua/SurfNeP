// Sai có chủ đích: server lặp — chào client, phục vụ đến khi nó đóng rồi mới accept client tiếp theo (không giới hạn N).
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 3) return 1;
    int ls = socket(AF_INET, SOCK_STREAM, 0), yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_ANY);
    a.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&a, sizeof a) < 0 || listen(ls, 16) < 0) return 1;
    for (;;) {
        int fd = accept(ls, NULL, NULL);
        char buf[2048];
        ssize_t n;
        send(fd, "WELCOME\n", 8, 0);
        while ((n = recv(fd, buf, sizeof buf, 0)) > 0) send(fd, "LOGIN_FIRST\n", 12, 0);
        close(fd);
    }
}
