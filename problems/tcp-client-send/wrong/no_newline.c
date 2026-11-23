// SAI có chủ đích: thiếu '\n' cuối thông điệp -> server nhận thiếu 1 byte.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 4) return 1;
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(atoi(argv[2]));
    a.sin_addr.s_addr = inet_addr(argv[1]);
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (connect(s, (struct sockaddr *)&a, sizeof a) < 0) { perror("connect"); return 1; }
    send(s, argv[3], strlen(argv[3]), 0);
    close(s);
    return 0;
}
