// SAI có chủ đích: không bỏ ký tự xuống dòng cuối dòng nên datagram thừa một byte.
#include <arpa/inet.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    struct sockaddr_in sa = {0};
    sa.sin_family = AF_INET;
    sa.sin_port = htons((unsigned short)atoi(argv[2]));
    if (inet_pton(AF_INET, argv[1], &sa.sin_addr) != 1) {
        fprintf(stderr, "dia chi IP khong hop le: %s\n", argv[1]);
        return 1;
    }
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    char line[4096], reply[2049];
    while (fgets(line, sizeof line, stdin)) {
        size_t n = strlen(line);
        sendto(s, line, n, 0, (struct sockaddr *)&sa, sizeof sa);

        struct pollfd p = {.fd = s, .events = POLLIN};
        if (poll(&p, 1, 1000) > 0) {
            ssize_t k = recvfrom(s, reply, sizeof reply - 1, 0, NULL, NULL);
            if (k >= 0) {
                fwrite(reply, 1, (size_t)k, stdout);
                fputc('\n', stdout);
            }
        } else {
            fputs("TIMEOUT\n", stdout);
        }
        fflush(stdout);
    }
    close(s);
    return 0;
}
