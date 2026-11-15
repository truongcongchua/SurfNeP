#include <arpa/inet.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

static int send_all(int fd, const char *buf, size_t n) {
    while (n > 0) {
        ssize_t k = send(fd, buf, n, MSG_NOSIGNAL);
        if (k <= 0) return -1;
        buf += k;
        n -= (size_t)k;
    }
    return 0;
}

static void send_file(int c, const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return;
    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof buf, f)) > 0)
        if (send_all(c, buf, n) < 0) break;
    fclose(f);
}

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <greeting_file> <log_file>\n", argv[0]);
        return 1;
    }
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 5) < 0) {
        perror("bind/listen");
        return 1;
    }
    for (;;) {
        int c = accept(ls, NULL, NULL);
        if (c < 0) continue;
        send_file(c, argv[2]);
        int log = open(argv[3], O_WRONLY | O_CREAT | O_APPEND, 0644);
        char buf[4096];
        ssize_t n;
        while ((n = recv(c, buf, sizeof buf, 0)) > 0)
            if (log >= 0 && write(log, buf, (size_t)n) != n) break;
        if (log >= 0) close(log);
        close(c);
    }
}
