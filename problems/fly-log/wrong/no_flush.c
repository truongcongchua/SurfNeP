// Sai có chủ đích: ghi log bằng fprintf nhưng không fflush (log nằm trong bộ đệm stdio, bộ chấm không thấy ngay),
// và ghi SEND sau khi đã gửi.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

static FILE *logf;
static void ev(const char *addr, const char *kind, const char *text) {
    time_t now = time(NULL);
    char ts[32];
    strftime(ts, sizeof ts, "%Y-%m-%d %H:%M:%S", localtime(&now));
    if (text) fprintf(logf, "[%s] %s %s \"%s\"\n", ts, kind, addr, text);
    else fprintf(logf, "[%s] %s %s\n", ts, kind, addr);
}

int main(int argc, char *argv[]) {
    if (argc != 3) return 1;
    logf = fopen(argv[2], "a");
    int ls = socket(AF_INET, SOCK_STREAM, 0), yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_ANY);
    a.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&a, sizeof a) < 0 || listen(ls, 16) < 0) return 1;
    for (;;) {
        struct sockaddr_in ca;
        socklen_t cl = sizeof ca;
        int fd = accept(ls, (struct sockaddr *)&ca, &cl);
        char addr[32], buf[1024];
        snprintf(addr, sizeof addr, "%s:%d", inet_ntoa(ca.sin_addr), ntohs(ca.sin_port));
        ev(addr, "CONNECT", NULL);
        ssize_t n;
        while ((n = recv(fd, buf, sizeof buf - 1, 0)) > 0) {
            buf[n] = 0;
            buf[strcspn(buf, "\r\n")] = 0;
            ev(addr, "RECV", buf);
            send(fd, "100 OK PONG\n", 12, 0);
            ev(addr, "SEND", "100 OK PONG");
        }
        ev(addr, "DISCONNECT", NULL);
        close(fd);
    }
}
