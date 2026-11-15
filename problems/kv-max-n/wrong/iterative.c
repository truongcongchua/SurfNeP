// SAI có chủ đích: server lặp, phục vụ xong client này mới accept client khác -> BLOCKED.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static char keys[1000][65], vals[1000][65];
static int nk = 0;

static int find(const char *k) {
    for (int i = 0; i < nk; i++) if (!strcmp(keys[i], k)) return i;
    return -1;
}

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
    for (;;) {
        int fd = accept(ls, NULL, NULL);
        FILE *in = fdopen(dup(fd), "r");
        send(fd, "WELCOME\n", 8, 0);
        char line[256], out[160];
        while (fgets(line, sizeof line, in)) {
            line[strcspn(line, "\r\n")] = 0;
            char c[16], k[65], v[65], x[8];
            int n = sscanf(line, "%15s %64s %64s %7s", c, k, v, x);
            if (n == 3 && !strcmp(c, "SET")) {
                int i = find(k); if (i < 0) { i = nk++; strcpy(keys[i], k); }
                strcpy(vals[i], v); send(fd, "OK\n", 3, 0);
            } else if (n == 2 && !strcmp(c, "GET")) {
                int i = find(k);
                if (i < 0) send(fd, "NOT_FOUND\n", 10, 0);
                else { snprintf(out, sizeof out, "VALUE %s\n", vals[i]); send(fd, out, strlen(out), 0); }
            } else if (n == 2 && !strcmp(c, "DEL")) {
                int i = find(k);
                if (i < 0) send(fd, "NOT_FOUND\n", 10, 0);
                else { nk--; strcpy(keys[i], keys[nk]); strcpy(vals[i], vals[nk]); send(fd, "OK\n", 3, 0); }
            } else if (n == 1 && !strcmp(c, "COUNT")) {
                snprintf(out, sizeof out, "COUNT %d\n", nk); send(fd, out, strlen(out), 0);
            } else if (n == 1 && !strcmp(c, "QUIT")) { send(fd, "BYE\n", 4, 0); break; }
            else send(fd, "ERROR\n", 6, 0);
        }
        fclose(in);
        close(fd);
    }
}
