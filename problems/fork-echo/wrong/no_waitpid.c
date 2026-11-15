// SAI có chủ đích: không thu dọn tiến trình con -> zombie.
#include <arpa/inet.h>
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
    listen(ls, 64);
    for (;;) {
        int c = accept(ls, NULL, NULL);
        if (fork() == 0) {
            close(ls);
            char buf[8192];
            ssize_t k;
            while ((k = recv(c, buf, sizeof buf, 0)) > 0) send(c, buf, (size_t)k, MSG_NOSIGNAL);
            _exit(0);
        }
        close(c);
    }
}
