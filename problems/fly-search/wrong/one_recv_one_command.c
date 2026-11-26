// Sai có chủ đích: coi mỗi lần recv là đúng một lệnh (không ghép dòng) và dùng select cho nhiều client.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
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
    int cl[64];
    for (int i = 0; i < 64; i++) cl[i] = -1;
    for (;;) {
        fd_set rd;
        FD_ZERO(&rd);
        FD_SET(ls, &rd);
        int mx = ls;
        for (int i = 0; i < 64; i++)
            if (cl[i] >= 0) { FD_SET(cl[i], &rd); if (cl[i] > mx) mx = cl[i]; }
        select(mx + 1, &rd, NULL, NULL, NULL);
        if (FD_ISSET(ls, &rd)) {
            int fd = accept(ls, NULL, NULL);
            for (int i = 0; i < 64; i++) if (cl[i] < 0) { cl[i] = fd; break; }
        }
        for (int i = 0; i < 64; i++) {
            if (cl[i] < 0 || !FD_ISSET(cl[i], &rd)) continue;
            char buf[2048];
            ssize_t n = recv(cl[i], buf, sizeof buf - 1, 0);
            if (n <= 0) { close(cl[i]); cl[i] = -1; continue; }
            buf[n] = 0;
            if (!strncmp(buf, "QUIT", 4)) { send(cl[i], "100 OK\n", 7, 0); close(cl[i]); cl[i] = -1; }
            else send(cl[i], "110 FLIGHTS 0\n", 14, 0);
        }
    }
}
