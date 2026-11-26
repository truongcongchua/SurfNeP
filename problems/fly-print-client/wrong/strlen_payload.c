// Sai có chủ đích: coi nội dung vé là chuỗi C (dùng strlen/fputs) nên mất mọi thứ sau byte 0x00, và dùng một lần recv cho cả tiêu đề.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 7) return 1;
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = inet_addr(argv[1]);
    a.sin_port = htons(atoi(argv[2]));
    if (connect(s, (struct sockaddr *)&a, sizeof a) < 0) return 1;
    char buf[70000];
    recv(s, buf, sizeof buf - 1, 0);
    snprintf(buf, sizeof buf, "LOGIN %s %s\n", argv[3], argv[4]);
    send(s, buf, strlen(buf), 0);
    recv(s, buf, sizeof buf - 1, 0);
    snprintf(buf, sizeof buf, "PRINT %s\n", argv[5]);
    send(s, buf, strlen(buf), 0);
    ssize_t n = recv(s, buf, sizeof buf - 1, 0);
    if (n <= 0) return 1;
    buf[n] = 0;
    char *nl = strchr(buf, '\n');
    if (!nl || strncmp(buf, "120 FILE ", 9)) return 1;
    FILE *f = fopen(argv[6], "wb");
    fputs(nl + 1, f);
    fclose(f);
    send(s, "QUIT\n", 5, 0);
    return 0;
}
