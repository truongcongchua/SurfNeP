// SAI có chủ đích: mở log bằng O_TRUNC mỗi client -> ghi đè dữ liệu client trước.
#include <arpa/inet.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    (void)argc;
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(atoi(argv[1]));
    bind(ls, (struct sockaddr *)&a, sizeof a);
    listen(ls, 5);
    for (;;) {
        int c = accept(ls, NULL, NULL);
        char buf[4096];
        int g = open(argv[2], O_RDONLY);
        ssize_t k;
        while ((k = read(g, buf, sizeof buf)) > 0) send(c, buf, k, 0);
        close(g);
        int log = open(argv[3], O_WRONLY | O_CREAT | O_TRUNC, 0644);
        ssize_t n;
        while ((n = recv(c, buf, sizeof buf, 0)) > 0) write(log, buf, (size_t)n);
        close(log);
        close(c);
    }
}
