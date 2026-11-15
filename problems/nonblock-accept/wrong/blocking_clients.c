// SAI có chủ đích: chỉ socket lắng nghe non-blocking, socket client vẫn blocking -> recv chặn -> BLOCKED.
#include <arpa/inet.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    (void)argc;
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1, on = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(atoi(argv[1]));
    bind(ls, (struct sockaddr *)&a, sizeof a);
    listen(ls, 64);
    ioctl(ls, FIONBIO, &on);
    int cl[512], n = 0;
    for (;;) {
        int c = accept(ls, NULL, NULL);
        if (c >= 0) cl[n++] = c;
        for (int i = 0; i < n; i++) {
            char buf[8192];
            ssize_t k = recv(cl[i], buf, sizeof buf, 0);
            if (k > 0) send(cl[i], buf, (size_t)k, MSG_NOSIGNAL);
            else { close(cl[i]); cl[i--] = cl[--n]; }
        }
        usleep(1000);
    }
}
