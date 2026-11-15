// SAI có chủ đích: đọc hết stdin vào bộ nhớ rồi mới gửi -> trượt test gửi từng dòng.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    (void)argc;
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(atoi(argv[2]));
    inet_pton(AF_INET, argv[1], &a.sin_addr);
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (connect(s, (struct sockaddr *)&a, sizeof a) < 0) return 1;
    size_t cap = 1 << 20, len = 0;
    char *all = malloc(cap);
    ssize_t n;
    while ((n = read(0, all + len, cap - len)) > 0) len += (size_t)n;
    send(s, all, len, 0);
    close(s);
    return 0;
}
