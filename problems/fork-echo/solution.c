#include <arpa/inet.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

static void reap(int sig) {
    (void)sig;
    int saved = errno;
    while (waitpid(-1, NULL, WNOHANG) > 0) {
    }
    errno = saved;
}

static int send_all(int fd, const char *buf, size_t n) {
    while (n > 0) {
        ssize_t k = send(fd, buf, n, MSG_NOSIGNAL);
        if (k <= 0) return -1;
        buf += k;
        n -= (size_t)k;
    }
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    struct sigaction sa = {0};
    sa.sa_handler = reap;
    sa.sa_flags = SA_RESTART;
    sigaction(SIGCHLD, &sa, NULL);

    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 64) < 0) {
        perror("bind/listen");
        return 1;
    }
    for (;;) {
        int c = accept(ls, NULL, NULL);
        if (c < 0) continue;  // EINTR do SIGCHLD
        pid_t pid = fork();
        if (pid == 0) {
            close(ls);
            char buf[8192];
            ssize_t k;
            while ((k = recv(c, buf, sizeof buf, 0)) > 0)
                if (send_all(c, buf, (size_t)k) < 0) break;
            close(c);
            _exit(0);
        }
        close(c);
    }
}
