// SAI có chủ đích: dùng strlen() thay vì số byte recv trả về -> hỏng với byte 0x00.
#include <arpa/inet.h>
#include <stdlib.h>
#include <string.h>
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
        char buf[8193];
        ssize_t n;
        while ((n = recv(c, buf, sizeof buf - 1, 0)) > 0) {
            buf[n] = 0;
            send(c, buf, strlen(buf), 0);
        }
        close(c);
    }
}
