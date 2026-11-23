// SAI có chủ đích: coi mỗi lần recv() là đúng một dòng (không có bộ đệm riêng).
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX 64
static int fds[MAX];
static char ids[MAX][64];

int main(int argc, char *argv[]) {
    (void)argc;
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(atoi(argv[1]));
    bind(ls, (struct sockaddr *)&a, sizeof a);
    listen(ls, 16);
    for (int i = 0; i < MAX; i++) fds[i] = -1;
    for (;;) {
        fd_set rd;
        FD_ZERO(&rd);
        FD_SET(ls, &rd);
        int mx = ls;
        for (int i = 0; i < MAX; i++)
            if (fds[i] >= 0) { FD_SET(fds[i], &rd); if (fds[i] > mx) mx = fds[i]; }
        select(mx + 1, &rd, NULL, NULL, NULL);
        if (FD_ISSET(ls, &rd)) {
            int fd = accept(ls, NULL, NULL);
            for (int i = 0; i < MAX; i++) if (fds[i] < 0) { fds[i] = fd; ids[i][0] = 0; break; }
        }
        for (int i = 0; i < MAX; i++) {
            if (fds[i] < 0 || !FD_ISSET(fds[i], &rd)) continue;
            char buf[1024];
            ssize_t n = recv(fds[i], buf, sizeof buf - 1, 0);
            if (n <= 0) { close(fds[i]); fds[i] = -1; continue; }
            buf[n] = 0;
            buf[strcspn(buf, "\r\n")] = 0;
            if (!ids[i][0]) {
                char id[64], name[64], extra[8];
                if (sscanf(buf, "%63[^: ]: %63s %7s", id, name, extra) == 2) {
                    strcpy(ids[i], id);
                    char m[128]; snprintf(m, sizeof m, "OK %s\n", id); send(fds[i], m, strlen(m), 0);
                } else send(fds[i], "ERROR\n", 6, 0);
                continue;
            }
            char m[1200]; snprintf(m, sizeof m, "%s: %s\n", ids[i], buf);
            for (int j = 0; j < MAX; j++)
                if (j != i && fds[j] >= 0 && ids[j][0]) send(fds[j], m, strlen(m), 0);
        }
    }
}
