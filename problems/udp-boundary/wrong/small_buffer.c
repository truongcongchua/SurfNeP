// SAI có chủ đích: bộ đệm 1024 byte -> datagram lớn bị cắt cụt; đếm chung mọi người gửi.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    (void)argc;
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(atoi(argv[1]));
    bind(s, (struct sockaddr *)&a, sizeof a);
    char buf[1024];
    unsigned long count = 0;
    for (;;) {
        struct sockaddr_in f;
        socklen_t fl = sizeof f;
        ssize_t n = recvfrom(s, buf, sizeof buf, 0, (struct sockaddr *)&f, &fl);
        char out[64];
        int len = snprintf(out, sizeof out, "LEN %zd %lu", n, ++count);
        sendto(s, out, (size_t)len, 0, (struct sockaddr *)&f, fl);
    }
}
