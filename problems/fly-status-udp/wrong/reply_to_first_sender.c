// Sai có chủ đích: nhớ địa chỉ của client đầu tiên rồi trả lời MỌI lệnh về địa chỉ đó.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 3) return 1;
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in a = {0}, first = {0};
    int have = 0;
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_ANY);
    a.sin_port = htons(atoi(argv[1]));
    if (bind(s, (struct sockaddr *)&a, sizeof a) < 0) return 1;
    char buf[2048];
    for (;;) {
        struct sockaddr_in from;
        socklen_t fl = sizeof from;
        ssize_t n = recvfrom(s, buf, sizeof buf - 1, 0, (struct sockaddr *)&from, &fl);
        if (n < 0) continue;
        if (!have) { first = from; have = 1; }
        sendto(s, "ON_TIME\n", 8, 0, (struct sockaddr *)&first, sizeof first);
    }
}
