// SAI có chủ đích: coi recvfrom() == 0 như TCP "đóng kết nối" và thoát.
#include <arpa/inet.h>
#include <stdlib.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    (void)argc;
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(atoi(argv[1]));
    bind(s, (struct sockaddr *)&a, sizeof a);
    char buf[4096];
    for (;;) {
        struct sockaddr_in f;
        socklen_t fl = sizeof f;
        ssize_t n = recvfrom(s, buf, sizeof buf, 0, (struct sockaddr *)&f, &fl);
        if (n <= 0) return 0;
        sendto(s, buf, (size_t)n, 0, (struct sockaddr *)&f, fl);
    }
}
