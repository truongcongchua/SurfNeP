// SAI có chủ đích: dùng select() nhưng khi có client thì phục vụ nó đến khi đóng -> BLOCKED.
#include <arpa/inet.h>
#include <stdlib.h>
#include <sys/select.h>
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
    listen(ls, 64);
    for (;;) {
        fd_set rd;
        FD_ZERO(&rd);
        FD_SET(ls, &rd);
        select(ls + 1, &rd, NULL, NULL, NULL);
        int c = accept(ls, NULL, NULL);
        char buf[8192];
        ssize_t k;
        while ((k = recv(c, buf, sizeof buf, 0)) > 0) send(c, buf, (size_t)k, 0);
        close(c);
    }
}
