// SAI có chủ đích: mở log bằng "w" mỗi client -> ghi đè dữ liệu client trước.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    (void)argc;
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(atoi(argv[1]));
    bind(ls, (struct sockaddr *)&a, sizeof a);
    listen(ls, 5);
    for (;;) {
        int c = accept(ls, NULL, NULL);
        char buf[4096];
        FILE *g = fopen(argv[2], "rb");
        size_t k;
        while ((k = fread(buf, 1, sizeof buf, g)) > 0) send(c, buf, k, 0);
        fclose(g);
        FILE *log = fopen(argv[3], "w");
        ssize_t n;
        while ((n = recv(c, buf, sizeof buf, 0)) > 0) fwrite(buf, 1, (size_t)n, log);
        fclose(log);
        close(c);
    }
}
