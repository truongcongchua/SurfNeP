// SAI có chủ đích: sscanf lỏng lẻo và bộ đếm COUNT dùng chung cho mọi người gửi.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    (void)argc;
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(atoi(argv[1]));
    bind(s, (struct sockaddr *)&a, sizeof a);
    char buf[1024], out[64];
    long count = 0;
    for (;;) {
        struct sockaddr_in f;
        socklen_t fl = sizeof f;
        ssize_t n = recvfrom(s, buf, sizeof buf - 1, 0, (struct sockaddr *)&f, &fl);
        buf[n] = 0;
        long long x, y;
        char op;
        if (!strcmp(buf, "COUNT")) snprintf(out, sizeof out, "%ld", count);
        else if (sscanf(buf, "%lld %c %lld", &x, &op, &y) != 3) strcpy(out, "ERROR syntax");
        else if ((op == '/' || op == '%') && y == 0) strcpy(out, "ERROR div0");
        else {
            long long r = op == '+' ? x + y : op == '-' ? x - y : op == '*' ? x * y : op == '/' ? x / y : x % y;
            count++;
            snprintf(out, sizeof out, "%lld", r);
        }
        sendto(s, out, strlen(out), 0, (struct sockaddr *)&f, fl);
    }
}
