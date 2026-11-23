// SAI có chủ đích: ghép thông điệp vào bộ đệm 1024 byte -> thông điệp dài bị cắt.
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
    char line[1024];
    snprintf(line, sizeof(line), "%s\n", argv[3]);
    send(s, line, strlen(line), 0);
    close(s);
    return 0;
}
